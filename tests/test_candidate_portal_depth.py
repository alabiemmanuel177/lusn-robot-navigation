import numpy as np
from candidate_portal_depth import portal_estimate


def test_opening_does_not_take_back_wall_as_front_depth():
    depth=np.full((100,100),5.);depth[:,:15]=2.;depth[:,85:]=2.
    out=portal_estimate(depth,[0,0,100,100],np.array([[100,0,50],[0,100,50],[0,0,1]]),np.eye(4))
    assert out['point_xyz']==[0.,0.,2.]
    assert not out['object_identity_verified']


def test_disagreement_abstains():
    depth=np.ones((100,100));depth[:,85:]=3
    assert portal_estimate(depth,[0,0,100,100],np.eye(3),np.eye(4))['status']=='portal_sides_disagree'


def test_missing_side_abstains():
    depth=np.ones((100,100));depth[:,:15]=np.nan
    assert portal_estimate(depth,[0,0,100,100],np.eye(3),np.eye(4))['map_pose'] is None
