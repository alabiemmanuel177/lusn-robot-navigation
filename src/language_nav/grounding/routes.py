from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from language_nav.contracts import RouteEligibility, SemanticObservationContract
from language_nav.systems.variants import SemanticRouteCandidate


class ObservationIdentityLedger:
    """Validate snapshot provenance without counting callbacks as new evidence.

    One ledger belongs to one instruction/episode. A newer detector frame is not
    assumed statistically independent: policies still evaluate a single snapshot.
    Updates are atomic so an invalid graph cannot partially advance watermarks.
    """

    def __init__(self, maximum_entities: int = 4096) -> None:
        if maximum_entities < 1:
            raise ValueError("observation identity capacity must be positive")
        self.maximum_entities = maximum_entities
        self._latest: dict[str, SemanticObservationContract] = {}
        self.revision = 0

    def accept(self, observations: Iterable[SemanticObservationContract], *, now_ns: int) -> int:
        pending = dict(self._latest)
        changed = False
        entities = set()
        identities = set()
        previous_owners = {
            (item.source, item.observation_id): entity_id
            for entity_id, item in self._latest.items()
        }
        for observation in observations:
            identity = (observation.source, observation.observation_id)
            if (not observation.entity_id or not all(identity)
                    or observation.sequence < 0
                    or not 0 < observation.observed_at_ns <= now_ns
                    or observation.entity_id in entities or identity in identities):
                raise ValueError("invalid, duplicate, or future observation identity")
            if previous_owners.get(identity, observation.entity_id) != observation.entity_id:
                raise ValueError("observation identity reassigned to another entity")
            entities.add(observation.entity_id)
            identities.add(identity)
            previous = pending.get(observation.entity_id)
            if previous is not None:
                if observation == previous:
                    continue
                if (observation.source != previous.source
                        or observation.observation_id == previous.observation_id
                        or observation.sequence <= previous.sequence
                        or observation.observed_at_ns <= previous.observed_at_ns):
                    raise ValueError("observation identity changed or watermark regressed")
            pending[observation.entity_id] = observation
            changed = True
        if len(pending) > self.maximum_entities:
            raise ValueError("observation identity capacity exceeded")
        self._latest = pending
        self.revision += int(changed)
        return self.revision


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
                anchor_observation_id=anchor.observation_id if anchor else "",
                anchor_observed_at_ns=anchor.observed_at_ns if anchor else 0,
                anchor_observation_source=anchor.source if anchor else "",
                anchor_observation_sequence=anchor.sequence if anchor else -1,
                anchor_x=anchor.pose.x if anchor and anchor.frame_id == "map" else None,
                anchor_y=anchor.pose.y if anchor and anchor.frame_id == "map" else None,
                terminal_observation_id=terminal.observation_id if terminal else "",
                terminal_observed_at_ns=terminal.observed_at_ns if terminal else 0,
                terminal_observation_source=terminal.source if terminal else "",
                terminal_observation_sequence=terminal.sequence if terminal else -1,
            )
        )
    return tuple(candidates)
