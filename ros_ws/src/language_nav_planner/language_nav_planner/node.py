import json
from dataclasses import asdict

import rclpy
from language_nav.contracts import Pose2D, RouteEligibility as CoreRouteEligibility
from language_nav.contracts import SemanticObservationContract
from language_nav.grounding import SemanticRouteProposal as CoreRouteProposal
from language_nav.grounding import build_semantic_route_candidates
from language_nav.systems import B6ContradictionAware, SystemInput
from language_nav_interfaces.msg import (
    BeliefGraph,
    LanguageHypotheses,
    LanguageNavDecision,
    RouteEligibility,
    SemanticRouteProposal,
)
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy


class PlannerNode(Node):
    def __init__(self):
        super().__init__("language_nav_planner")
        qos = QoSProfile(
            depth=2,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.publisher = self.create_publisher(LanguageNavDecision, "/language_nav/decision", qos)
        self.belief_subscription = self.create_subscription(
            BeliefGraph, "/belief_graph", self.on_belief, qos
        )
        self.hypothesis_subscription = self.create_subscription(
            LanguageHypotheses, "/language_hypotheses", self.on_hypotheses, qos
        )
        self.proposal_subscription = self.create_subscription(
            SemanticRouteProposal, "/language_nav/route_proposals", self.on_proposal, qos
        )
        self.eligibility_subscription = self.create_subscription(
            RouteEligibility, "/language_nav/route_eligibility", self.on_eligibility, qos
        )
        self.hypotheses = {}
        self.proposals = {}
        self.eligibility = {}
        self.latest_belief = None
        self.policy = B6ContradictionAware()

    def on_hypotheses(self, message):
        if message.schema_version != "language-hypotheses/v1" or not message.instruction_id:
            self.get_logger().error("rejecting malformed language hypotheses")
            return
        try:
            payload = json.loads(message.hypotheses_json)
        except json.JSONDecodeError as exc:
            self.get_logger().error(f"rejecting malformed hypothesis JSON: {exc}")
            return
        if payload.get("instruction_id") != message.instruction_id or not payload.get("raw_text"):
            self.get_logger().error("hypothesis payload identity mismatch")
            return
        self.hypotheses[message.instruction_id] = payload

    def on_proposal(self, message):
        if message.schema_version != "semantic-route-proposal/v1" or not message.instruction_id:
            self.get_logger().error("rejecting malformed semantic route proposal")
            return
        try:
            proposal = CoreRouteProposal(
                route_id=message.route_id,
                anchor_region_id=message.anchor_region_id,
                terminal_region_id=message.terminal_region_id,
                distance=float(message.distance),
                prior_risk=float(message.prior_risk),
                observation_coverage=float(message.observation_coverage),
                traversability_observed=bool(message.traversability_observed),
                branch_index=int(message.branch_index),
                side=message.side,
                relation=message.relation,
            )
        except ValueError as exc:
            self.get_logger().error(f"rejecting semantic route proposal: {exc}")
            return
        self.proposals[(message.instruction_id, message.route_id)] = proposal
        self._evaluate_latest()

    def on_eligibility(self, message):
        if message.schema_version != "route-eligibility/v1":
            self.get_logger().error("rejecting unsupported route eligibility schema")
            return
        try:
            result = CoreRouteEligibility(
                request_id=message.request_id,
                eligible=bool(message.eligible),
                traversability_observed=bool(message.traversability_observed),
                estimated_cost=float(message.estimated_cost),
                risk=float(message.risk),
                reason=message.reason,
            )
        except ValueError as exc:
            self.get_logger().error(f"rejecting route eligibility: {exc}")
            return
        self.eligibility[result.request_id] = result
        self._evaluate_latest()

    def on_belief(self, message):
        if message.schema_version != "belief-graph/v1":
            self.get_logger().error("rejecting unsupported belief graph schema")
            return
        self.latest_belief = message
        self._evaluate_latest()

    def _evaluate_latest(self):
        message = self.latest_belief
        if message is None:
            return
        hypotheses = self.hypotheses.get(message.instruction_id)
        if hypotheses is None:
            self._publish_abstention(message, "no matching language hypotheses")
            return
        try:
            graph = json.loads(message.graph_json)
            observations = tuple(
                _observation(entity_id, payload)
                for entity_id, payload in graph.get("entities", {}).items()
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self._publish_abstention(message, f"invalid belief graph: {exc}")
            return
        proposals = tuple(
            proposal
            for (instruction_id, _), proposal in self.proposals.items()
            if instruction_id == message.instruction_id
        )
        if not proposals:
            self._publish_abstention(message, "no semantic route proposals")
            return
        candidates = build_semantic_route_candidates(
            observations,
            proposals,
            tuple(self.eligibility.values()),
        )
        decision = self.policy.decide(
            SystemInput(
                instruction_id=message.instruction_id,
                raw_text=str(hypotheses["raw_text"]),
                candidates=candidates,
                monitor_failure_probability=0.0,
            )
        )
        output = LanguageNavDecision()
        output.schema_version = "language-nav-decision/v1"
        output.instruction_id = message.instruction_id
        output.decision_id = f"belief-{message.update_index}"
        output.action = decision.action.value
        output.route_id = decision.route_id or ""
        output.candidates_json = json.dumps(
            [asdict(candidate) for candidate in candidates], separators=(",", ":"), sort_keys=True
        )
        output.costs_json = json.dumps(
            {candidate.route_id: {"distance": candidate.distance, "risk": candidate.risk}
             for candidate in candidates},
            separators=(",", ":"), sort_keys=True,
        )
        output.guard_passed = decision.guard_passed
        output.reason = decision.reason
        output.decided_at_ns = self.get_clock().now().nanoseconds
        self.publisher.publish(output)

    def _publish_abstention(self, message, reason):
        output = LanguageNavDecision()
        output.schema_version = "language-nav-decision/v1"
        output.instruction_id = message.instruction_id
        output.decision_id = f"belief-{message.update_index}"
        output.action = "stop_and_abstain"
        output.route_id = ""
        output.candidates_json = "[]"
        output.costs_json = "{}"
        output.guard_passed = False
        output.reason = reason
        output.decided_at_ns = self.get_clock().now().nanoseconds
        self.publisher.publish(output)


def _observation(entity_id, payload):
    pose = payload["pose"]
    return SemanticObservationContract(
        schema_version="semantic-observation/v1",
        observation_id=str(payload["observation_id"]),
        entity_id=str(entity_id),
        category=str(payload["category"]),
        attributes={str(key): str(value) for key, value in payload["attributes"].items()},
        pose=Pose2D(float(pose["x"]), float(pose["y"]), float(pose.get("yaw", 0.0))),
        covariance=tuple(float(value) for value in payload["covariance"]),
        confidence=float(payload["confidence"]),
        observed_at_ns=int(payload["observed_at_ns"]),
        frame_id=str(payload["frame_id"]),
        source=str(payload["source"]),
        sequence=int(payload["sequence"]),
        region_id=str(payload["region_id"]),
    )


def main(args=None):
    rclpy.init(args=args)
    node = PlannerNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
