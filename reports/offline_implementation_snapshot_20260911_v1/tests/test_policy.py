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


def test_ineligible_instruction_route_does_not_authorize_wrong_safe_route():
    belief = BeliefState({"right-second": .8, "left-first": .2}, .85, 0.)
    routes = [RouteAssessment("right-second", 1., False, False, uses_clause=True),
              RouteAssessment("left-first", 0., True, True, uses_clause=False)]
    assert GuardedBeliefPolicy().choose(belief, routes).action is ActionKind.ABSTAIN


def test_supported_safe_route_is_not_replaced_just_because_wrong_route_is_lower_risk():
    belief = BeliefState({"right-second": .8, "left-first": .2}, .85, 0.)
    routes = [RouteAssessment("right-second", .1, True, True, uses_clause=True),
              RouteAssessment("left-first", 0., True, True, uses_clause=False)]
    assert GuardedBeliefPolicy().choose(belief, routes).route_id == "right-second"
