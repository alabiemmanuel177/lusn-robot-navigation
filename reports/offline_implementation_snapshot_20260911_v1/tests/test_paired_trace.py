from language_nav.benchmark.paired_trace import run_paired_trace


def test_first_meaningful_result_is_reproduced() -> None:
    trace = run_paired_trace()
    assert trace["deterministic_system"]["outcome"] == "wrong_branch_timeout"
    assert trace["belief_system"]["outcome"] == "instruction_completed"
    assert trace["belief_system"]["selected_action"] == "ignore_clause"
    assert trace["clause_reliability_after"] < 0.35
    assert trace["contradiction_after"] > 0.25
