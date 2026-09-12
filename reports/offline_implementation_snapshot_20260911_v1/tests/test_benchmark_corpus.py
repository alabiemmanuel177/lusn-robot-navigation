from language_nav.benchmark import CorruptionCondition, CorruptionEngine, build_corpus
from language_nav.parsing import RuleBasedParser


def test_corpus_has_twenty_parseable_bases_and_three_paraphrases_each() -> None:
    corpus = build_corpus()
    parser = RuleBasedParser()
    assert len(corpus) == 20
    assert len({item.map_id for item in corpus}) == 12
    assert {item.map_id for item in corpus} == {
        "dev_00", "dev_01", "dev_02", "dev_03", "dev_04", "dev_05",
        "val_00", "val_01", "val_02",
        "test_00", "test_01", "test_02",
    }
    assert {item.partition for item in corpus} == {"development", "validation", "held_out"}
    for route in corpus:
        assert route.platform_route_id.startswith(route.map_id + "_r")
        assert len(route.paraphrases) == 3
        parser.parse(route.canonical_text, route.base_instruction_id)
        for paraphrase in route.paraphrases:
            parser.parse(paraphrase.text, paraphrase.variant_id)


def test_all_eight_conditions_are_seeded_and_exactly_manifested() -> None:
    route = build_corpus()[0]
    engine = CorruptionEngine()
    first = engine.generate_all(route, seed=7)
    second = engine.generate_all(route, seed=7)
    assert first == second
    assert {item.evaluator_manifest.condition for item in first} == set(CorruptionCondition)
    assert len(first) == 8
    assert all(item.evaluator_manifest.evaluator_only for item in first)
    for item in first:
        for edit in item.evaluator_manifest.edits:
            assert route.canonical_text[edit.start:edit.end] == edit.before


def test_missing_landmark_changes_environment_not_instruction() -> None:
    route = build_corpus()[0]
    generated = CorruptionEngine().apply(route, CorruptionCondition.MISSING_LANDMARK, 3)
    assert generated.deployed.raw_text == route.canonical_text
    assert generated.evaluator_manifest.edits == ()
    assert generated.evaluator_manifest.environment_edits[0]["operation"] == "remove_entity"
