from __future__ import annotations

import rclpy
from diagnostic_msgs.msg import DiagnosticArray
from language_nav.live import MonitorStreamGuard, research2_ready_to_state, research2_warning_to_state
from language_nav_interfaces.msg import FailureMonitorState
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy


class Research2MonitorBridge(Node):
    def __init__(self) -> None:
        super().__init__("research2_monitor_bridge")
        self.stream_guard = MonitorStreamGuard()
        output_qos = QoSProfile(
            depth=2,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.publisher = self.create_publisher(
            FailureMonitorState, "/failure_monitor_state", output_qos
        )
        self.subscription = self.create_subscription(
            DiagnosticArray, "/research2/warning", self.on_warning, 10
        )
        event_qos = QoSProfile(
            depth=50,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.event_subscription = self.create_subscription(
            DiagnosticArray, "/research2/events", self.on_event, event_qos
        )

    @staticmethod
    def _stamp_ns(message: DiagnosticArray) -> int:
        return int(message.header.stamp.sec) * 1_000_000_000 + int(message.header.stamp.nanosec)

    def _publish(self, state) -> None:
        if state is None:
            return
        output = FailureMonitorState()
        output.schema_version = state.schema_version
        output.level = state.level.value
        output.failure_probability = state.failure_probability
        output.reason_codes = list(state.reason_codes)
        output.observed_at_ns = state.observed_at_ns
        self.publisher.publish(output)

    def _reject(self, reason):
        self.get_logger().error(reason)
        self._publish(self.stream_guard.invalidate(self.get_clock().now().nanoseconds))

    @staticmethod
    def _values(status):
        values = {item.key: item.value for item in status.values}
        if len(values) != len(status.values):
            raise ValueError("duplicate diagnostic keys")
        return values

    def on_event(self, message: DiagnosticArray) -> None:
        matching = [status for status in message.status if status.name == "research2/monitor_started"]
        if not matching:
            return
        if len(matching) != 1:
            self._reject("rejecting duplicate Research 2 monitor_started statuses")
            return
        observed_at_ns = self._stamp_ns(message)
        if observed_at_ns <= 0:
            # Research 2 publishes monitor_started in its constructor. With simulated
            # time enabled, that one event can precede the node's first /clock sample.
            # Receipt time is valid only for this readiness heartbeat; prediction
            # warning timestamps are never rewritten.
            observed_at_ns = self.get_clock().now().nanoseconds
        try:
            values = self._values(matching[0])
            state = research2_ready_to_state(values, observed_at_ns)
            state = self.stream_guard.accept(state, self.get_clock().now().nanoseconds)
        except (TypeError, ValueError) as exc:
            self._reject(f"rejecting Research 2 readiness event: {exc}")
            return
        self._publish(state)

    def on_warning(self, message: DiagnosticArray) -> None:
        matching = [status for status in message.status if status.name == "research2/warning"]
        if len(matching) != 1:
            self._reject("rejecting warning without exactly one research2/warning status")
            return
        try:
            values = self._values(matching[0])
            state = research2_warning_to_state(values, self._stamp_ns(message))
            state = self.stream_guard.accept(state, self.get_clock().now().nanoseconds)
        except (TypeError, ValueError) as exc:
            self._reject(f"rejecting Research 2 warning: {exc}")
            return
        self._publish(state)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = Research2MonitorBridge()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
