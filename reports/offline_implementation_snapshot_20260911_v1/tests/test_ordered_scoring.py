from copy import deepcopy
import pytest

from language_nav.evaluation.ordered import score_ordered_instruction


def annotation():
    return {"schema_version": "ordered-instruction-geometry/v1", "geometry_verified": True,
            "geometry_evidence": "synthetic unit-test geometry", "map_sha256": "fixture",
            "required_gate_ids": ["chair-past", "doorway-two"],
            "gates": [{"gate_id": name, "a": [x, 1], "b": [x, -1], "direction": 1}
                      for name, x in [("chair-past", 1), ("doorway-two", 2)]]}


def test_order_and_direction_and_terminal_are_required():
    score = lambda points, **kw: score_ordered_instruction(points, annotation(), **kw)
    assert score([(0, 0), (3, 0)], terminal_identity_correct=True)["instruction_completion"]
    assert not score([(3, 0), (0, 0)], terminal_identity_correct=True)["instruction_completion"]
    assert not score([(0, 2), (3, 2)], terminal_identity_correct=True)["instruction_completion"]
    assert not score([(0, 0), (3, 0)], terminal_identity_correct=False)["instruction_completion"]
    assert not score([(0, 0), (3, 0)], terminal_identity_correct=True, collision=True)["instruction_completion"]
    a = annotation()
    a["required_gate_ids"].reverse()
    assert not score_ordered_instruction([(0, 0), (3, 0)], a, terminal_identity_correct=True)["instruction_completion"]


def test_unverified_or_missing_evidence_never_becomes_success():
    a = deepcopy(annotation())
    a["geometry_verified"] = False
    assert score_ordered_instruction([(0, 0), (3, 0)], a, terminal_identity_correct=True)["instruction_completion"] is None
    assert score_ordered_instruction([], annotation(), terminal_identity_correct=True)["instruction_completion"] is None


def test_entering_a_forbidden_doorway_does_not_pass_after_eventual_arrival():
    a=annotation()
    a['gates'].append({'gate_id':'wrong-door', 'a':[1.5,1], 'b':[1.5,-1], 'direction':1})
    a['forbidden_gate_ids']=['wrong-door']
    result=score_ordered_instruction([(0,0),(3,0)],a,terminal_identity_correct=True)
    assert not result['instruction_completion']
    assert result['forbidden_crossings'][0]['gate_id']=='wrong-door'


@pytest.mark.parametrize("failure", [{"collision": True}, {"timeout": True}])
@pytest.mark.parametrize("positions", [[], [(0, 0), (3, 0)]])
def test_known_failure_dominates_unknown_terminal(positions, failure):
    result = score_ordered_instruction(positions, annotation(), terminal_identity_correct=None, **failure)
    assert result["instruction_completion"] is False


def test_duplicate_required_gate_is_invalid():
    a = annotation()
    a["required_gate_ids"] *= 2
    with pytest.raises(ValueError, match="unique"):
        score_ordered_instruction([(0, 0), (3, 0)], a, terminal_identity_correct=True)
