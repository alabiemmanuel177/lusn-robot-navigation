import numpy as np
import pytest
from candidate_depth_support import estimate


def inputs():
    return np.ones((20,20))*2,[0,0,20,20],np.array([[10.,0,10],[0,10.,10],[0,0,1.]]),np.eye(4)


def test_surface_measurement_has_no_catalogue_or_accuracy_claim():
    r=estimate(*inputs())
    assert r['status']=='visible_surface_estimate' and r['point_xyz'][2]==2.
    assert not r['covariance_calibrated'] and not r['object_identity_verified']
    assert not r['calibration_eligible'] and not r['systematic_reference_offset_estimated']


def test_insufficient_depth_not_negative_label():
    d,b,k,t=inputs();d[:]=np.nan
    r=estimate(d,b,k,t)
    assert r['status']=='insufficient_depth_support' and r['map_pose'] is None
    assert 'correct' not in r


def test_background_mixture_explicitly_flagged():
    d,b,k,t=inputs();d[:,10:]=6.
    assert estimate(d,b,k,t)['multiple_surfaces_possible']


def test_reject_nonrigid_transform_and_bad_focal_length():
    d,b,k,t=inputs();t[0,0]=2.
    with pytest.raises(ValueError):estimate(d,b,k,t)
    t=np.eye(4);k[0,0]=0.
    with pytest.raises(ValueError):estimate(d,b,k,t)
