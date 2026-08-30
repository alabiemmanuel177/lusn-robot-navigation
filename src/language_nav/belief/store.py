from __future__ import annotations

from dataclasses import dataclass

from language_nav.contracts import Pose2D, SemanticObservationContract


@dataclass(frozen=True)
class StoredSemanticEntity:
    category: str
    attributes: dict[str, str]
    confidence: float
    region_id: str
    observed_at_ns: int
    observation_id: str
    source: str
    sequence: int
    pose: Pose2D
    covariance: tuple[float, float, float, float]
    frame_id: str


class SemanticBeliefStore:
    """Idempotent, freshness-aware storage for live/replayed observations."""

    def __init__(self) -> None:
        self._entities: dict[str, StoredSemanticEntity] = {}
        self._observation_ids: set[str] = set()
        self._last_sequence: dict[str, int] = {}
        self.update_index = 0

    def apply(self, observation: SemanticObservationContract) -> bool:
        if observation.observation_id in self._observation_ids:
            return False
        last_sequence = self._last_sequence.get(observation.source, -1)
        if observation.sequence < last_sequence:
            return False
        current = self._entities.get(observation.entity_id)
        if current is not None and observation.observed_at_ns < current.observed_at_ns:
            return False

        self._observation_ids.add(observation.observation_id)
        self._last_sequence[observation.source] = max(last_sequence, observation.sequence)
        self._entities[observation.entity_id] = StoredSemanticEntity(
            category=observation.category,
            attributes=dict(observation.attributes),
            confidence=observation.confidence,
            region_id=observation.region_id,
            observed_at_ns=observation.observed_at_ns,
            observation_id=observation.observation_id,
            source=observation.source,
            sequence=observation.sequence,
            pose=observation.pose,
            covariance=observation.covariance,
            frame_id=observation.frame_id,
        )
        self.update_index += 1
        return True

    def snapshot(self) -> dict[str, dict[str, object]]:
        return {
            entity_id: {
                "category": entity.category,
                "attributes": dict(entity.attributes),
                "confidence": entity.confidence,
                "region_id": entity.region_id,
                "observed_at_ns": entity.observed_at_ns,
                "observation_id": entity.observation_id,
                "source": entity.source,
                "sequence": entity.sequence,
                "pose": {
                    "x": entity.pose.x,
                    "y": entity.pose.y,
                    "yaw": entity.pose.yaw,
                },
                "covariance": list(entity.covariance),
                "frame_id": entity.frame_id,
            }
            for entity_id, entity in sorted(self._entities.items())
        }
