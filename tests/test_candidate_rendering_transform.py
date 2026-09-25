import numpy as np
import pytest
from candidate_rendering_transform import rigid, correction, described_mounts
from expansion_camera_model import rotation_from_rpy
from finalize_steps14_candidate import quaternion_rotation


@pytest.mark.parametrize('rpy',[(0,0,0),(.1,-.2,1.2),(-.3,.2,-2.)])
def test_recovers_render_transform_without_commanded_pose(rpy):
    nominal,rendered=described_mounts()
    actual_base=rigid(rotation_from_rpy(*rpy),[3,4,.002])
    recorded=actual_base@nominal
    assert np.allclose(correction(recorded,nominal,rendered),actual_base@rendered)
    # Passing nominal TF directly produces the original extrinsic error.
    assert np.linalg.norm(recorded[:3,3]-(actual_base@rendered)[:3,3])>.13


def test_improper_transform_rejected():
    nominal,rendered=described_mounts()
    bad=np.eye(4);bad[0,0]=-1
    with pytest.raises(ValueError):correction(bad,nominal,rendered)


def test_quaternion_contract():
    assert np.allclose(quaternion_rotation(dict(x=0,y=0,z=0,w=1)),np.eye(3))
    with pytest.raises(ValueError):quaternion_rotation(dict(x=0,y=0,z=0,w=2))
