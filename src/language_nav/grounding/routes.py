from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from language_nav.contracts import RouteEligibility, SemanticObservationContract
from language_nav.systems.variants import SemanticRouteCandidate


@dataclass(frozen=True)
class SemanticRouteProposal:
    """A topological route whose geometry remains owned by Research 1/Nav2."""

    route_id: str
    anchor_region_id: str
    terminal_region_id: str
    distance: float
    prior_risk: float
    observation_coverage: float
    traversability_observed: bool
    branch_index: int
    side: str
    relation: str = "past"

    def __post_init__(self) -> None:
        if not self.route_id or not self.anchor_region_id or not self.terminal_region_id:
            raise ValueError("semantic route identifiers must be non-empty")
        if self.distance < 0.0:
            raise ValueError("semantic route distance must be non-negative")
        if not 0.0 <= self.prior_risk <= 1.0:
            raise ValueError("semantic route prior risk must be in [0, 1]")
        if not 0.0 <= self.observation_coverage <= 1.0:
            raise ValueError("observation coverage must be in [0, 1]")
        if self.branch_index < 1:
            raise ValueError("branch index must be positive")
        if self.side not in {"left", "right"}:
            raise ValueError("semantic route side must be left or right")


def build_semantic_route_candidates(
    observations: Iterable[SemanticObservationContract],
    proposals: Iterable[SemanticRouteProposal],
    eligibility: Iterable[RouteEligibility],
) -> tuple[SemanticRouteCandidate, ...]:
    """Join perception and Nav2 facts without letting either replace the other."""

    observations_by_region: dict[str, list[SemanticObservationContract]] = {}
    for observation in observations:
        observations_by_region.setdefault(observation.region_id, []).append(observation)
    eligibility_by_request = {item.request_id: item for item in eligibility}

    candidates: list[SemanticRouteCandidate] = []
    for proposal in proposals:
        anchors = observations_by_region.get(proposal.anchor_region_id, [])
        anchor = max(anchors, key=lambda item: (item.confidence, item.entity_id), default=None)
        terminals = observations_by_region.get(proposal.terminal_region_id, [])
        terminal = max(terminals, key=lambda item: (item.confidence, item.entity_id), default=None)
        nav2 = eligibility_by_request.get(proposal.route_id)
        candidates.append(
            SemanticRouteCandidate(
                route_id=proposal.route_id,
                region_id=proposal.anchor_region_id,
                anchor_entity_id=(
                    anchor.entity_id
                    if anchor is not None
                    else f"unobserved:{proposal.anchor_region_id}:landmark"
                ),
                anchor_category=anchor.category if anchor is not None else "unknown",
                anchor_attributes=dict(anchor.attributes) if anchor is not None else {},
                terminal_category=terminal.category if terminal is not None else None,
                semantic_confidence=anchor.confidence if anchor is not None else 0.0,
                observation_coverage=proposal.observation_coverage,
                distance=nav2.estimated_cost if nav2 is not None else proposal.distance,
                risk=max(proposal.prior_risk, nav2.risk if nav2 is not None else 1.0),
                traversability_observed=(
                    proposal.traversability_observed
                    and nav2 is not None
                    and nav2.traversability_observed
                ),
                nav2_eligible=bool(nav2 and nav2.eligible),
                branch_index=proposal.branch_index,
                side=proposal.side,
                relation=proposal.relation,
            )
        )
    return tuple(candidates)
