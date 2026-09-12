#!/usr/bin/env python3
"""Real ROS transport fault injection; synthetic inputs, never study evidence."""
import argparse
import json
from pathlib import Path
import threading
import time

from run_live_contract_smoke import (Fixture, Research2MonitorBridge, SemanticRouteNode,
                                     PlannerNode, MultiThreadedExecutor, rclpy)
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite readiness smoke")
    rclpy.init(args=["--ros-args", "-p", "require_failure_monitor:=true", "-p",
                    "catalog:=/home/eao/risk-calibrated-nav/configs/landmark_bridge/semantic_routes/dev_00.yaml"])
    nodes = [Research2MonitorBridge(), SemanticRouteNode(), PlannerNode(), Fixture()]
    fixture = nodes[-1]
    events = fixture.create_publisher(DiagnosticArray, "/research2/events", QoSProfile(
        depth=10, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.TRANSIENT_LOCAL))
    executor = MultiThreadedExecutor(num_threads=4)
    for node in nodes:
        executor.add_node(node)
    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()
    checks = []

    def wait_for(action, since):
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if any(d.action == action for d in fixture.decisions[since:]):
                return
            time.sleep(.05)
        raise AssertionError(f"no {action} after fault/fixture")

    def warning(values, stamp=None):
        message = DiagnosticArray()
        message.header.stamp = stamp or fixture.get_clock().now().to_msg()
        status = DiagnosticStatus()
        status.name = "research2/warning"
        status.values = [KeyValue(key=k, value=v) for k, v in values.items()]
        message.status = [status]
        fixture.warning_pub.publish(message)
        return message

    nominal = {"risk_score": "0.1", "persistent": "false", "alarm": "false", "engineering_smoke": "false"}
    try:
        time.sleep(.7)
        fixture.publish_fixture()
        wait_for("commit", 0)
        checks.append("guarded_commit")
        index = len(fixture.decisions)
        warning({"risk_score": "invalid"})
        wait_for("stop_and_abstain", index)
        checks.append("malformed_warning_stops")
        event = DiagnosticArray()
        event.header.stamp = fixture.get_clock().now().to_msg()
        status = DiagnosticStatus()
        status.name = "research2/monitor_started"
        status.values = [KeyValue(key="event_type", value="monitor_started"),
                         KeyValue(key="engineering_smoke", value="false")]
        event.status = [status]
        index = len(fixture.decisions)
        events.publish(event)
        time.sleep(.5)
        assert not any(d.action == "commit" for d in fixture.decisions[index:])
        checks.append("readiness_cannot_clear_fault")
        index = len(fixture.decisions)
        valid = warning(nominal)
        wait_for("commit", index)
        checks.append("fresh_prediction_recovers")
        index = len(fixture.decisions)
        fixture.warning_pub.publish(valid)
        wait_for("stop_and_abstain", index)
        checks.append("replayed_prediction_stops")
        index = len(fixture.decisions)
        warning(nominal)
        wait_for("commit", index)
        index = len(fixture.decisions)
        future = fixture.get_clock().now().to_msg()
        future.sec += 30
        warning(nominal, future)
        wait_for("stop_and_abstain", index)
        checks.append("future_prediction_stops")
        index = len(fixture.decisions)
        warning(nominal)
        wait_for("commit", index)
        index = len(fixture.decisions)
        wait_for("stop_and_abstain", index)
        checks.append("silent_publisher_watchdog_stops")
    finally:
        executor.shutdown()
        for node in nodes:
            node.destroy_node()
        rclpy.shutdown()
        thread.join(timeout=2)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as stream:
            json.dump({"research_evidence": False, "passed": len(checks) == 7,
                       "checks": checks}, stream, indent=2)
    print(json.dumps({"passed": True, "checks": checks}))


if __name__ == "__main__":
    main()
