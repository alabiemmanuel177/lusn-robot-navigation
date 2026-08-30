from dataclasses import asdict

from language_nav.benchmark import CorruptionCondition, CorruptionEngine, build_corpus
from language_nav.evaluation import analyze_paired_graph_records
from language_nav.runner import PairedCampaign
from language_nav.systems import B2DeterministicWaypoints, B6ContradictionAware


def test_study_analysis_preserves_pairing_and_scope_metrics() -> None:
    route = build_corpus()[0]
    variants = tuple(
        CorruptionEngine().apply(route, condition, 0)
        for condition in (
            CorruptionCondition.TRUTHFUL_ORIGINAL,
            CorruptionCondition.ATTRIBUTE_CORRUPTION,
        )
    )
    records = PairedCampaign().run(
        (route,), variants, (B2DeterministicWaypoints(), B6ContradictionAware()), (0,)
    )
    analysis = analyze_paired_graph_records(
        [asdict(record) for record in records], bootstrap_samples=20
    )
    assert analysis["paired_blocks"] == 2
    assert analysis["paired_b6_minus_b2"]["completion_difference"]["estimate"] == 0.5
    assert analysis["paired_b6_minus_b2"]["critical_risk_difference"]["estimate"] == -0.5
