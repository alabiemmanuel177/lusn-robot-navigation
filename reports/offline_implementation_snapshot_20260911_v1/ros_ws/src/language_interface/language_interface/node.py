import json

import rclpy
from language_nav.parsing import RuleBasedParser
from language_nav_interfaces.msg import LanguageHypotheses, LanguageInstruction
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy


class InstructionNode(Node):
    def __init__(self):
        super().__init__("language_interface")
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.publisher = self.create_publisher(LanguageHypotheses, "/language_hypotheses", qos)
        self.subscription = self.create_subscription(LanguageInstruction, "/language_instruction", self.on_instruction, qos)
        self.parser = RuleBasedParser()

    def on_instruction(self, message):
        if message.schema_version != "language-instruction/v1" or not message.instruction_id:
            self.get_logger().error("rejecting malformed language instruction")
            return
        parsed = self.parser.parse(message.raw_text, message.instruction_id, message.provenance)
        output = LanguageHypotheses()
        output.schema_version = "language-hypotheses/v1"
        output.instruction_id = message.instruction_id
        output.parser_version = parsed.parser_version
        output.hypotheses_json = json.dumps(parsed.to_dict(), separators=(",", ":"))
        output.published_at_ns = self.get_clock().now().nanoseconds
        self.publisher.publish(output)


def main(args=None):
    rclpy.init(args=args)
    node = InstructionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
