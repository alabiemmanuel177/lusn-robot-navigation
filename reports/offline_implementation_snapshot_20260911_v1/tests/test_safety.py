import pytest

from language_nav.safety import assert_deployable_payload


def test_evaluator_fields_are_rejected() -> None:
    with pytest.raises(ValueError, match="oracle_goal_pose"):
        assert_deployable_payload({"raw_text": "go", "oracle_goal_pose": [1, 2, 0]})


def test_deployed_fields_pass() -> None:
    assert_deployable_payload({"instruction_id": "i1", "raw_text": "go through the corridor"})

