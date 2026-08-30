from language_nav.benchmark import CorruptionCondition, CorruptionEngine, build_corpus
from language_nav.benchmark.annotations import annotate_grounding
from language_nav.evaluation.campaign import summarize_campaign
from language_nav.runner import PairedCampaign
from language_nav.systems import B2DeterministicWaypoints, B6ContradictionAware


def test_ambiguous_grounding_annotation_names_both_candidates() -> None:
    route = build_corpus()[0]
    variant = CorruptionEngine().apply(route, CorruptionCondition.AMBIGUOUS_REFERENCE, 0)
    annotation = annotate_grounding(route, variant)
    assert annotation.ambiguity_flag
    assert annotation.intended_entity_id in annotation.acceptable_entity_ids
    assert len(annotation.acceptable_entity_ids) == 2
    assert annotation.evaluator_only


def test_paired_campaign_summary_keeps_completion_and_safety_together() -> None:
    route = build_corpus()[0]
    variants = (
        CorruptionEngine().apply(route, CorruptionCondition.TRUTHFUL_ORIGINAL, 0),
        CorruptionEngine().apply(route, CorruptionCondition.ATTRIBUTE_CORRUPTION, 0),
    )
    records = PairedCampaign().run((route,), variants, (B2DeterministicWaypoints(), B6ContradictionAware()), (0,))
    summary = summarize_campaign(records)
    assert summary["episodes"] == 4
    assert summary["paired_b6_minus_b2"]["blocks"] == 2
    assert all("completion_rate" in cell and "critical_failure_rate" in cell for cell in summary["cells"])
