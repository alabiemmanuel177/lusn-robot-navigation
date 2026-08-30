from __future__ import annotations

from language_nav.models import ActionKind, BeliefState, Decision, RouteAssessment


class GuardedBeliefPolicy:
    def __init__(
        self,
        *,
        hard_route_risk: float = 0.35,
        ignore_clause_reliability: float = 0.35,
        inspect_min_information_gain: float = 0.18,
        abstain_all_routes_risk: float = 0.70,
    ) -> None:
        self.hard_route_risk = hard_route_risk
        self.ignore_clause_reliability = ignore_clause_reliability
        self.inspect_min_information_gain = inspect_min_information_gain
        self.abstain_all_routes_risk = abstain_all_routes_risk

    def choose(self, belief: BeliefState, routes: list[RouteAssessment]) -> Decision:
        if not routes:
            return Decision(ActionKind.ABSTAIN, None, "no candidate route", False)

        guarded = [route for route in routes if route.nav2_eligible and route.traversability_observed]
        if not guarded:
            return Decision(ActionKind.ABSTAIN, None, "Nav2 or traversability guard rejected every route", False)

        safe = [route for route in guarded if route.risk <= self.hard_route_risk]
        safe_without_clause = [route for route in safe if not route.uses_clause]
        if belief.clause_reliability < self.ignore_clause_reliability and safe_without_clause:
            route = min(safe_without_clause, key=lambda item: item.risk)
            return Decision(ActionKind.IGNORE, route.route_id, "clause reliability collapsed; safe evidence-backed route remains", True)

        inspect = [
            route
            for route in safe
            if route.expected_information_gain >= self.inspect_min_information_gain
        ]
        if belief.contradiction > 0.25 and inspect:
            route = max(inspect, key=lambda item: item.expected_information_gain)
            return Decision(ActionKind.INSPECT, route.route_id, "material contradiction with positive information gain", True)

        if safe:
            route = min(safe, key=lambda item: item.risk)
            return Decision(ActionKind.COMMIT, route.route_id, "route is observed, Nav2-eligible, and below hard risk", True)

        if min(route.risk for route in guarded) >= self.abstain_all_routes_risk:
            return Decision(ActionKind.ABSTAIN, None, "all eligible routes exceed abstention risk", True)
        return Decision(ActionKind.ABSTAIN, None, "no route satisfies the hard risk constraint", True)

