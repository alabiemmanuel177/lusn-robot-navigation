from __future__ import annotations

from language_nav.contracts import Pose2D, SemanticObservationContract


class RosSemanticObservationAdapter:
    """Duck-typed conversion so core tests do not require a ROS installation."""

    @staticmethod
    def from_message(message) -> SemanticObservationContract:
        attributes = dict(zip(message.attribute_keys, message.attribute_values, strict=True))
        return SemanticObservationContract(
            schema_version=message.schema_version,
            observation_id=message.observation_id,
            entity_id=message.entity_id,
            category=message.category,
            attributes=attributes,
            pose=Pose2D(float(message.x), float(message.y), float(message.yaw)),
            covariance=tuple(float(value) for value in message.covariance),
            confidence=float(message.confidence),
            observed_at_ns=int(message.observed_at_ns),
            frame_id=message.frame_id,
            source=message.source,
            sequence=int(message.sequence),
            region_id=message.region_id,
        )

