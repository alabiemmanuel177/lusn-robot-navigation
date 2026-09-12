#!/usr/bin/env python3
"""Run one create-once, non-protected Research 3 Gazebo/Nav2 episode."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import threading
import time

import rclpy
from geometry_msgs.msg import PoseWithCovarianceStamped
from language_nav_interfaces.msg import (
    FailureMonitorState,
    LanguageInstruction,
    LanguageNavDecision,
    LanguageNavOutcome,
    RouteEligibility,
)
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
import yaml
from language_nav.live import measured_live_outcome, terminal_identity_outcome, validate_trajectory_evidence
from language_nav.evaluation.ordered import score_ordered_instruction

from episode_logger.monitor import EpisodeMonitor, HAVE_CONTACTS
from experiment_controller import preflight
from experiment_controller.run_episode import (
    Stack,
    load_system_config,
    nav2_bringup_ready,
    shutdown_nav2_lifecycle,
    simulation_launch_command,
    write_episode_params,
)


ROOT = Path(__file__).resolve().parents[1]
R1 = Path("/home/eao/risk-calibrated-nav")
R2 = Path("/home/eao/failure-prediction")


class TimestampedEpisodeMonitor(EpisodeMonitor):
    """Pair source timestamps with exactly the positions accepted by the provider."""

    def __init__(self, **kwargs):
        self.capture_lock = threading.RLock()
        self.position_stamps = []
        self.localization_diagnostics = []
        self.scan_diagnostics = []
        self.pose_diagnostic_history = []
        super().__init__(**kwargs)

    def _on_gt(self, message):
        with self.capture_lock:
            before = len(self.m.gt_positions)
            super()._on_gt(message)
            self.pose_diagnostic_history.append((self._stamp_s(message),
                message.pose.position.x, message.pose.position.y, self._yaw(message.pose.orientation)))
            if len(self.pose_diagnostic_history) > 4096:
                del self.pose_diagnostic_history[:1024]
            if len(self.m.gt_positions) > before:
                self.position_stamps.append(int(message.header.stamp.sec) * 1_000_000_000
                                            + int(message.header.stamp.nanosec))

    def _on_scan(self, message):
        super()._on_scan(message)
        with self.capture_lock, self._lock:
            stamp = self._stamp_s(message)
            if (not self._active or len(self.scan_diagnostics) >= 100
                    or (self.scan_diagnostics and stamp - self.scan_diagnostics[-1]['stamp_s'] < .5)):
                return
            pose = min(self.pose_diagnostic_history, key=lambda p: abs(p[0] - stamp), default=None)
            if pose is None or abs(pose[0] - stamp) > .1:
                return
            self.scan_diagnostics.append(dict(stamp_s=stamp, ground_truth_pose=list(pose),
                frame_id=message.header.frame_id, angle_min=message.angle_min,
                angle_increment=message.angle_increment, range_min=message.range_min,
                range_max=message.range_max,
                ranges=[float(r) if math.isfinite(r) else None for r in message.ranges]))

    def start(self):
        with self.capture_lock:
            self.started_ns = self.get_clock().now().nanoseconds
            super().start()

    def _on_amcl(self, message):
        super()._on_amcl(message)
        with self.capture_lock, self._lock:
            if not self._active or len(self.localization_diagnostics) >= 2048:
                return
            stamp = self._stamp_s(message)
            nearest = min(zip(self._gt_stamps, self._gt_hist),
                          key=lambda row: abs(row[0] - stamp), default=None)
            matched = nearest is not None and abs(nearest[0] - stamp) <= .1
            self.localization_diagnostics.append({
                'amcl_stamp_ns': int(message.header.stamp.sec) * 1_000_000_000 + message.header.stamp.nanosec,
                'amcl_xy': [message.pose.pose.position.x, message.pose.pose.position.y],
                'amcl_yaw': self._yaw(message.pose.pose.orientation),
                'ground_truth_xy': list(nearest[1]) if matched else None,
                'ground_truth_stamp_ns': round(nearest[0] * 1e9) if matched else None,
                'maximum_pair_gap_s': .1, 'paired': matched})

    def stop(self):
        with self.capture_lock:
            super().stop()
            self.ended_ns = self.get_clock().now().nanoseconds


class LiveController(Node):
    def __init__(self) -> None:
        super().__init__("research3_live_episode_controller")
        qos = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.decisions = []
        self.outcomes = []
        self.monitors = []
        self.eligibility = []
        self.instruction_pub = self.create_publisher(
            LanguageInstruction, "/language_instruction", qos
        )
        self.create_subscription(LanguageNavDecision, "/language_nav/decision", self.decisions.append, qos)
        self.create_subscription(LanguageNavOutcome, "/language_nav/outcome", self.outcomes.append, qos)
        self.create_subscription(FailureMonitorState, "/failure_monitor_state", self.monitors.append, qos)
        self.create_subscription(RouteEligibility, "/language_nav/route_eligibility", self.eligibility.append, qos)

    def publish_instruction(self, variant: dict) -> None:
        message = LanguageInstruction()
        message.schema_version = "language-instruction/v1"
        message.instruction_id = variant["variant_id"]
        message.raw_text = variant["raw_text"]
        message.provenance = variant["provenance"]
        message.received_at_ns = self.get_clock().now().nanoseconds
        self.instruction_pub.publish(message)


def _route(route_id: str) -> tuple[dict, dict]:
    map_id = route_id.rsplit("_r", 1)[0]
    document = yaml.safe_load((R1 / "configs" / "routes" / f"{map_id}.yaml").read_text())
    active = list(document.get("routes") or []) + list(document.get("replacement_routes") or [])
    selected = next((item for item in active if item["route_id"] == route_id), None)
    if selected is None:
        raise ValueError(f"unknown route {route_id}")
    return document, selected


def _variant(variant_id: str) -> dict:
    payload = json.loads((ROOT / "data/manifests/instruction_benchmark_v0.1.json").read_text())
    selected = next(
        (item for item in payload["deployed_variants"] if item["variant_id"] == variant_id), None
    )
    if selected is None:
        raise ValueError(f"unknown deployed variant {variant_id}")
    return selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--route-id", default="dev_00_r0")
    parser.add_argument("--variant-id", default="base-r010-truthful_original-s0")
    parser.add_argument("--run-id", default="r3-dev00-truthful-live-v1")
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--goal-tolerance-m", type=float, default=0.35)
    parser.add_argument("--system-id", choices=("B1", "B2", "B4", "B5", "B6"), default="B6")
    parser.add_argument("--ordered-geometry", type=Path)
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        raise SystemExit("timeout must be finite and positive")
    if not math.isfinite(args.goal_tolerance_m) or args.goal_tolerance_m <= 0:
        raise SystemExit("goal tolerance must be finite and positive")
    if not HAVE_CONTACTS:
        raise SystemExit("contact measurement is unavailable")
    # Scope the provider's orphan cleanup to this run and its descendants.
    os.environ.setdefault("RCN_WORKER_ID", args.run_id)
    if args.route_id.startswith("test_"):
        raise SystemExit("protected test routes require explicit held-out authorization")
    route_doc, route = _route(args.route_id)
    variant = _variant(args.variant_id)
    map_id = route_doc["map_id"]
    semantic_catalog = R1 / "configs/landmark_bridge/semantic_routes" / f"{map_id}.yaml"
    semantic_doc = yaml.safe_load(semantic_catalog.read_text())
    if semantic_doc.get("partition") not in {"development", "validation"}:
        raise SystemExit("this runner refuses protected catalogues")
    mapping = next(
        (item for item in semantic_doc["routes"] if item["platform_route_id"] == args.route_id), None
    )
    if mapping is None or mapping["base_instruction_id"] != variant["base_instruction_id"]:
        raise SystemExit("route and benchmark instruction do not match")

    report_dir = ROOT / "reports/live_episodes" / args.run_id
    if report_dir.exists():
        raise SystemExit(f"refusing to overwrite create-once run {report_dir}")
    report_dir.mkdir(parents=True)
    (report_dir / "request.json").write_text(json.dumps({
        "schema_version": "research3-live-request/v1",
        "run_id": args.run_id,
        "system_id": args.system_id,
        "route_id": args.route_id,
        "variant_id": args.variant_id,
        "partition": semantic_doc["partition"],
        "protected_test_routes_used": False,
    }, indent=2, sort_keys=True) + "\n")

    scene = R1 / "configs/landmark_bridge/scenes" / f"{map_id}.yaml"
    scene_document = yaml.safe_load(scene.read_text())
    ordered_geometry = None
    if args.ordered_geometry:
        ordered_geometry = json.loads(args.ordered_geometry.read_text())
        if (ordered_geometry.get("map_sha256") != scene_document["map_hash"]
                or ordered_geometry.get("base_instruction_id") != variant["base_instruction_id"]):
            raise ValueError("ordered geometry map/instruction identity mismatch")
    runtime_scene = ROOT / "data/landmark_bridge/runtime_scenes" / f"{map_id}.yaml"
    world = Path("/tmp") / f"{args.run_id}.sdf"
    subprocess.run([
        "python3", str(R1 / "scripts/make_landmark_world.py"),
        "--scene", str(scene), "--output", str(world),
    ], check=True)

    stack = Stack(report_dir / "logs")
    monitor = controller = executor = spin = None
    nav2_started = False
    failure = None
    episode_started_ns = None
    started_wall = time.time()
    try:
        rclpy.init()
        stack.launch("sim", simulation_launch_command(map_id, route["start"], world))
        readiness = dict(preflight.MANDATORY)
        readiness.update(preflight.EVALUATION_ONLY)
        ready = preflight.wait_until_ready(readiness, timeout_s=90.0)
        if not ready.ok:
            raise RuntimeError("simulator preflight failed: " + ready.summary())

        system = load_system_config(R1 / "configs/systems/s0.yaml")
        params = write_episode_params(
            R1 / "configs/nav2/nav2_common.yaml",
            report_dir / "nav2_params.yaml",
            float(route["start"]["x"]),
            float(route["start"]["y"]),
            float(route["start"].get("yaw", 0.0)),
            system,
        )
        stack.launch("nav2", [
            "ros2", "launch", "simulation_worlds", "nav2.launch.py",
            f"map:={R1 / 'data' / semantic_doc['partition'] / map_id / 'map.yaml'}",
            f"params_file:={params}",
        ])
        nav2_started = True

        monitor = TimestampedEpisodeMonitor(perception_enabled=False)
        controller = LiveController()
        executor = MultiThreadedExecutor(num_threads=4)
        executor.add_node(monitor)
        executor.add_node(controller)
        spin = threading.Thread(target=executor.spin, daemon=True)
        spin.start()
        nav_client = ActionClient(monitor, NavigateToPose, "navigate_to_pose")
        bringup = nav2_bringup_ready(nav_client, monitor, 90.0)
        if bringup is not None:
            raise RuntimeError(bringup)

        initial = PoseWithCovarianceStamped()
        initial.header.frame_id = "map"
        initial.pose.pose.position.x = float(route["start"]["x"])
        initial.pose.pose.position.y = float(route["start"]["y"])
        yaw = float(route["start"].get("yaw", 0.0))
        initial.pose.pose.orientation.z = math.sin(yaw / 2.0)
        initial.pose.pose.orientation.w = math.cos(yaw / 2.0)
        initial.pose.covariance[0] = 0.25
        initial.pose.covariance[7] = 0.25
        initial.pose.covariance[35] = 0.068
        initial_pub = monitor.create_publisher(PoseWithCovarianceStamped, "/initialpose", 10)
        convergence_deadline = time.monotonic() + 60.0
        while time.monotonic() < convergence_deadline and not monitor.amcl_converged():
            initial.header.stamp = monitor.get_clock().now().to_msg()
            initial_pub.publish(initial)
            time.sleep(1.0)
        if not monitor.amcl_converged():
            raise RuntimeError("AMCL did not converge")

        r2_output = report_dir / "research2"
        r3_output = report_dir / "research3"
        r2_output.mkdir()
        r3_output.mkdir()
        stack.launch("research3", [
            "ros2", "launch", "language_nav_bringup", "live_adapters.launch.py",
            f"scene:={runtime_scene}", f"semantic_catalog:={semantic_catalog}",
            f"partition:={semantic_doc['partition']}", f"run_id:={args.run_id}",
            f"system_id:={args.system_id}",
            f"calibration:={ROOT / 'configs/landmark_calibration_v1.json'}",
            f"research2_output_dir:={r2_output}", f"research3_output_dir:={r3_output}",
        ])
        monitor_deadline = time.monotonic() + 45.0
        while time.monotonic() < monitor_deadline and not controller.monitors:
            time.sleep(0.1)
        if not controller.monitors:
            raise RuntimeError("frozen Research 2 monitor readiness was not observed")
        if monitor.spawned_in_collision():
            raise RuntimeError("robot spawned in collision before instruction dispatch")
        monitor.start()
        episode_started_ns = monitor.started_ns
        controller.publish_instruction(variant)

        episode_deadline = time.monotonic() + args.timeout
        while time.monotonic() < episode_deadline and not controller.outcomes:
            if monitor.snapshot().collision:
                break
            time.sleep(0.1)
        monitor.stop()
        episode_ended_ns = monitor.ended_ns
        measurements = monitor.snapshot()
        outcome = controller.outcomes[-1] if controller.outcomes else None
        timed_out = outcome is None and not measurements.collision
        reason = (
            "measured collision" if measurements.collision else
            "episode wall-time limit reached" if timed_out else outcome.reason
        )
        predictions = [
            item for item in controller.monitors
            if "no_prediction_yet" not in item.reason_codes
            and episode_started_ns <= item.observed_at_ns <= episode_ended_ns
        ]
        evidence = {
            "schema_version": "research3-live-measurements/v2",
            "run_id": args.run_id,
            "episode_started_at_ns": episode_started_ns,
            "episode_ended_at_ns": episode_ended_ns,
            "ground_truth_positions": list(measurements.gt_positions),
            "ground_truth_timestamps_ns": monitor.position_stamps,
            "commanded_goal": [float(route["goal"]["x"]), float(route["goal"]["y"])],
            "goal_tolerance_m": args.goal_tolerance_m,
            "nav2_reported_success": bool(outcome and outcome.navigation_success),
            "timeout": timed_out,
            "scene_sha256": hashlib.sha256(scene.read_bytes()).hexdigest(),
            "terminal_ground_truth": scene_document["entities"],
            "expected_terminal_region_id": mapping["terminal_region_id"],
            "ordered_geometry": ordered_geometry,
            "collision_count": measurements.collision_count,
            "predictions": [
                {"observed_at_ns": item.observed_at_ns,
                 "failure_probability": item.failure_probability,
                 "reason_codes": list(item.reason_codes)} for item in predictions
            ],
            "decisions": [
                {"action": item.action, "route_id": item.route_id, "reason": item.reason,
                 "decided_at_ns": item.decided_at_ns} for item in controller.decisions
            ],
        }
        evidence_path = report_dir / "measurements.json"
        with evidence_path.open("x") as stream:
            json.dump(evidence, stream, indent=2)
        summary = {
            "schema_version": "research3-live-summary/v3",
            "run_id": args.run_id,
            "system_id": args.system_id,
            "corruption_condition": args.variant_id.removeprefix(variant["base_instruction_id"] + "-").rsplit("-s", 1)[0],
            "measurements_sha256": hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
            "route_id": args.route_id,
            "variant_id": args.variant_id,
            "partition": semantic_doc["partition"],
            "protected_test_routes_used": False,
            **measured_live_outcome(
                positions=measurements.gt_positions,
                distance_m=measurements.path_length_m,
                goal=(float(route["goal"]["x"]), float(route["goal"]["y"])),
                goal_tolerance_m=args.goal_tolerance_m,
                collision=measurements.collision, timeout=timed_out,
                nav2_success=bool(outcome and outcome.navigation_success),
            ),
            **terminal_identity_outcome(
                measurements.gt_positions, scene_document["entities"], mapping["terminal_region_id"],
            ),
            "reason": reason,
            "interventions": json.loads(outcome.interventions_json) if outcome else None,
            "valid_terminal_outcome": bool(measurements.gt_positions),
            "episode_started_at_ns": episode_started_ns,
            "episode_ended_at_ns": episode_ended_ns,
            "collision_count": measurements.collision_count,
            "measurement_source": "Research 1 ground-truth pose and contact monitor",
            "decision_count": len(controller.decisions),
            "eligibility_count": len(controller.eligibility),
            "monitor_state_count": len(controller.monitors),
            "monitor_prediction_observed": bool(predictions),
            "episode_prediction_count": len(predictions),
            "duration_wall_s": time.time() - started_wall,
        }
        if ordered_geometry is not None:
            ordered_score = score_ordered_instruction(
                measurements.gt_positions, ordered_geometry,
                terminal_identity_correct=summary["terminal_identity_correct"],
                collision=measurements.collision, timeout=timed_out,
            )
            summary["ordered_instruction_score"] = ordered_score
            summary["instruction_completion"] = ordered_score["instruction_completion"]
            summary["semantic_outcome_measured"] = ordered_score["instruction_completion"] is not None
        summary["trajectory_quality"] = validate_trajectory_evidence(
            measurements.gt_positions, monitor.position_stamps, episode_started_ns, episode_ended_ns)
        if not summary["trajectory_quality"]["valid"]:
            summary["navigation_success"] = False
            summary["instruction_completion"] = None
            summary["semantic_outcome_measured"] = False
            summary["valid_terminal_outcome"] = False
        with (report_dir / "summary.json").open("x") as stream:
            json.dump(summary, stream, indent=2, sort_keys=True)
            stream.write("\n")
        print(json.dumps(summary, sort_keys=True))
    except Exception as exc:
        failure = str(exc)
        (report_dir / "failure.txt").write_text(failure + "\n")
        if episode_started_ns is not None and not (report_dir / "summary.json").exists():
            # Once dispatched, an infrastructure failure is a retained trial, not
            # permission for the campaign runner to silently replace the episode.
            with (report_dir / "summary.json").open("x") as stream:
                json.dump({
                    "schema_version": "research3-live-summary/v2",
                    "run_id": args.run_id, "route_id": args.route_id,
                    "variant_id": args.variant_id, "system_id": args.system_id,
                    "partition": semantic_doc["partition"], "protected_test_routes_used": False,
                    "navigation_success": False, "instruction_completion": None,
                    "infrastructure_failure": True, "valid_terminal_outcome": False,
                    "reason": failure, "episode_started_at_ns": episode_started_ns,
                    "measurement_status": "incomplete_requires_audit",
                }, stream, indent=2, sort_keys=True)
                stream.write("\n")
        raise
    finally:
        if nav2_started and monitor is not None and rclpy.ok():
            shutdown_nav2_lifecycle(monitor, 20.0)
        stack.shutdown()
        if executor is not None:
            executor.shutdown()
        for node in (controller, monitor):
            if node is not None:
                node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        if spin is not None:
            spin.join(timeout=2.0)
        if failure:
            print(f"live episode failed: {failure}")


if __name__ == "__main__":
    main()
