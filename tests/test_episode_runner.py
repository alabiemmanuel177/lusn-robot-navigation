from dataclasses import replace

import pytest

from language_nav.benchmark import CorruptionCondition, CorruptionEngine, build_corpus
from language_nav.runner import EpisodeRunner, ImmutableJsonlWriter, assert_replay_equivalent, verify_jsonl
from language_nav.systems import B2DeterministicWaypoints, B6ContradictionAware


def test_paired_episode_is_deterministic_and_replay_equivalent() -> None:
    route = build_corpus()[0]
    generated = CorruptionEngine().apply(route, CorruptionCondition.ATTRIBUTE_CORRUPTION, 5)
    runner = EpisodeRunner()
    first = runner.run(route, generated, B6ContradictionAware(), 42)
    second = runner.run(route, generated, B6ContradictionAware(), 42)
    assert_replay_equivalent(first, second)
    assert first.outcome.instruction_completion
    assert first.outcome.contradiction_recovery


def test_deterministic_variant_records_wrong_goal_separately() -> None:
    route = build_corpus()[0]
    generated = CorruptionEngine().apply(route, CorruptionCondition.ATTRIBUTE_CORRUPTION, 5)
    record = EpisodeRunner().run(route, generated, B2DeterministicWaypoints(), 42)
    assert record.outcome.navigation_success
    assert record.outcome.wrong_goal
    assert record.outcome.hallucination_induced_critical_failure
    assert not record.outcome.infrastructure_failure


def test_immutable_log_checksums_and_refuses_overwrite(tmp_path) -> None:
    route = build_corpus()[0]
    generated = CorruptionEngine().apply(route, CorruptionCondition.TRUTHFUL_ORIGINAL, 1)
    record = EpisodeRunner().run(route, generated, B2DeterministicWaypoints(), 1)
    path = tmp_path / "episodes.jsonl"
    with ImmutableJsonlWriter(path) as writer:
        writer.write(record)
    loaded = verify_jsonl(path)
    assert loaded[0]["run_id"] == record.run_id
    with pytest.raises(FileExistsError):
        with ImmutableJsonlWriter(path):
            pass
