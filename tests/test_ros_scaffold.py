from pathlib import Path


def test_ros_packages_and_contract_messages_are_present() -> None:
    root = Path("ros_ws/src")
    packages = {"language_nav_interfaces", "language_interface", "semantic_belief_map", "language_nav_planner", "language_nav_bringup"}
    assert all((root / package / "package.xml").exists() for package in packages)
    messages = {path.name for path in (root / "language_nav_interfaces" / "msg").glob("*.msg")}
    assert {
        "LanguageInstruction.msg",
        "SemanticObservation.msg",
        "BeliefGraph.msg",
        "LanguageNavDecision.msg",
        "RouteRequest.msg",
        "RouteEligibility.msg",
        "RouteExecutionResult.msg",
        "FailureMonitorState.msg",
        "SemanticRouteProposal.msg",
    } <= messages


def test_planner_scaffold_defaults_to_abstention_without_nav2_guard() -> None:
    source = Path("ros_ws/src/language_nav_planner/language_nav_planner/node.py").read_text()
    assert 'output.action = "stop_and_abstain"' in source
    assert "output.guard_passed = False" in source
    assert "build_semantic_route_candidates" in source
    assert "B6ContradictionAware" in source
