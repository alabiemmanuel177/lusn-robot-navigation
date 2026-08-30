import math

from language_nav.evaluation import (
    contradiction_recovery_rate,
    hierarchical_bootstrap,
    paired_risk_difference,
    reliability_curve,
    risk_coverage_curve,
    route_fidelity,
    spl,
)


def test_navigation_and_selective_prediction_metrics() -> None:
    assert math.isclose(spl(True, 4, 5), 0.8)
    assert spl(False, 4, 4) == 0
    assert route_fidelity(("a", "b", "c"), ("a", "b", "c")) == 1.0
    assert route_fidelity(("a", "x", "c"), ("a", "b", "c")) < 1.0
    curve = risk_coverage_curve([0.9, 0.8, 0.1], [1, 0, 0])
    assert curve[0]["risk"] == 0
    assert curve[-1]["coverage"] == 1
    assert reliability_curve([0.1, 0.9], [0, 1], bins=2)[0]["count"] == 1


def test_paired_risk_recovery_and_hierarchical_bootstrap_are_deterministic() -> None:
    assert paired_risk_difference([1, 0, 1], [0, 0, 0]) == 2 / 3
    assert contradiction_recovery_rate([True, False, True], [True, True, False]) == 0.5
    records = [
        {"map_id": "m1", "route_id": "r1", "base_instruction_id": "b1", "success": 1},
        {"map_id": "m1", "route_id": "r2", "base_instruction_id": "b2", "success": 0},
        {"map_id": "m2", "route_id": "r3", "base_instruction_id": "b3", "success": 1},
    ]
    first = hierarchical_bootstrap(records, lambda row: row["success"], samples=100, seed=9)
    second = hierarchical_bootstrap(records, lambda row: row["success"], samples=100, seed=9)
    assert first == second
    assert first.estimate == 2 / 3
