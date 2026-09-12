from __future__ import annotations

import hashlib
import heapq
import math
from dataclasses import dataclass, field, replace

from language_nav.contracts import (
    FailureMonitorState,
    MonitorLevel,
    Pose2D,
    RouteEligibility,
    RouteExecutionResult,
    RouteRequest,
    SemanticObservationContract,
)


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    kind: str
    pose: Pose2D


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    distance: float
    traversable: bool = True
    observed: bool = True


@dataclass(frozen=True)
class GraphLandmark:
    entity_id: str
    category: str
    node_id: str
    attributes: dict[str, str] = field(default_factory=dict)
    confidence: float = 0.95
    visibility_hops: int = 0


class GraphWorld:
    """Deterministic topological world used before Gazebo is available."""

    def __init__(
        self,
        world_id: str,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
        landmarks: list[GraphLandmark],
        start_node: str,
    ) -> None:
        self.world_id = world_id
        self.nodes = {node.node_id: node for node in nodes}
        self.edges = tuple(edges)
        self.landmarks = {landmark.entity_id: landmark for landmark in landmarks}
        if start_node not in self.nodes:
            raise ValueError("start node is absent from graph")
        self.current_node = start_node
        self.sequence = 0
        self.clock_ns = 0
        self.visited = [start_node]
        self._validate()

    def _validate(self) -> None:
        for edge in self.edges:
            if edge.source not in self.nodes or edge.target not in self.nodes:
                raise ValueError(f"edge references unknown node: {edge}")
            if edge.distance <= 0:
                raise ValueError("edge distances must be positive")
        for landmark in self.landmarks.values():
            if landmark.node_id not in self.nodes:
                raise ValueError(f"landmark {landmark.entity_id} references unknown node")

    def clone(self) -> GraphWorld:
        return GraphWorld(
            self.world_id,
            list(self.nodes.values()),
            list(self.edges),
            list(self.landmarks.values()),
            self.current_node,
        )

    def without_landmark(self, entity_id: str) -> GraphWorld:
        clone = self.clone()
        clone.landmarks.pop(entity_id, None)
        return clone

    def with_blocked_edge(self, source: str, target: str) -> GraphWorld:
        clone = self.clone()
        clone.edges = tuple(
            replace(edge, traversable=False)
            if {edge.source, edge.target} == {source, target}
            else edge
            for edge in clone.edges
        )
        return clone

    def neighbors(self, node_id: str, *, observed_only: bool = False) -> tuple[tuple[str, GraphEdge], ...]:
        neighbors: list[tuple[str, GraphEdge]] = []
        for edge in self.edges:
            if not edge.traversable or (observed_only and not edge.observed):
                continue
            if edge.source == node_id:
                neighbors.append((edge.target, edge))
            elif edge.target == node_id:
                neighbors.append((edge.source, edge))
        return tuple(sorted(neighbors, key=lambda item: item[0]))

    def shortest_path(self, start: str, goal: str, *, observed_only: bool = False) -> tuple[str, ...] | None:
        queue: list[tuple[float, str, tuple[str, ...]]] = [(0.0, start, (start,))]
        best: dict[str, float] = {}
        while queue:
            cost, node_id, path = heapq.heappop(queue)
            if node_id == goal:
                return path
            if cost >= best.get(node_id, math.inf):
                continue
            best[node_id] = cost
            for neighbor, edge in self.neighbors(node_id, observed_only=observed_only):
                heapq.heappush(queue, (cost + edge.distance, neighbor, path + (neighbor,)))
        return None

    def path_distance(self, path: tuple[str, ...]) -> float:
        total = 0.0
        for source, target in zip(path, path[1:], strict=False):
            match = next(
                edge for edge in self.edges if {edge.source, edge.target} == {source, target}
            )
            total += match.distance
        return total

    def hop_distance(self, start: str, goal: str) -> int | None:
        path = self.shortest_path(start, goal)
        return None if path is None else len(path) - 1

    def visible_landmarks(self) -> tuple[GraphLandmark, ...]:
        visible = []
        for landmark in self.landmarks.values():
            distance = self.hop_distance(self.current_node, landmark.node_id)
            if distance is not None and distance <= landmark.visibility_hops:
                visible.append(landmark)
        return tuple(sorted(visible, key=lambda item: item.entity_id))

    def observe(self) -> tuple[SemanticObservationContract, ...]:
        observations: list[SemanticObservationContract] = []
        for landmark in self.visible_landmarks():
            self.sequence += 1
            self.clock_ns += 100_000_000
            pose = self.nodes[landmark.node_id].pose
            digest = hashlib.sha256(
                f"{self.world_id}:{self.sequence}:{landmark.entity_id}".encode()
            ).hexdigest()[:16]
            observations.append(
                SemanticObservationContract(
                    schema_version="semantic-observation/v1",
                    observation_id=f"obs-{digest}",
                    entity_id=landmark.entity_id,
                    category=landmark.category,
                    attributes=dict(landmark.attributes),
                    pose=pose,
                    covariance=(0.04, 0.0, 0.0, 0.04),
                    confidence=landmark.confidence,
                    observed_at_ns=self.clock_ns,
                    frame_id="map",
                    source="graph-world",
                    sequence=self.sequence,
                    region_id=landmark.node_id,
                )
            )
        return tuple(observations)

    def execute_path(self, path: tuple[str, ...]) -> RouteExecutionResult:
        request_id = f"graph-path-{self.sequence + 1}"
        if not path or path[0] != self.current_node:
            return RouteExecutionResult(request_id, False, tuple(self.visited), 0.0, reason="path does not start at robot")
        distance = 0.0
        for source, target in zip(path, path[1:], strict=False):
            edge = next(
                (edge for edge in self.edges if {edge.source, edge.target} == {source, target}),
                None,
            )
            if edge is None or not edge.traversable:
                return RouteExecutionResult(request_id, False, tuple(self.visited), distance, reason="edge unavailable")
            distance += edge.distance
            self.current_node = target
            self.visited.append(target)
            self.clock_ns += int(edge.distance * 1_000_000_000)
        return RouteExecutionResult(request_id, True, tuple(path), distance)


class GraphWorldAdapter:
    """Implements the same observation, route, and monitor contracts as ROS adapters."""

    def __init__(self, world: GraphWorld) -> None:
        self.world = world

    def observe(self) -> tuple[SemanticObservationContract, ...]:
        return self.world.observe()

    def check(self, request: RouteRequest) -> RouteEligibility:
        if request.target_region_id not in self.world.nodes:
            return RouteEligibility(request.request_id, False, False, math.inf, 1.0, "unknown target region")
        path = self.world.shortest_path(self.world.current_node, request.target_region_id, observed_only=True)
        if path is None:
            return RouteEligibility(request.request_id, False, False, math.inf, 1.0, "no observed traversable path")
        cost = self.world.path_distance(path)
        risk = min(0.3, 0.02 * max(0, len(path) - 1))
        eligible = risk <= request.maximum_risk
        return RouteEligibility(request.request_id, eligible, True, cost, risk, "eligible" if eligible else "risk threshold")

    def execute(self, request: RouteRequest) -> RouteExecutionResult:
        eligibility = self.check(request)
        if not eligibility.eligible:
            return RouteExecutionResult(request.request_id, False, tuple(self.world.visited), 0.0, reason=eligibility.reason)
        path = self.world.shortest_path(self.world.current_node, request.target_region_id, observed_only=True)
        assert path is not None
        result = self.world.execute_path(path)
        return replace(result, request_id=request.request_id)

    def state(self) -> FailureMonitorState:
        return FailureMonitorState("failure-monitor/v1", MonitorLevel.NOMINAL, 0.02, (), self.world.clock_ns)


def make_fixture_world(world_id: str = "fixture-graph-01") -> GraphWorld:
    nodes = [
        GraphNode("start", "corridor", Pose2D(0, 0)),
        GraphNode("hall", "corridor", Pose2D(1, 0)),
        GraphNode("junction", "junction", Pose2D(2, 0)),
        GraphNode("left_branch", "corridor", Pose2D(2, 1)),
        GraphNode("right_branch", "corridor", Pose2D(2, -1)),
        GraphNode("goal", "laboratory_entrance", Pose2D(3, 1)),
        GraphNode("decoy", "office_entrance", Pose2D(3, -1)),
    ]
    edges = [
        GraphEdge("start", "hall", 1.0),
        GraphEdge("hall", "junction", 1.0),
        GraphEdge("junction", "left_branch", 1.0),
        GraphEdge("junction", "right_branch", 1.0),
        GraphEdge("left_branch", "goal", 1.0),
        GraphEdge("right_branch", "decoy", 1.0),
    ]
    landmarks = [
        GraphLandmark("chair-red", "chair", "left_branch", {"color": "red"}, visibility_hops=1),
        GraphLandmark("chair-blue", "chair", "right_branch", {"color": "blue"}, visibility_hops=1),
        GraphLandmark("lab-entrance", "laboratory_entrance", "goal", {}, visibility_hops=1),
        GraphLandmark("office-entrance", "office_entrance", "decoy", {}, visibility_hops=1),
    ]
    return GraphWorld(world_id, nodes, edges, landmarks, "start")

