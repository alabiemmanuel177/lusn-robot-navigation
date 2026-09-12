from language_nav.models import ClauseType
from language_nav.parsing import RuleBasedParser


def test_parse_protocol_example_exactly() -> None:
    parsed = RuleBasedParser().parse(
        "Go through the corridor, then continue past the red chair, then turn left after the chair, then stop near the laboratory entrance.",
        "fixture-001",
    )
    assert [clause.clause_type for clause in parsed.clauses] == [
        ClauseType.MOTION,
        ClauseType.LANDMARK,
        ClauseType.TURN,
        ClauseType.TERMINAL,
    ]
    assert parsed.clauses[1].alternatives[0].target == "chair"
    assert parsed.clauses[1].alternatives[0].attributes == {"color": "red"}
    assert parsed.clauses[2].alternatives[0].relation == "after"
    assert parsed.clauses[3].alternatives[0].target == "laboratory_entrance"


def test_parse_topology_and_epistemic_strength() -> None:
    parsed = RuleBasedParser().parse("Take the second doorway on the right.", "fixture-002")
    alternative = parsed.clauses[0].alternatives[0]
    assert alternative.branch_index == 2
    assert alternative.side == "right"

