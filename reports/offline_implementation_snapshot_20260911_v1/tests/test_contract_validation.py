import pytest

from language_nav.contracts import RouteEligibility, RouteExecutionResult, RouteRequest


def test_route_contracts_reject_invalid_risk_and_distance() -> None:
    with pytest.raises(ValueError, match="maximum route risk"):
        RouteRequest("request", "region", "commit", 1.1)
    with pytest.raises(ValueError, match="route risk"):
        RouteEligibility("request", True, True, 1.0, -0.1, "invalid")
    with pytest.raises(ValueError, match="distance"):
        RouteExecutionResult("request", False, (), -1.0)
