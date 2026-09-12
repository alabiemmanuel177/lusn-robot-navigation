from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, replace

from language_nav.benchmark.corpus import RouteInstruction
from language_nav.benchmark.corruptions import CorruptionCondition, GeneratedVariant
from language_nav.contracts import Pose2D, RouteRequest
from language_nav.models import ActionKind
from language_nav.runner.logging import configuration_digest
from language_nav.systems.variants import NavigationVariant, SemanticRouteCandidate, SystemInput
from language_nav.world import GraphEdge, GraphLandmark, GraphNode, GraphWorld, GraphWorldAdapter


@dataclass(frozen=True)
class InterventionBudget:
    inspect: int = 1
    backtrack: int = 1
    clarify: int = 0
    abstain: int = 1


@dataclass(frozen=True)
class EpisodeOutcome:
    instruction_completion: bool
    navigation_success: bool
    collision: bool
    timeout: bool
    wrong_goal: bool
    abstained: bool
    infrastructure_failure: bool
    hallucination_induced_critical_failure: bool
    contradiction_recovery: bool


@dataclass(frozen=True)
class EpisodeRecord:
    schema_version: str
    run_id: str
    protocol_version: str
    map_id: str
    route_id: str
    base_instruction_id: str
    variant_id: str
    system_id: str
    seed: int
    configuration_digest: str
    corruption_condition: str
    raw_instruction: str
    decision: dict[str, object]
    visited_regions: tuple[str, ...]
    distance: float
    shortest_path_distance: float
    interventions: dict[str, int]
    outcome: EpisodeOutcome
    exclusion_record: str | None = None


class EpisodeRunner:
    def __init__(self, budget: InterventionBudget | None = None) -> None:
        self.budget = budget or InterventionBudget()

    def run(
        self,
        route: RouteInstruction,
        generated: GeneratedVariant,
        system: NavigationVariant,
        seed: int,
    ) -> EpisodeRecord:
        world, correct_target, decoy_target = _make_route_world(route, generated)
        adapter = GraphWorldAdapter(world)
        approach = world.shortest_path("start", "junction", observed_only=True)
        assert approach is not None
        world.execute_path(approach)
        observations = adapter.observe()
        route_candidates = _route_candidates(route, world, observations, correct_target, decoy_target)
        monitor = adapter.state()
        deployed = SystemInput(
            instruction_id=generated.deployed.variant_id,
            raw_text=generated.deployed.raw_text,
            candidates=route_candidates,
            monitor_failure_probability=monitor.failure_probability,
        )
        first_decision = system.decide(deployed)
        decisions = [first_decision]
        if first_decision.action is ActionKind.INSPECT and self.budget.inspect >= 1:
            # Re-evaluation of the same authored snapshot is NOT a new viewpoint.
            # step_index must not amplify its evidence.
            decisions.append(system.decide(replace(deployed, step_index=1)))
        if decisions[-1].action is ActionKind.INSPECT:
            decisions.append(replace(decisions[-1], action=ActionKind.ABSTAIN,
                                     route_id=None, reason="inspection requires new evidence"))
        decision = decisions[-1]
        interventions = {
            "inspect": int(any(item.action is ActionKind.INSPECT for item in decisions)),
            "backtrack": int(decision.action is ActionKind.BACKTRACK),
            "clarify": int(decision.action is ActionKind.CLARIFY),
            "abstain": int(decision.action is ActionKind.ABSTAIN),
            "ignore": int(decision.action is ActionKind.IGNORE),
        }
        budget_exceeded = (
            interventions["inspect"] > self.budget.inspect
            or interventions["backtrack"] > self.budget.backtrack
            or interventions["clarify"] > self.budget.clarify
            or interventions["abstain"] > self.budget.abstain
        )

        execution = None
        selected_target = None
        if decision.route_id is not None and not budget_exceeded and decision.action is not ActionKind.ABSTAIN:
            selected_target = correct_target if decision.route_id == "route-primary" else decoy_target
            request = RouteRequest(
                request_id=f"{generated.deployed.variant_id}:{system.system_id}",
                target_region_id=selected_target,
                semantic_intent=decision.action.value,
                maximum_risk=0.35,
            )
            execution = adapter.execute(request)

        reached_goal = bool(execution and execution.succeeded and selected_target == correct_target)
        reached_decoy = bool(execution and execution.succeeded and selected_target == decoy_target)
        abstained = decision.action is ActionKind.ABSTAIN or budget_exceeded
        infrastructure_failure = bool(execution and execution.infrastructure_failure)
        corrupted = generated.evaluator_manifest.condition not in {
            CorruptionCondition.TRUTHFUL_ORIGINAL,
            CorruptionCondition.TRUTHFUL_PARAPHRASE,
        }
        critical = corrupted and reached_decoy and decision.guard_passed
        outcome = EpisodeOutcome(
            instruction_completion=reached_goal,
            navigation_success=bool(execution and execution.succeeded),
            collision=bool(execution and execution.collision),
            timeout=not reached_goal and not reached_decoy and not abstained and not infrastructure_failure,
            wrong_goal=reached_decoy,
            abstained=abstained,
            infrastructure_failure=infrastructure_failure,
            hallucination_induced_critical_failure=critical,
            contradiction_recovery=reached_goal and decision.contradiction > 0.25,
        )
        shortest = world.path_distance(world.shortest_path("start", correct_target) or ())
        config = {
            "protocol": "1.0",
            "policy_revision": "engineering-readiness-20260910",
            "budget": asdict(self.budget),
            "system": system.system_id,
            "seed": seed,
        }
        run_material = f"{config['policy_revision']}:{route.route_id}:{generated.deployed.variant_id}:{system.system_id}:{seed}"
        run_id = hashlib.sha256(run_material.encode()).hexdigest()[:24]
        return EpisodeRecord(
            schema_version="episode-record/v1",
            run_id=run_id,
            protocol_version="1.0",
            map_id=route.map_id,
            route_id=route.route_id,
            base_instruction_id=route.base_instruction_id,
            variant_id=generated.deployed.variant_id,
            system_id=system.system_id,
            seed=seed,
            configuration_digest=configuration_digest(config),
            corruption_condition=generated.evaluator_manifest.condition.value,
            raw_instruction=generated.deployed.raw_text,
            decision={**asdict(decision), "trace": [asdict(item) for item in decisions]},
            visited_regions=tuple(world.visited),
            distance=execution.distance + 2.0 if execution else 2.0,
            shortest_path_distance=shortest,
            interventions=interventions,
            outcome=outcome,
        )


class PairedCampaign:
    def __init__(self, runner: EpisodeRunner | None = None) -> None:
        self.runner = runner or EpisodeRunner()

    def run(
        self,
        routes: tuple[RouteInstruction, ...],
        variants: tuple[GeneratedVariant, ...],
        systems: tuple[NavigationVariant, ...],
        seeds: tuple[int, ...],
    ) -> tuple[EpisodeRecord, ...]:
        variants_by_base: dict[str, list[GeneratedVariant]] = {}
        for variant in variants:
            variants_by_base.setdefault(variant.deployed.base_instruction_id, []).append(variant)
        records = []
        for route in routes:
            for generated in variants_by_base.get(route.base_instruction_id, []):
                for seed in seeds:
                    for system in systems:
                        records.append(self.runner.run(route, generated, system, seed))
        return tuple(records)


def assert_replay_equivalent(first: EpisodeRecord, replayed: EpisodeRecord) -> None:
    comparable_first = replace(first, run_id="replay", configuration_digest="replay")
    comparable_second = replace(replayed, run_id="replay", configuration_digest="replay")
    if comparable_first != comparable_second:
        raise ValueError("offline replay does not match original episode")


def _make_route_world(
    route: RouteInstruction,
    generated: GeneratedVariant,
) -> tuple[GraphWorld, str, str]:
    primary_left = route.topology_side == "left"
    primary_branch = "left_branch" if primary_left else "right_branch"
    secondary_branch = "right_branch" if primary_left else "left_branch"
    correct_target = "primary_terminal"
    decoy_target = "secondary_terminal"
    decoy_category = "office_entrance" if route.terminal_category == "laboratory_entrance" else "laboratory_entrance"
    nodes = [
        GraphNode("start", "corridor", Pose2D(0, 0)),
        GraphNode("hall", "corridor", Pose2D(1, 0)),
        GraphNode("junction", "junction", Pose2D(2, 0)),
        GraphNode("left_branch", "corridor", Pose2D(2, 1)),
        GraphNode("right_branch", "corridor", Pose2D(2, -1)),
        GraphNode(correct_target, route.terminal_category, Pose2D(3, 1 if primary_left else -1)),
        GraphNode(decoy_target, decoy_category, Pose2D(3, -1 if primary_left else 1)),
    ]
    edges = [
        GraphEdge("start", "hall", 1.0),
        GraphEdge("hall", "junction", 1.0),
        GraphEdge("junction", "left_branch", 1.0),
        GraphEdge("junction", "right_branch", 1.0),
        GraphEdge(primary_branch, correct_target, 1.0),
        GraphEdge(secondary_branch, decoy_target, 1.0),
    ]
    colors = ("red", "blue", "green", "yellow")
    color = route.anchor_attributes["color"]
    decoy_color = colors[(colors.index(color) + 1) % len(colors)]
    landmarks = [
        GraphLandmark(route.anchor_entity_id, "chair", primary_branch, {"color": color}, 0.95, 1),
        GraphLandmark(f"{route.route_id}-decoy-chair", "chair", secondary_branch, {"color": decoy_color}, 0.94, 1),
        GraphLandmark(f"{route.route_id}-terminal", route.terminal_category, correct_target, {}, 0.96, 2),
        GraphLandmark(f"{route.route_id}-decoy-terminal", decoy_category, decoy_target, {}, 0.93, 2),
    ]
    for edit in generated.evaluator_manifest.environment_edits:
        if edit["operation"] == "remove_entity":
            landmarks = [landmark for landmark in landmarks if landmark.entity_id != edit["entity_id"]]
        elif edit["operation"] == "add_decoy":
            landmarks.append(GraphLandmark(f"{route.route_id}-ambiguous-chair", "chair", secondary_branch, {"color": color}, 0.92, 1))
    return GraphWorld(route.map_id, nodes, edges, landmarks, "start"), correct_target, decoy_target


def _route_candidates(route, world, observations, correct_target, decoy_target):
    observed_by_region: dict[str, list] = {}
    for observation in observations:
        observed_by_region.setdefault(observation.region_id, []).append(observation)
    primary_branch = "left_branch" if route.topology_side == "left" else "right_branch"
    secondary_branch = "right_branch" if primary_branch == "left_branch" else "left_branch"
    branches = (("route-primary", primary_branch, correct_target), ("route-secondary", secondary_branch, decoy_target))
    candidates = []
    for route_id, branch, target in branches:
        anchor = next((item for item in observed_by_region.get(branch, []) if item.category == "chair"), None)
        terminal = next((item for item in observations if item.region_id == target), None)
        candidates.append(
            SemanticRouteCandidate(
                route_id=route_id,
                region_id=branch,
                anchor_entity_id=anchor.entity_id if anchor else f"unobserved:{branch}:chair",
                anchor_category=anchor.category if anchor else "unknown",
                anchor_attributes=dict(anchor.attributes) if anchor else {},
                terminal_category=terminal.category if terminal else None,
                semantic_confidence=anchor.confidence if anchor else 0.05,
                observation_coverage=0.95,
                distance=2.0,
                risk=0.08,
                traversability_observed=True,
                nav2_eligible=True,
                branch_index=2 if route_id == "route-primary" else 1,
                side=route.topology_side if route_id == "route-primary" else ("right" if route.topology_side == "left" else "left"),
                relation="past" if route_id == "route-primary" else "near",
            )
        )
    return tuple(candidates)
