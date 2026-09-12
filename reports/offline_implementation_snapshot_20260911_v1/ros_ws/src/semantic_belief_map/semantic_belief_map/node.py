import json

import rclpy
from language_nav.adapters import RosSemanticObservationAdapter
from language_nav.belief import SemanticBeliefStore
from language_nav_interfaces.msg import BeliefGraph, LanguageHypotheses, SemanticObservation
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy


class BeliefMapNode(Node):
    def __init__(self):
        super().__init__("semantic_belief_map")
        observation_qos = QoSProfile(depth=20, reliability=ReliabilityPolicy.RELIABLE)
        state_qos = QoSProfile(
            depth=2,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        instruction_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.publisher = self.create_publisher(BeliefGraph, "/belief_graph", state_qos)
        self.observation_subscription = self.create_subscription(
            SemanticObservation, "/semantic_observations", self.on_observation, observation_qos
        )
        self.hypothesis_subscription = self.create_subscription(
            LanguageHypotheses, "/language_hypotheses", self.on_hypotheses, instruction_qos
        )
        self.store = SemanticBeliefStore()
        self.instruction_id = ""

    def on_hypotheses(self, message):
        if message.schema_version != "language-hypotheses/v1" or not message.instruction_id:
            self.get_logger().error("rejecting malformed language hypotheses")
            return
        self.instruction_id = message.instruction_id
        self.publish_graph()

    def on_observation(self, message):
        try:
            observation = RosSemanticObservationAdapter.from_message(message)
        except (TypeError, ValueError) as exc:
            self.get_logger().error(f"rejecting malformed semantic observation: {exc}")
            return
        if not self.store.apply(observation):
            self.get_logger().warning(
                f"ignoring duplicate or stale observation {observation.observation_id}"
            )
            return
        self.publish_graph()

    def publish_graph(self):
        output = BeliefGraph()
        output.schema_version = "belief-graph/v1"
        output.instruction_id = self.instruction_id
        output.graph_json = json.dumps(
            {"entities": self.store.snapshot()}, separators=(",", ":"), sort_keys=True
        )
        output.update_index = self.store.update_index
        output.published_at_ns = self.get_clock().now().nanoseconds
        self.publisher.publish(output)


def main(args=None):
    rclpy.init(args=args)
    node = BeliefMapNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
