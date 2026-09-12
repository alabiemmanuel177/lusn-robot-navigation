from language_nav.belief import SemanticBeliefStore
from language_nav.contracts import Pose2D, SemanticObservationContract


def _observation(observation_id: str, sequence: int, observed_at_ns: int = 10):
    return SemanticObservationContract(
        "semantic-observation/v1",
        observation_id,
        "chair-1",
        "chair",
        {"color": "red"},
        Pose2D(1, 2),
        (0.1, 0.0, 0.0, 0.1),
        0.9,
        observed_at_ns,
        "map",
        "research1-bridge",
        sequence,
        "junction-1",
    )


def test_store_is_idempotent_for_replayed_observation() -> None:
    store = SemanticBeliefStore()
    observation = _observation("obs-1", 1)
    assert store.apply(observation)
    assert not store.apply(observation)
    assert store.update_index == 1


def test_store_rejects_stale_source_sequence_and_entity_timestamp() -> None:
    store = SemanticBeliefStore()
    assert store.apply(_observation("obs-2", 2, 20))
    assert not store.apply(_observation("obs-stale-sequence", 1, 30))
    assert not store.apply(_observation("obs-stale-time", 3, 19))
    assert store.snapshot()["chair-1"]["observation_id"] == "obs-2"
