from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class ClauseType(StrEnum):
    MOTION = "motion"
    LANDMARK = "landmark"
    TURN = "turn"
    TOPOLOGY = "topology"
    TERMINAL = "terminal"


class EvidenceKind(StrEnum):
    SUPPORT = "support"
    CONTRADICTION = "contradiction"
    EXPECTED_ABSENT = "expected_absent"


class ActionKind(StrEnum):
    COMMIT = "commit"
    INSPECT = "inspect"
    BACKTRACK = "backtrack"
    IGNORE = "ignore_clause"
    CLARIFY = "ask_clarification"
    ABSTAIN = "stop_and_abstain"


@dataclass(frozen=True)
class ParseAlternative:
    probability: float
    action: str
    target: str | None = None
    relation: str | None = None
    attributes: dict[str, str] = field(default_factory=dict)
    branch_index: int | None = None
    side: str | None = None
    epistemic_strength: float = 0.85


@dataclass(frozen=True)
class Clause:
    clause_id: str
    text: str
    clause_type: ClauseType
    alternatives: tuple[ParseAlternative, ...]


@dataclass(frozen=True)
class InstructionHypotheses:
    instruction_id: str
    raw_text: str
    parser_version: str
    clauses: tuple[Clause, ...]
    provenance: str = "hand_authored"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SemanticEntity:
    entity_id: str
    category: str
    region_id: str
    attributes: dict[str, str] = field(default_factory=dict)
    confidence: float = 1.0
    observed: bool = True


@dataclass(frozen=True)
class GroundingCandidate:
    entity_id: str
    region_id: str
    prior: float
    predicted: bool
    compatibility: float


@dataclass(frozen=True)
class Evidence:
    candidate_id: str
    kind: EvidenceKind
    semantic_confidence: float
    observation_coverage: float
    compatibility: float = 1.0
    source: str = "semantic_observation"
    affects_clause_reliability: bool = True


@dataclass(frozen=True)
class BeliefState:
    candidate_probabilities: dict[str, float]
    clause_reliability: float
    contradiction: float
    update_index: int = 0


@dataclass(frozen=True)
class RouteAssessment:
    route_id: str
    risk: float
    traversability_observed: bool
    nav2_eligible: bool
    expected_information_gain: float = 0.0
    uses_clause: bool = True


@dataclass(frozen=True)
class Decision:
    action: ActionKind
    route_id: str | None
    reason: str
    guard_passed: bool
