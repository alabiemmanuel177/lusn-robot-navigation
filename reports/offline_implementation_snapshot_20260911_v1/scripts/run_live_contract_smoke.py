#!/usr/bin/env python3
"""Exercise the real ROS message path without claiming experimental evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import threading
import time

import rclpy
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from language_nav_interfaces.msg import (
    BeliefGraph,
    LanguageHypotheses,
    LanguageNavDecision,
    RouteEligibility,
    SemanticRouteProposal,
)
from language_nav_planner.node import PlannerNode
from language_nav_runtime.monitor_bridge import Research2MonitorBridge
from language_nav_runtime.semantic_routes import SemanticRouteNode
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy


ROOT = Path(__file__).resolve().parents[1]


class Fixture(Node):
    def __init__(self) -> None:
        super().__init__("research3_contract_smoke_fixture")
        qos = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.hypotheses_pub = self.create_publisher(
            LanguageHypotheses, "/language_hypotheses", qos
        )
        self.belief_pub = self.create_publisher(BeliefGraph, "/belief_graph", qos)
        self.warning_pub = self.create_publisher(DiagnosticArray, "/research2/warning", 10)
        self.eligibility_pub = self.create_publisher(
            RouteEligibility, "/language_nav/route_eligibility", qos
        )
        self.proposal_sub = self.create_subscription(
            SemanticRouteProposal, "/language_nav/route_proposals", self.on_proposal, qos
        )
        self.decision_sub = self.create_subscription(
            LanguageNavDecision, "/language_nav/decision", self.on_decision, qos
        )
        self.proposals = []
        self.decisions = []

    def on_proposal(self, proposal: SemanticRouteProposal) -> None:
        self.proposals.append(proposal)
        eligibility = RouteEligibility()
        eligibility.schema_version = "route-eligibility/v1"
        eligibility.request_id = proposal.route_id
        eligibility.eligible = True
        eligibility.traversability_observed = True
        eligibility.estimated_cost = proposal.distance
        eligibility.risk = 0.05
        eligibility.reason = "contract fixture path"
        eligibility.assessed_at_ns = self.get_clock().now().nanoseconds
        self.eligibility_pub.publish(eligibility)

    def on_decision(self, decision: LanguageNavDecision) -> None:
        self.decisions.append(decision)

    def publish_fixture(self) -> None:
        now = self.get_clock().now()
        warning = DiagnosticArray()
        warning.header.stamp = now.to_msg()
        status = DiagnosticStatus()
        status.name = "research2/warning"
        status.values = [
            KeyValue(key="risk_score", value="0.10"),
            KeyValue(key="persistent", value="false"),
            KeyValue(key="alarm", value="false"),
            KeyValue(key="engineering_smoke", value="false"),
            KeyValue(key="diagnosed_signal_group", value="none"),
        ]
        warning.status = [status]
        self.warning_pub.publish(warning)

        hypotheses = LanguageHypotheses()
        hypotheses.schema_version = "language-hypotheses/v1"
        hypotheses.instruction_id = "base-r010-truthful_original-s0"
        hypotheses.parser_version = "contract-fixture"
        hypotheses.hypotheses_json = json.dumps({
            "instruction_id": hypotheses.instruction_id,
            "raw_text": (
                "Go through the corridor, then continue past the blue chair, then take "
                "the second doorway on the right, then stop near the office entrance."
            ),
        })
        hypotheses.published_at_ns = now.nanoseconds
        self.hypotheses_pub.publish(hypotheses)

        def entity(observation_id, category, region_id, attributes):
            return {
                "observation_id": observation_id,
                "category": category,
                "attributes": attributes,
                "pose": {"x": 0.0, "y": 0.0, "yaw": 0.0},
                "covariance": [0.01, 0.0, 0.0, 0.01],
                "confidence": 0.95,
                "observed_at_ns": now.nanoseconds,
                "frame_id": "map",
                "source": "contract-fixture-not-research-evidence",
                "sequence": 1,
                "region_id": region_id,
            }

        belief = BeliefGraph()
        belief.schema_version = "belief-graph/v1"
        belief.instruction_id = hypotheses.instruction_id
        belief.graph_json = json.dumps({"entities": {
            "dev_00-r010-blue-chair": entity(
                "fixture-chair", "chair", "dev_00-r010-anchor-region", {"color": "blue"}
            ),
            "dev_00-r010-office": entity(
                "fixture-office", "office_entrance", "dev_00-r010-terminal", {}
            ),
        }})
        belief.update_index = 1
        belief.published_at_ns = now.nanoseconds
        self.belief_pub.publish(belief)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=ROOT / "reports" / "live_contract_smoke_v1.json"
    )
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite create-once smoke report: {args.output}")

    catalog = (
        "/home/eao/risk-calibrated-nav/configs/landmark_bridge/semantic_routes/dev_00.yaml"
    )
    rclpy.init(args=["--ros-args", "-p", f"catalog:={catalog}", "-p", "require_failure_monitor:=true"])
    nodes = [Research2MonitorBridge(), SemanticRouteNode(), PlannerNode(), Fixture()]
    executor = MultiThreadedExecutor(num_threads=4)
    for node in nodes:
        executor.add_node(node)
    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()
    fixture = nodes[-1]
    try:
        time.sleep(0.5)
        fixture.publish_fixture()
        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            commits = [
                item for item in fixture.decisions
                if item.action == "commit" and item.guard_passed and item.route_id == "dev_00_r0"
            ]
            if commits:
                record = {
                    "schema_version": "research3-live-contract-smoke/v1",
                    "research_evidence": False,
                    "fixture_warning_only": True,
                    "proposal_count": len(fixture.proposals),
                    "decision_count": len(fixture.decisions),
                    "final_action": commits[-1].action,
                    "final_route_id": commits[-1].route_id,
                    "guard_passed": commits[-1].guard_passed,
                    "monitor_path": "/research2/warning -> /failure_monitor_state -> B6 risk",
                }
                args.output.parent.mkdir(parents=True, exist_ok=True)
                with args.output.open("x", encoding="utf-8") as stream:
                    json.dump(record, stream, indent=2, sort_keys=True)
                    stream.write("\n")
                print(json.dumps(record, sort_keys=True))
                return
            time.sleep(0.05)
        raise SystemExit("timed out waiting for guarded B6 commit")
    finally:
        executor.shutdown()
        for node in nodes:
            node.destroy_node()
        rclpy.shutdown()
        thread.join(timeout=2.0)


if __name__ == "__main__":
    main()
