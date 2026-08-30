from types import SimpleNamespace

from language_nav.adapters import NoOpFailureMonitor, RosSemanticObservationAdapter, RosbagReplayAdapter
from language_nav.contracts import MonitorLevel


def test_ros_message_and_rosbag_rows_share_contract() -> None:
    message = SimpleNamespace(
        schema_version="semantic-observation/v1", observation_id="o1", entity_id="e1", category="chair",
        attribute_keys=["color"], attribute_values=["red"], x=1, y=2, yaw=0, covariance=[0.1, 0, 0, 0.1],
        confidence=0.9, observed_at_ns=10, frame_id="map", source="research1", sequence=1, region_id="r1",
    )
    live = RosSemanticObservationAdapter.from_message(message)
    replay = RosbagReplayAdapter([
        {
            "schema_version": "semantic-observation/v1", "observation_id": "o1", "entity_id": "e1",
            "category": "chair", "attributes": {"color": "red"}, "pose": {"x": 1, "y": 2, "yaw": 0},
            "covariance": [0.1, 0, 0, 0.1], "confidence": 0.9, "observed_at_ns": 10,
            "frame_id": "map", "source": "research1", "sequence": 1, "region_id": "r1",
        }
    ]).observe()[0]
    assert live == replay


def test_noop_monitor_is_explicitly_unavailable() -> None:
    state = NoOpFailureMonitor().state()
    assert state.level is MonitorLevel.NOMINAL
    assert state.failure_probability == 0
    assert state.reason_codes == ("monitor_unavailable",)


def test_rosbag_replay_batches_observations_from_the_same_timestamp() -> None:
    common = {
        "schema_version": "semantic-observation/v1", "category": "chair",
        "attributes": {"color": "red"}, "pose": {"x": 1, "y": 2},
        "covariance": [0.1, 0, 0, 0.1], "confidence": 0.9,
        "frame_id": "map", "source": "research1", "region_id": "r1",
    }
    replay = RosbagReplayAdapter([
        {**common, "observation_id": "o3", "entity_id": "e3", "observed_at_ns": 20, "sequence": 2},
        {**common, "observation_id": "o1", "entity_id": "e1", "observed_at_ns": 10, "sequence": 1},
        {**common, "observation_id": "o2", "entity_id": "e2", "observed_at_ns": 10, "sequence": 1},
    ])
    assert {item.observation_id for item in replay.observe()} == {"o1", "o2"}
    assert [item.observation_id for item in replay.observe()] == ["o3"]
    assert replay.observe() == ()
