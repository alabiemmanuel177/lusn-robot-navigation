from __future__ import annotations

import rclpy
from language_nav.benchmark.semantic_catalog import load_semantic_route_catalog
from language_nav.benchmark.physical_catalog import load_physical_runtime_catalog
from language_nav.live import base_instruction_id
from language_nav_interfaces.msg import LanguageHypotheses, SemanticRouteProposal
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy


class SemanticRouteNode(Node):
    def __init__(self) -> None:
        super().__init__("semantic_route_provider")
        self.declare_parameter("catalog", "")
        self.declare_parameter("physical_catalog", "")
        self.declare_parameter("research1_repository", "/home/eao/risk-calibrated-nav")
        catalog_path = str(self.get_parameter("catalog").value)
        physical_path = str(self.get_parameter("physical_catalog").value)
        from language_nav.physical_heldout_authorization import node_authorization
        heldout = node_authorization(self)
        if heldout is not None and not physical_path:
            raise PermissionError('held-out authorization requires a physical catalogue')
        if physical_path:
            self.catalog = load_physical_runtime_catalog(physical_path, heldout_authorization=heldout).semantic
        elif not catalog_path:
            raise ValueError("catalog parameter is required")
        else:
            self.catalog = load_semantic_route_catalog(
                catalog_path,
                str(self.get_parameter("research1_repository").value),
                allow_protected=False,
            )
        qos = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.publisher = self.create_publisher(
            SemanticRouteProposal, "/language_nav/route_proposals", qos
        )
        self.subscription = self.create_subscription(
            LanguageHypotheses, "/language_hypotheses", self.on_hypotheses, qos
        )

    def on_hypotheses(self, message: LanguageHypotheses) -> None:
        if message.schema_version != "language-hypotheses/v1":
            self.get_logger().error("rejecting unsupported hypothesis schema")
            return
        try:
            base_id = base_instruction_id(message.instruction_id)
        except ValueError as exc:
            self.get_logger().error(str(exc))
            return
        matches = [route for route in self.catalog.routes if route.base_instruction_id == base_id]
        if not matches:
            self.get_logger().error(
                f"instruction {message.instruction_id} has no route in {self.catalog.map_id}"
            )
            return
        for route in matches:
            proposal = route.proposal
            output = SemanticRouteProposal()
            output.schema_version = "semantic-route-proposal/v1"
            output.instruction_id = message.instruction_id
            output.route_id = proposal.route_id
            output.anchor_region_id = proposal.anchor_region_id
            output.terminal_region_id = proposal.terminal_region_id
            output.distance = proposal.distance
            output.prior_risk = proposal.prior_risk
            output.observation_coverage = proposal.observation_coverage
            output.traversability_observed = proposal.traversability_observed
            output.branch_index = proposal.branch_index
            output.side = proposal.side
            output.relation = proposal.relation
            output.proposed_at_ns = self.get_clock().now().nanoseconds
            self.publisher.publish(output)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SemanticRouteNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
