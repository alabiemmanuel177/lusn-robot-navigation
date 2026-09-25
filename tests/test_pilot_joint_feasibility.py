import pytest
from audit_pilot_joint_feasibility import consistent


def test_reference_threshold_is_inclusive_and_not_a_human_label():
    reference = {'pose': {'x': 0., 'y': 0., 'yaw': 0.}}
    result = consistent({'x': .35, 'y': 0., 'yaw': 0.}, reference)
    assert result['necessary_pose_rule_passed']
    assert 'correct' not in result and 'human_verdict' not in result
    assert not consistent({'x': .350001, 'y': 0., 'yaw': 0.}, reference)['necessary_pose_rule_passed']


def test_reject_nonfinite_and_check_catalogue_yaw_only():
    reference = {'pose': {'x': 0., 'y': 0., 'yaw': 0.}}
    with pytest.raises(ValueError): consistent({'x': float('nan'), 'y': 0., 'yaw': 0.}, reference)
    assert not consistent({'x': 0., 'y': 0., 'yaw': .1}, reference)['necessary_pose_rule_passed']
