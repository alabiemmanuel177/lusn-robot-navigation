import math

from language_nav.belief import initialize_belief, update_belief
from language_nav.models import Evidence, EvidenceKind, GroundingCandidate


def _candidates() -> list[GroundingCandidate]:
    return [
        GroundingCandidate("a", "left", 0.6, False, 0.8),
        GroundingCandidate("b", "right", 0.4, True, 0.6),
    ]


def test_belief_is_finite_bounded_and_normalized() -> None:
    state = initialize_belief(_candidates())
    updated = update_belief(state, [Evidence("a", EvidenceKind.SUPPORT, 0.9, 0.8)])
    assert math.isclose(sum(updated.candidate_probabilities.values()), 1.0)
    assert all(math.isfinite(value) and 0 <= value <= 1 for value in updated.candidate_probabilities.values())
    assert 0 <= updated.clause_reliability <= 1


def test_support_and_contradiction_have_expected_direction() -> None:
    state = initialize_belief(_candidates())
    supported = update_belief(state, [Evidence("a", EvidenceKind.SUPPORT, 1.0, 1.0)])
    contradicted = update_belief(state, [Evidence("a", EvidenceKind.CONTRADICTION, 1.0, 1.0)])
    assert supported.candidate_probabilities["a"] > state.candidate_probabilities["a"]
    assert contradicted.candidate_probabilities["a"] < state.candidate_probabilities["a"]
    assert contradicted.clause_reliability < state.clause_reliability


def test_one_frame_contribution_is_capped() -> None:
    state = initialize_belief(_candidates())
    ordinary = update_belief(state, [Evidence("a", EvidenceKind.SUPPORT, 1.0, 1.0)], max_log_odds_contribution=0.2)
    extreme = update_belief(state, [Evidence("a", EvidenceKind.SUPPORT, 99.0, 99.0)], max_log_odds_contribution=0.2)
    assert ordinary == extreme


def test_rejected_alternative_does_not_imply_clause_is_false() -> None:
    state = initialize_belief(_candidates())
    updated = update_belief(
        state,
        [Evidence("b", EvidenceKind.CONTRADICTION, 1.0, 1.0, affects_clause_reliability=False)],
    )
    assert updated.candidate_probabilities["b"] < state.candidate_probabilities["b"]
    assert updated.clause_reliability == state.clause_reliability
    assert updated.contradiction == 0
