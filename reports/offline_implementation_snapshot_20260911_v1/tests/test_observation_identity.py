from dataclasses import replace

import pytest

from language_nav.contracts import Pose2D, SemanticObservationContract
from language_nav.grounding.routes import (
    ObservationIdentityLedger, SemanticRouteProposal, build_semantic_route_candidates,
)
from language_nav.systems import B6ContradictionAware, SystemInput


def observation(entity="chair", region="anchor", category="chair", sequence=1):
    return SemanticObservationContract(
        "semantic-observation/v1", f"{entity}-{sequence}", entity, category,
        {"color": "red"}, Pose2D(1, 2), (0.1, 0, 0, 0.1), 0.95,
        sequence * 100, "map", "camera", sequence, region,
    )


def test_snapshot_replay_does_not_advance_evidence_revision():
    ledger = ObservationIdentityLedger()
    old = observation()
    assert ledger.accept([old], now_ns=1000) == 1
    assert ledger.accept([old], now_ns=2000) == 1
    assert ledger.accept([observation(sequence=2)], now_ns=2000) == 2
    with pytest.raises(ValueError, match="watermark"):
        ledger.accept([old], now_ns=2000)


@pytest.mark.parametrize("change", [
    {"confidence": 0.2},
    {"observation_id": "new-id"},
    {"source": "other-camera", "observation_id": "new-id", "sequence": 2, "observed_at_ns": 200},
])
def test_identity_mutation_and_unproven_source_restart_rejected(change):
    ledger = ObservationIdentityLedger()
    old = observation()
    ledger.accept([old], now_ns=1000)
    with pytest.raises(ValueError):
        ledger.accept([replace(old, **change)], now_ns=1000)
    assert ledger.revision == 1


def test_failed_snapshot_is_atomic_and_future_observations_are_rejected():
    ledger = ObservationIdentityLedger()
    ledger.accept([observation()], now_ns=1000)
    with pytest.raises(ValueError):
        ledger.accept([observation(sequence=2), observation("door", sequence=20)], now_ns=1000)
    assert ledger.accept([observation()], now_ns=1000) == 1
    with pytest.raises(ValueError):
        ledger.accept([observation(), observation()], now_ns=1000)


def test_route_join_preserves_anchor_and_terminal_provenance_for_all_alternatives():
    proposals = tuple(SemanticRouteProposal(
        f"route-{index}", "anchor", "terminal", 4, 0.1, 0.9, True,
        index % 2 + 1, "left" if index < 2 else "right",
    ) for index in range(4))
    candidates = build_semantic_route_candidates(
        [observation(), observation("lab", "terminal", "laboratory_entrance", 2)],
        proposals, [],
    )
    assert len(candidates) == 4
    for candidate in candidates:
        assert candidate.anchor_observation_id == "chair-1"
        assert candidate.anchor_observed_at_ns == 100
        assert candidate.anchor_observation_source == "camera"
        assert candidate.anchor_observation_sequence == 1
        assert candidate.terminal_observation_id == "lab-2"
        assert candidate.terminal_observed_at_ns == 200
    policy = B6ContradictionAware()
    inputs = SystemInput("episode", "Continue past the red chair.", candidates)
    before = policy.decide(inputs)
    refreshed = policy.decide(replace(inputs, step_index=50, monitor_failure_probability=0.8))
    assert refreshed.candidate_probabilities == before.candidate_probabilities
    assert refreshed.clause_reliability == before.clause_reliability
    assert refreshed.contradiction == before.contradiction


def test_unobserved_routes_do_not_invent_observation_provenance():
    proposal = SemanticRouteProposal("r", "anchor", "terminal", 4, 0.1, 0.9, True, 1, "left")
    candidate, = build_semantic_route_candidates([], [proposal], [])
    assert candidate.anchor_observation_id == ""
    assert candidate.anchor_observed_at_ns == 0
    assert candidate.terminal_observation_id == ""


def test_ledger_capacity_and_cross_snapshot_identity_reassignment_fail_closed():
    ledger = ObservationIdentityLedger(maximum_entities=1)
    old = observation()
    ledger.accept([old], now_ns=1000)
    with pytest.raises(ValueError, match="reassigned"):
        ledger.accept([replace(old, entity_id="other")], now_ns=1000)
    with pytest.raises(ValueError, match="capacity"):
        ledger.accept([observation("door")], now_ns=1000)
    assert ledger.revision == 1


def test_physical_planner_waits_for_all_alternatives_and_all_assessments():
    # Exercise the actual pure callback gate without requiring ROS in core tests.
    import ast
    from pathlib import Path
    from types import SimpleNamespace

    path = (Path(__file__).resolve().parents[1] / "ros_ws/src/language_nav_planner/"
            "language_nav_planner/node.py")
    module = ast.parse(path.read_text())
    function = next(node for node in module.body
                    if isinstance(node, ast.FunctionDef) and node.name == "_route_set_ready")
    namespace = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), "exec"), namespace)
    ready = namespace["_route_set_ready"]
    expected = {"left-1", "left-2", "right-1", "right-2"}
    proposals = tuple(SimpleNamespace(route_id=route) for route in sorted(expected))
    assessments = {route: SimpleNamespace(eligible=False) for route in expected}
    assert not ready(expected, proposals[:1], assessments)
    assert not ready(expected, proposals, {proposals[0].route_id: assessments[proposals[0].route_id]})
    assert not ready(expected, proposals + (SimpleNamespace(route_id="unknown"),), assessments)
    assert ready(expected, proposals, assessments)
    assert ready(set(), proposals[:1], {})  # Legacy catalogue compatibility.
