import numpy as np
import pytest
from candidate_pose_validation import compare_transforms,reference_consistency


def options():return dict(estimate_stamp_ns=123,truth_stamp_ns=123,truth_source='simulator_world_pose',descriptions_bound=True)


def test_exact_truth_and_error():
    a=np.eye(4);b=np.eye(4);b[0,3]=.031
    assert not compare_transforms(a,b,**options())['engineering_screen_pass']
    assert compare_transforms(a,a,**options())['engineering_screen_pass']


@pytest.mark.parametrize('key,value',[('truth_source','commanded_pose'),('truth_source','localization_tf'),('truth_stamp_ns',124),('descriptions_bound',False)])
def test_nonindependent_or_unbound_truth_rejected(key,value):
    args=options();args[key]=value
    with pytest.raises(ValueError):compare_transforms(np.eye(4),np.eye(4),**args)


def test_rotation_screen_and_reference_scope():
    b=np.eye(4);theta=.1
    b[:2,:2]=[[np.cos(theta),-np.sin(theta)],[np.sin(theta),np.cos(theta)]]
    out=compare_transforms(np.eye(4),b,**options())
    assert abs(out['rotation_error_rad']-.1)<1e-10 and not out['engineering_screen_pass']
    ref=reference_consistency([.35,0],[0,0])
    assert ref['within_existing_radius'] and not ref['instance_verified']
