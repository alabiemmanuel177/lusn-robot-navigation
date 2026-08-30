from __future__ import annotations

from collections.abc import Callable

from language_nav.contracts import RouteEligibility, RouteExecutionResult, RouteRequest


class Nav2ContractAdapter:
    """Dependency-injected boundary around Nav2 eligibility and execution calls."""

    def __init__(
        self,
        checker: Callable[[RouteRequest], RouteEligibility],
        executor: Callable[[RouteRequest], RouteExecutionResult],
    ) -> None:
        self._checker = checker
        self._executor = executor

    def check(self, request: RouteRequest) -> RouteEligibility:
        result = self._checker(request)
        if result.request_id != request.request_id:
            raise ValueError("Nav2 eligibility response request_id mismatch")
        return result

    def execute(self, request: RouteRequest) -> RouteExecutionResult:
        eligibility = self.check(request)
        if not eligibility.eligible:
            return RouteExecutionResult(
                request.request_id,
                False,
                (),
                0.0,
                reason=f"Nav2 guard: {eligibility.reason}",
            )
        result = self._executor(request)
        if result.request_id != request.request_id:
            raise ValueError("Nav2 execution response request_id mismatch")
        return result

