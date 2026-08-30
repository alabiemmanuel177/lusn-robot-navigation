from language_nav.models import ActionKind, BeliefState, RouteAssessment
from language_nav.planning import GuardedBeliefPolicy


def test_nav2_guard_has_final_authority() -> None:
    belief = BeliefState({"candidate": 1.0}, 0.9, 0.0)
    decision = GuardedBeliefPolicy().choose(
        belief,
        [RouteAssessment("unsafe", 0.01, True, False)],
    )
    assert decision.action is ActionKind.ABSTAIN
    assert not decision.guard_passed


def test_low_reliability_ignores_clause_when_safe_alternative_exists() -> None:
    belief = BeliefState({"candidate": 1.0}, 0.2, 0.8)
    decision = GuardedBeliefPolicy().choose(
        belief,
        [
            RouteAssessment("false", 0.8, True, True, uses_clause=True),
            RouteAssessment("observed", 0.1, True, True, uses_clause=False),
        ],
    )
    assert decision.action is ActionKind.IGNORE
    assert decision.route_id == "observed"

