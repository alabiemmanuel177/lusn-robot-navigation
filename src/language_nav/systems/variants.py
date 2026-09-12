from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Protocol

from language_nav.belief import initialize_belief, update_belief
from language_nav.models import (
    ActionKind,
    Evidence,
    EvidenceKind,
    GroundingCandidate,
    RouteAssessment,
)
from language_nav.parsing import RuleBasedParser
from language_nav.planning import GuardedBeliefPolicy
from language_nav.safety import assert_deployable_payload


@dataclass(frozen=True)
class SemanticRouteCandidate:
    route_id: str
    region_id: str
    anchor_entity_id: str
    anchor_category: str
    anchor_attributes: dict[str, str]
    terminal_category: str | None
    semantic_confidence: float
    observation_coverage: float
    distance: float
    risk: float
    traversability_observed: bool
    nav2_eligible: bool
    branch_index: int = 2
    side: str = "left"
    relation: str = "past"
    anchor_observation_id: str = ""
    anchor_observed_at_ns: int = 0
    anchor_observation_source: str = ""
    anchor_observation_sequence: int = -1
    terminal_observation_id: str = ""
    terminal_observed_at_ns: int = 0
    terminal_observation_source: str = ""
    terminal_observation_sequence: int = -1
    anchor_x: float | None = None
    anchor_y: float | None = None


@dataclass(frozen=True)
class SystemInput:
    instruction_id: str
    raw_text: str
    candidates: tuple[SemanticRouteCandidate, ...]
    monitor_failure_probability: float = 0.0
    step_index: int = 0

    def __post_init__(self) -> None:
        route_ids = [candidate.route_id for candidate in self.candidates]
        if len(route_ids) != len(set(route_ids)):
            raise ValueError("route hypotheses must have unique route IDs")
        assert_deployable_payload(
            {
                "instruction_id": self.instruction_id,
                "raw_text": self.raw_text,
                "candidates": self.candidates,
                "monitor_failure_probability": self.monitor_failure_probability,
            }
        )


@dataclass(frozen=True)
class SystemDecision:
    system_id: str
    action: ActionKind
    route_id: str | None
    reason: str
    guard_passed: bool
    clause_reliability: float
    contradiction: float
    candidate_probabilities: dict[str, float] = field(default_factory=dict)


class NavigationVariant(Protocol):
    system_id: str

    def decide(self, inputs: SystemInput) -> SystemDecision: ...


def _identified_observation(candidate: SemanticRouteCandidate, kind: str) -> bool:
    """Snapshot evidence is not regional search coverage or an independent view.

    The runtime observation ledger validates freshness/identity before building
    candidates. Graph-only candidates have no sensor identity and retain their
    authored evidence weighting.
    """
    stamp = getattr(candidate, kind + "_observed_at_ns")
    sequence = getattr(candidate, kind + "_observation_sequence")
    return (bool(getattr(candidate, kind + "_observation_id"))
            and bool(getattr(candidate, kind + "_observation_source"))
            and type(stamp) is int and stamp > 0
            and type(sequence) is int and sequence >= 0)


def _clauses(inputs: SystemInput):
    parsed = RuleBasedParser().parse(inputs.raw_text, inputs.instruction_id)
    landmarks = [clause for clause in parsed.clauses if clause.clause_type.value == "landmark"]
    landmark = landmarks[-1] if landmarks else None
    terminal = next((clause for clause in parsed.clauses if clause.clause_type.value == "terminal"), None)
    topology = next((clause for clause in parsed.clauses if clause.clause_type.value == "topology"), None)
    return parsed, landmark, terminal, topology


def _compatibility(target: str, attributes: dict[str, str], candidate: SemanticRouteCandidate) -> float:
    category = 1.0 if candidate.anchor_category == target else 0.05
    if attributes:
        attribute = sum(candidate.anchor_attributes.get(key) == value for key, value in attributes.items()) / len(attributes)
    else:
        attribute = 1.0
    return max(1e-5, (0.65 * category + 0.35 * attribute) * candidate.semantic_confidence)


def _guard(candidate: SemanticRouteCandidate | None, system_id: str, reason: str) -> SystemDecision:
    if candidate is None:
        return SystemDecision(system_id, ActionKind.ABSTAIN, None, reason, False, 0.0, 0.0)
    if not candidate.nav2_eligible or not candidate.traversability_observed:
        return SystemDecision(system_id, ActionKind.ABSTAIN, None, "route guard rejected selection", False, 0.0, 0.0)
    return SystemDecision(system_id, ActionKind.COMMIT, candidate.route_id, reason, True, 1.0, 0.0)


class B1CategoryExplorer:
    system_id = "B1"

    def decide(self, inputs: SystemInput) -> SystemDecision:
        _, _, terminal, _ = _clauses(inputs)
        target = terminal.alternatives[0].target if terminal else None
        matching = [candidate for candidate in inputs.candidates if candidate.terminal_category == target]
        eligible = matching or list(inputs.candidates)
        selected = min(eligible, key=lambda item: (item.distance, item.route_id), default=None)
        return _guard(selected, self.system_id, "category-only terminal exploration")


class B2DeterministicWaypoints:
    system_id = "B2"

    def decide(self, inputs: SystemInput) -> SystemDecision:
        _, landmark, _, topology = _clauses(inputs)
        if landmark is None or not inputs.candidates:
            return _guard(None, self.system_id, "no landmark clause")
        hypothesis = landmark.alternatives[0]
        topology_hypothesis = topology.alternatives[0] if topology else None

        def score(item):
            semantic = _compatibility(hypothesis.target or "", hypothesis.attributes, item)
            topology_match = 1.0 if topology_hypothesis and item.branch_index == topology_hypothesis.branch_index and item.side == topology_hypothesis.side else 0.0
            relation_match = 1.0 if item.relation == hypothesis.relation else 0.0
            return (0.85 * semantic + 0.10 * topology_match + 0.05 * relation_match, -item.distance)

        selected = max(inputs.candidates, key=score, default=None)
        return _guard(selected, self.system_id, "single highest-scoring semantic waypoint")


class _BeliefVariant:
    system_id = "belief"
    calibrated = False

    def _raw(self, hypothesis, candidate: SemanticRouteCandidate) -> float:
        score = _compatibility(hypothesis.target or "", hypothesis.attributes, candidate)
        return self._calibrate(score) if self.calibrated else score

    def _calibrate(self, score: float) -> float:
        return score

    def _belief(self, inputs: SystemInput):
        _, landmark, terminal, topology = _clauses(inputs)
        if landmark is None or not inputs.candidates:
            return None, None, terminal, {}
        hypothesis = landmark.alternatives[0]
        topology_hypothesis = topology.alternatives[0] if topology else None
        raw = {}
        for candidate in inputs.candidates:
            semantic = self._raw(hypothesis, candidate)
            topology_match = 1.0 if topology_hypothesis and candidate.branch_index == topology_hypothesis.branch_index and candidate.side == topology_hypothesis.side else 0.0
            relation_match = 1.0 if candidate.relation == hypothesis.relation else 0.0
            # Alternatives may share a physical landmark; belief is over routes.
            raw[candidate.route_id] = 0.85 * semantic + 0.10 * topology_match + 0.05 * relation_match
        total = sum(raw.values())
        groundings = [
            GroundingCandidate(
                candidate.route_id,
                candidate.region_id,
                raw[candidate.route_id] / total,
                False,
                raw[candidate.route_id],
            )
            for candidate in inputs.candidates
        ]
        belief = initialize_belief(groundings, hypothesis.epistemic_strength)
        evidence = []
        supported_anchors, contradicted_anchors = set(), set()
        observed_match = any(
            _identified_observation(candidate, "anchor")
            and candidate.anchor_category == hypothesis.target
            and all(candidate.anchor_attributes.get(key) == value for key, value in hypothesis.attributes.items())
            for candidate in inputs.candidates)
        for candidate in inputs.candidates:
            category_match = candidate.anchor_category == hypothesis.target
            attributes_match = all(candidate.anchor_attributes.get(key) == value for key, value in hypothesis.attributes.items())
            if category_match and attributes_match:
                kind = EvidenceKind.SUPPORT
            elif category_match:
                kind = EvidenceKind.CONTRADICTION
            else:
                continue
            observed = _identified_observation(candidate, "anchor")
            direct_conflict = (kind is EvidenceKind.CONTRADICTION and observed
                               and not observed_match
                               and candidate.anchor_entity_id not in contradicted_anchors)
            evidence.append(
                Evidence(
                    candidate.route_id,
                    kind,
                    candidate.semantic_confidence,
                    1.0 if observed else candidate.observation_coverage,
                    affects_clause_reliability=(kind is EvidenceKind.SUPPORT
                                                and candidate.anchor_entity_id not in supported_anchors)
                                               or direct_conflict,
                )
            )
            if kind is EvidenceKind.SUPPORT:
                supported_anchors.add(candidate.anchor_entity_id)
            elif direct_conflict:
                contradicted_anchors.add(candidate.anchor_entity_id)
        belief = update_belief(belief, evidence)
        return belief, hypothesis, terminal, {candidate.route_id: candidate for candidate in inputs.candidates}


class B4UncalibratedBelief(_BeliefVariant):
    system_id = "B4"

    def decide(self, inputs: SystemInput) -> SystemDecision:
        belief, _, _, by_entity = self._belief(inputs)
        if belief is None:
            return _guard(None, self.system_id, "no landmark clause")
        entity_id = max(belief.candidate_probabilities, key=belief.candidate_probabilities.get)
        selected = by_entity[entity_id]
        guarded = _guard(selected, self.system_id, "uncalibrated belief maximum")
        return SystemDecision(
            self.system_id,
            guarded.action,
            guarded.route_id,
            guarded.reason,
            guarded.guard_passed,
            belief.clause_reliability,
            belief.contradiction,
            belief.candidate_probabilities,
        )


class B5CalibratedFixedPolicy(B4UncalibratedBelief):
    system_id = "B5"
    calibrated = True

    def __init__(self, temperature: float = 1.6) -> None:
        if temperature <= 0:
            raise ValueError("temperature must be positive")
        self.temperature = temperature

    def _calibrate(self, score: float) -> float:
        clipped = min(1 - 1e-6, max(1e-6, score))
        logit = math.log(clipped / (1 - clipped)) / self.temperature
        return 1 / (1 + math.exp(-logit))


class B6ContradictionAware(_BeliefVariant):
    system_id = "B6"
    calibrated = True

    def __init__(self, temperature: float = 1.6) -> None:
        self.temperature = temperature
        self.policy = GuardedBeliefPolicy()

    def _calibrate(self, score: float) -> float:
        clipped = min(1 - 1e-6, max(1e-6, score))
        return 1 / (1 + math.exp(-math.log(clipped / (1 - clipped)) / self.temperature))

    def decide(self, inputs: SystemInput) -> SystemDecision:
        belief, hypothesis, terminal, by_entity = self._belief(inputs)
        if belief is None or hypothesis is None:
            return _guard(None, self.system_id, "no landmark clause")
        exact = [
            candidate
            for candidate in inputs.candidates
            if candidate.anchor_category == hypothesis.target
            and all(candidate.anchor_attributes.get(key) == value for key, value in hypothesis.attributes.items())
        ]
        if not exact:
            # One snapshot supplies one absence update, never invented viewpoints.
            target_id = max(belief.candidate_probabilities, key=belief.candidate_probabilities.get)
            coverage = max((item.observation_coverage for item in inputs.candidates), default=0.0)
            observed_attribute_conflict = any(
                _identified_observation(candidate, "anchor")
                and candidate.anchor_category == hypothesis.target
                and not all(candidate.anchor_attributes.get(key) == value for key, value in hypothesis.attributes.items())
                for candidate in inputs.candidates)
            # A visible wrong attribute supplies direct counter-evidence, not a
            # second claim that a searched region lacks the requested landmark.
            # Zero-coverage absence also must not decay genuine contradiction.
            if coverage > 0 and not observed_attribute_conflict:
                absence = [Evidence(target_id, EvidenceKind.EXPECTED_ABSENT, 0.95, coverage)]
                belief = update_belief(belief, absence)

        best_entity = max(belief.candidate_probabilities, key=belief.candidate_probabilities.get)
        clause_route = by_entity[best_entity]
        terminal_target = terminal.alternatives[0].target if terminal else None
        if terminal_target and clause_route.terminal_category not in {None, terminal_target}:
            cross_clause = [
                Evidence(
                    best_entity,
                    EvidenceKind.CONTRADICTION,
                    clause_route.semantic_confidence,
                    1.0 if _identified_observation(clause_route, "terminal") else clause_route.observation_coverage,
                )
            ]
            belief = update_belief(belief, cross_clause)
        assessments = [
            RouteAssessment(
                candidate.route_id,
                max(candidate.risk, inputs.monitor_failure_probability),
                candidate.traversability_observed,
                candidate.nav2_eligible,
                expected_information_gain=0.25 if belief.contradiction > 0.25 and candidate.route_id == clause_route.route_id else 0.0,
                uses_clause=candidate.route_id == clause_route.route_id,
            )
            for candidate in inputs.candidates
        ]
        decision = self.policy.choose(belief, assessments)
        return SystemDecision(
            self.system_id,
            decision.action,
            decision.route_id,
            decision.reason,
            decision.guard_passed,
            belief.clause_reliability,
            belief.contradiction,
            belief.candidate_probabilities,
        )


def build_central_variants() -> tuple[NavigationVariant, ...]:
    return (
        B1CategoryExplorer(),
        B2DeterministicWaypoints(),
        B4UncalibratedBelief(),
        B5CalibratedFixedPolicy(),
        B6ContradictionAware(),
    )
