from __future__ import annotations

from collections.abc import Iterable

from language_nav.contracts import Pose2D, SemanticObservationContract


class RosbagReplayAdapter:
    """Replay normalized rosbag extraction rows through the live observation contract."""

    def __init__(self, rows: Iterable[dict[str, object]]) -> None:
        self._rows = iter(sorted(rows, key=lambda row: (int(row["observed_at_ns"]), int(row["sequence"]))))
        self._next: dict[str, object] | None = None

    def observe(self) -> tuple[SemanticObservationContract, ...]:
        row = self._next
        self._next = None
        if row is None:
            try:
                row = next(self._rows)
            except StopIteration:
                return ()
        observed_at_ns = int(row["observed_at_ns"])
        batch = [self._convert(row)]
        for following in self._rows:
            if int(following["observed_at_ns"]) != observed_at_ns:
                self._next = following
                break
            batch.append(self._convert(following))
        return tuple(batch)

    @staticmethod
    def _convert(row: dict[str, object]) -> SemanticObservationContract:
        pose = row["pose"]
        assert isinstance(pose, dict)
        attributes = row.get("attributes", {})
        assert isinstance(attributes, dict)
        return SemanticObservationContract(
            schema_version=str(row["schema_version"]),
            observation_id=str(row["observation_id"]),
            entity_id=str(row["entity_id"]),
            category=str(row["category"]),
            attributes={str(key): str(value) for key, value in attributes.items()},
            pose=Pose2D(float(pose["x"]), float(pose["y"]), float(pose.get("yaw", 0.0))),
            covariance=tuple(float(value) for value in row["covariance"]),
            confidence=float(row["confidence"]),
            observed_at_ns=int(row["observed_at_ns"]),
            frame_id=str(row["frame_id"]),
            source=str(row["source"]),
            sequence=int(row["sequence"]),
            region_id=str(row["region_id"]),
        )
