import numpy as np
from chair_foreground_band_candidate import chair_surface_estimate


def camera():return np.array([[100,0,25],[0,100,25],[0,0,1.]])


def test_sparse_bridge_does_not_merge_object_and_wall():
    d=np.full((50,50),3.);d[15:35,15:25]=1.5
    d[15:35,25]=np.linspace(1.52,2.98,20)
    r=chair_surface_estimate(d,[0,0,50,50],camera(),np.eye(4))
    assert 1.49<r['median_depth_m']<1.6
    assert not r['foreground_selection_verified'] and not r['calibration_eligible']


def test_tiny_outlier_is_not_supported_foreground():
    d=np.full((50,50),3.);d[15:35,15:25]=1.5;d[15,15:18]=.5
    assert chair_surface_estimate(d,[0,0,50,50],camera(),np.eye(4))['median_depth_m']==1.5


def test_absent_depth_not_mapped_to_false_detection():
    assert chair_surface_estimate(np.full((50,50),np.nan),[0,0,50,50],camera(),np.eye(4))['map_pose'] is None
