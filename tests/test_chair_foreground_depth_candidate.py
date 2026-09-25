import numpy as np
from chair_foreground_depth_candidate import chair_surface_estimate


def camera():return np.array([[100,0,25],[0,100,25],[0,0,1.]])


def test_foreground_background_separation_without_catalogue():
    d=np.full((50,50),3.);d[15:35,15:25]=1.5
    r=chair_surface_estimate(d,[0,0,50,50],camera(),np.eye(4))
    assert r['status']=='chair_foreground_surface_candidate'
    assert r['median_depth_m']==1.5
    assert r['other_depth_surfaces_present']
    assert not r['foreground_selection_verified']


def test_tiny_near_noise_cannot_win_cluster():
    d=np.full((50,50),3.);d[15:35,15:25]=1.5;d[15,15:18]=.5
    r=chair_surface_estimate(d,[0,0,50,50],camera(),np.eye(4))
    assert r['median_depth_m']==1.5


def test_insufficient_or_nan_depth_abstains():
    r=chair_surface_estimate(np.full((50,50),np.nan),[0,0,50,50],camera(),np.eye(4))
    assert r['map_pose'] is None


def test_continuous_wide_depth_still_abstains():
    d=np.tile(np.linspace(.5,3,50),(50,1))
    r=chair_surface_estimate(d,[0,0,50,50],camera(),np.eye(4))
    assert r['status']=='foreground_cluster_still_mixed' and r['map_pose'] is None
