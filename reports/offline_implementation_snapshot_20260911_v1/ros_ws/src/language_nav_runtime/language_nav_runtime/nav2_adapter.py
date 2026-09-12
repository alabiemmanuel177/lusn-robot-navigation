from __future__ import annotations

import json
import math
from copy import deepcopy
from pathlib import Path

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from language_nav.adapters.research1 import Research1RouteCatalog
from language_nav.benchmark.physical_catalog import load_physical_runtime_catalog
from language_nav.live import ImmutableEpisodeRecord, inspection_waypoint, path_length, has_post_inspection_anchor
from language_nav_interfaces.msg import (
    LanguageNavDecision,
    LanguageNavOutcome,
    RouteEligibility,
    RouteExecutionResult,
    SemanticRouteProposal,
)
from nav2_msgs.action import ComputePathToPose, NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy


class Nav2RouteAdapter(Node):
    def __init__(self) -> None:
        super().__init__("nav2_route_adapter")
        self.declare_parameter("partition", "development")
        self.declare_parameter("physical_catalog", "")
        self.declare_parameter("research1_repository", "/home/eao/risk-calibrated-nav")
        self.declare_parameter("run_id", "")
        self.declare_parameter("output_dir", "")
        self.declare_parameter("inspection_observation_timeout_s", 8.0)
        inspection_timeout = float(self.get_parameter("inspection_observation_timeout_s").value)
        if not math.isfinite(inspection_timeout) or inspection_timeout <= 2.0:
            raise ValueError("inspection observation timeout must exceed the 2s dwell")
        self.inspection_wait_timeout_ns = int(inspection_timeout * 1e9)
        partition = str(self.get_parameter("partition").value)
        if partition == "test":
            raise PermissionError("protected test routes require a separately authorized runner")
        physical_path = str(self.get_parameter("physical_catalog").value)
        if physical_path:
            physical = load_physical_runtime_catalog(physical_path)
            if physical.semantic.partition != partition:
                raise ValueError("physical catalogue partition mismatch")
            routes = physical.execution
        else:
            routes = Research1RouteCatalog(
                str(self.get_parameter("research1_repository").value)
            ).load_partition(partition, allow_protected=False)
        self.routes = {route.route_id: route for route in routes}
        self.proposals: dict[str, SemanticRouteProposal] = {}
        self.planned_distance: dict[str, float] = {}
        self.planning: set[str] = set()
        self.path_queue = []
        self.active_path_route = None
        self.executed_decisions: set[str] = set()
        self.active_instructions: set[str] = set()
        self.completed_instructions: set[str] = set()
        self.active_goal_handles = {}
        self.cancel_reasons: dict[str, str] = {}
        self.execution_started_ns: dict[str, int] = {}
        self.inspection_poses = {}
        self.inspection_completed_ns = {}
        self.pending_inspections = {}
        self.execution_trace = []

        qos = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.eligibility_pub = self.create_publisher(
            RouteEligibility, "/language_nav/route_eligibility", qos
        )
        self.execution_pub = self.create_publisher(
            RouteExecutionResult, "/language_nav/route_execution_result", qos
        )
        self.outcome_pub = self.create_publisher(
            LanguageNavOutcome, "/language_nav/outcome", qos
        )
        self.proposal_sub = self.create_subscription(
            SemanticRouteProposal, "/language_nav/route_proposals", self.on_proposal, qos
        )
        self.decision_sub = self.create_subscription(
            LanguageNavDecision, "/language_nav/decision", self.on_decision, qos
        )
        self.path_client = ActionClient(self, ComputePathToPose, "compute_path_to_pose")
        self.nav_client = ActionClient(self, NavigateToPose, "navigate_to_pose")
        self.path_timer = self.create_timer(0.1, self._start_next_path)
        self.inspection_timer = self.create_timer(0.25, self._check_inspection_timeout)

    def _check_inspection_timeout(self):
        now = self.get_clock().now().nanoseconds
        for instruction_id, decision in tuple(self.pending_inspections.items()):
            if instruction_id in self.completed_instructions or instruction_id in self.active_instructions:
                self.pending_inspections.pop(instruction_id, None)
                continue
            if now - self.inspection_completed_ns[instruction_id] >= self.inspection_wait_timeout_ns:
                self.pending_inspections.pop(instruction_id, None)
                stop = deepcopy(decision)
                stop.action = "stop_and_abstain"
                stop.route_id = ""
                self.execution_trace.append({"action": "inspection_observation_timeout",
                                             "instruction_id": instruction_id, "observed_at_ns": now})
                self._publish_execution(stop, False, False,
                                        "inspection ended without fresh anchor evidence; abstained")

    def _goal_pose(self, route_id: str) -> PoseStamped:
        route = self.routes[route_id]
        message = PoseStamped()
        message.header.frame_id = "map"
        message.header.stamp = self.get_clock().now().to_msg()
        message.pose.position.x = route.goal.x
        message.pose.position.y = route.goal.y
        message.pose.orientation.z = math.sin(route.goal.yaw / 2.0)
        message.pose.orientation.w = math.cos(route.goal.yaw / 2.0)
        return message

    def on_proposal(self, message: SemanticRouteProposal) -> None:
        if message.schema_version != "semantic-route-proposal/v1":
            return
        if message.route_id not in self.routes:
            self._publish_eligibility(message, False, float(message.distance), 1.0, "unknown route")
            return
        self.proposals[message.route_id] = message
        if message.route_id in self.planning:
            return
        self.planning.add(message.route_id)
        self.path_queue.append(message.route_id)

    def _start_next_path(self):
        # Nav2's action server may preempt a pending goal when several candidate
        # requests arrive together. Serialize assessments instead of interpreting
        # our own request contention as an unreachable route.
        if self.active_path_route is not None or not self.path_queue:
            return
        route_id = self.path_queue.pop(0)
        message = self.proposals[route_id]
        if not self.path_client.wait_for_server(timeout_sec=0.0):
            self.planning.discard(route_id)
            self._publish_eligibility(
                message, False, float(message.distance), 1.0, "Nav2 planner unavailable"
            )
            return
        self.active_path_route = route_id
        goal = ComputePathToPose.Goal()
        goal.goal = self._goal_pose(message.route_id)
        future = self.path_client.send_goal_async(goal)
        future.add_done_callback(
            lambda completed, route_id=message.route_id: self._path_goal_response(route_id, completed)
        )

    def _path_goal_response(self, route_id: str, future) -> None:
        goal_handle = future.result()
        if goal_handle is None or not goal_handle.accepted:
            self.active_path_route = None
            self.planning.discard(route_id)
            self._publish_eligibility(
                self.proposals[route_id], False, float(self.proposals[route_id].distance), 1.0,
                "Nav2 rejected path request",
            )
            return
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(
            lambda completed, selected=route_id: self._path_result(selected, completed)
        )

    def _path_result(self, route_id: str, future) -> None:
        self.active_path_route = None
        self.planning.discard(route_id)
        wrapped = future.result()
        result = wrapped.result
        eligible = wrapped.status == GoalStatus.STATUS_SUCCEEDED and result.error_code == 0
        points = tuple((pose.pose.position.x, pose.pose.position.y) for pose in result.path.poses)
        distance = path_length(points) if len(points) > 1 else float(self.proposals[route_id].distance)
        risk = float(self.proposals[route_id].prior_risk) if eligible else 1.0
        reason = "Nav2 path available" if eligible else (result.error_msg or f"Nav2 path status {wrapped.status}, error {result.error_code}")
        if eligible:
            self.planned_distance[route_id] = distance
            self.inspection_poses[route_id] = inspection_waypoint(points)
        self._publish_eligibility(self.proposals[route_id], eligible, distance, risk, reason)

    def _publish_eligibility(self, proposal, eligible, distance, risk, reason) -> None:
        output = RouteEligibility()
        output.schema_version = "route-eligibility/v1"
        output.request_id = proposal.route_id
        output.eligible = bool(eligible)
        output.traversability_observed = bool(eligible)
        output.estimated_cost = float(distance)
        output.risk = float(risk)
        output.reason = reason
        output.assessed_at_ns = self.get_clock().now().nanoseconds
        self.eligibility_pub.publish(output)

    def on_decision(self, message: LanguageNavDecision) -> None:
        if (message.schema_version == "language-nav-decision/v1"
                and message.action == "stop_and_abstain"
                and message.instruction_id in self.inspection_completed_ns
                and message.instruction_id not in self.active_instructions
                and message.instruction_id not in self.completed_instructions):
            self._publish_execution(message, False, False, "post-inspection abstention: " + message.reason)
            return
        if (
            message.schema_version == "language-nav-decision/v1"
            and message.action == "stop_and_abstain"
            and message.instruction_id in self.active_instructions
        ):
            self.cancel_reasons.setdefault(message.instruction_id, message.reason)
            handle = self.active_goal_handles.get(message.instruction_id)
            if handle is not None:
                handle.cancel_goal_async()
            return
        if (
            message.schema_version != "language-nav-decision/v1"
            or message.action not in {"commit", "inspect", "ignore", "backtrack"}
            or not message.guard_passed
            or not message.route_id
            or message.decision_id in self.executed_decisions
            or message.instruction_id in self.active_instructions
            or message.instruction_id in self.completed_instructions
        ):
            return
        if message.route_id not in self.planned_distance:
            self.get_logger().error("refusing decision without successful Nav2 eligibility")
            return
        if not self.nav_client.wait_for_server(timeout_sec=0.0):
            self.get_logger().error("refusing decision because NavigateToPose is unavailable")
            return
        inspected_at = self.inspection_completed_ns.get(message.instruction_id)
        if inspected_at is not None:
            # Let the detector/belief pipeline receive a new viewpoint before replanning.
            if message.decided_at_ns < inspected_at + 2_000_000_000:
                return
            if not has_post_inspection_anchor(message.candidates_json, message.route_id,
                                              inspected_at, self.get_clock().now().nanoseconds):
                # Monitor/proposal callbacks can issue a new decision without a
                # new sensor observation. Do not move on that timestamp alone.
                return
            if message.action == "inspect":
                self._publish_execution(message, False, False, "inspection budget exhausted; abstained")
                return
        inspection = self.inspection_poses.get(message.route_id)
        if message.action == "inspect" and inspection is None:
            self._publish_execution(message, False, False, "no distinct inspection viewpoint; abstained")
            return
        self.executed_decisions.add(message.decision_id)
        self.active_instructions.add(message.instruction_id)
        self.execution_started_ns[message.decision_id] = self.get_clock().now().nanoseconds
        goal = NavigateToPose.Goal()
        goal.pose = self._goal_pose(message.route_id)
        if message.action == "inspect":
            x, y, yaw = inspection
            goal.pose.pose.position.x = x
            goal.pose.pose.position.y = y
            goal.pose.pose.orientation.z = math.sin(yaw / 2)
            goal.pose.pose.orientation.w = math.cos(yaw / 2)
        self.execution_trace.append({
            "action": message.action, "instruction_id": message.instruction_id,
            "x": goal.pose.pose.position.x, "y": goal.pose.pose.position.y,
            "started_at_ns": self.get_clock().now().nanoseconds,
        })
        future = self.nav_client.send_goal_async(goal)
        future.add_done_callback(
            lambda completed, decision=message: self._nav_goal_response(decision, completed)
        )

    def _nav_goal_response(self, decision: LanguageNavDecision, future) -> None:
        goal_handle = future.result()
        if goal_handle is None or not goal_handle.accepted:
            self._publish_execution(decision, False, True, "Nav2 rejected navigation goal")
            return
        self.active_goal_handles[decision.instruction_id] = goal_handle
        if decision.instruction_id in self.cancel_reasons:
            goal_handle.cancel_goal_async()
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(
            lambda completed, selected=decision: self._nav_result(selected, completed)
        )

    def _nav_result(self, decision: LanguageNavDecision, future) -> None:
        wrapped = future.result()
        succeeded = wrapped.status == GoalStatus.STATUS_SUCCEEDED and wrapped.result.error_code == 0
        monitor_cancel = self.cancel_reasons.get(decision.instruction_id)
        if decision.action == "inspect" and succeeded and not monitor_cancel:
            self.inspection_completed_ns[decision.instruction_id] = self.get_clock().now().nanoseconds
            self.active_instructions.discard(decision.instruction_id)
            self.active_goal_handles.pop(decision.instruction_id, None)
            self.pending_inspections[decision.instruction_id] = deepcopy(decision)
            self.execution_trace.append({"action": "inspection_completed",
                                         "completed_at_ns": self.get_clock().now().nanoseconds})
            return
        reason = (
            f"monitor-driven abstention: {monitor_cancel}"
            if monitor_cancel
            else "navigation succeeded" if succeeded
            else wrapped.result.error_msg or f"Nav2 status {wrapped.status}"
        )
        infrastructure_failure = wrapped.status in {
            GoalStatus.STATUS_UNKNOWN,
            GoalStatus.STATUS_ABORTED,
        }
        self._publish_execution(decision, succeeded, infrastructure_failure, reason)

    def _publish_execution(self, decision, succeeded, infrastructure_failure, reason) -> None:
        completed_at_ns = self.get_clock().now().nanoseconds
        distance = self.planned_distance.get(decision.route_id, 0.0)
        result = RouteExecutionResult()
        result.schema_version = "route-execution-result/v1"
        result.request_id = decision.route_id
        result.succeeded = succeeded
        result.visited_regions = []
        result.distance = distance
        result.collision = False
        result.infrastructure_failure = infrastructure_failure
        result.reason = reason
        result.completed_at_ns = completed_at_ns
        self.execution_pub.publish(result)

        outcome = LanguageNavOutcome()
        outcome.schema_version = "language-nav-outcome/v1"
        outcome.instruction_id = decision.instruction_id
        outcome.instruction_completion = succeeded
        outcome.navigation_success = succeeded
        outcome.collision = False
        outcome.timeout = False
        outcome.wrong_goal = False
        interventions = [] if decision.action == "commit" else [decision.action]
        if decision.instruction_id in self.cancel_reasons:
            interventions.append("stop_and_abstain")
        outcome.interventions_json = json.dumps(interventions, separators=(",", ":"))
        outcome.reason = reason
        outcome.completed_at_ns = completed_at_ns
        self.outcome_pub.publish(outcome)
        self._write_record(decision, succeeded, infrastructure_failure, distance, reason, completed_at_ns)
        self.active_instructions.discard(decision.instruction_id)
        self.active_goal_handles.pop(decision.instruction_id, None)
        self.completed_instructions.add(decision.instruction_id)

    def _write_record(self, decision, succeeded, infrastructure_failure, distance, reason, completed_at_ns):
        output_dir = str(self.get_parameter("output_dir").value)
        run_id = str(self.get_parameter("run_id").value)
        if not output_dir or not run_id:
            return
        path = Path(output_dir).resolve() / f"{run_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        record = ImmutableEpisodeRecord(
            schema_version="research3-live-episode/v1",
            run_id=run_id,
            instruction_id=decision.instruction_id,
            route_id=decision.route_id,
            action=decision.action,
            navigation_success=succeeded,
            collision=False,
            timeout=False,
            infrastructure_failure=infrastructure_failure,
            distance=distance,
            reason=reason,
            started_at_ns=self.execution_started_ns.get(decision.decision_id, 0),
            completed_at_ns=completed_at_ns,
        )
        with path.open("x", encoding="utf-8") as stream:
            stream.write(record.to_json() + "\n")
        with path.with_suffix(".trace.json").open("x", encoding="utf-8") as stream:
            json.dump(self.execution_trace, stream, indent=2)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = Nav2RouteAdapter()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
