import numpy as np
import pytest
from bound_pose_observer import matrix
from run_bound_pose_preflight import mounts


def test_quaternion_and_invalid_norm():
    assert np.allclose(matrix([1,2,3],[0,0,0,1])[:3,3],[1,2,3])
    with pytest.raises(ValueError):matrix([0,0,0],[0,0,0,2])


def test_mounts_exclude_spawn_and_inertial_offset():
    sdf='''<sdf><model><link name="camera_link"><inertial><pose>9 9 9 0 0 0</pose></inertial><pose>0.069 -0.047 0.107 0 0 0</pose><sensor name="rcn_rgbd"><pose>0.064 -0.047 0.107 0 0 0</pose></sensor></link></model></sdf>'''
    urdf='''<robot><joint type="fixed"><parent link="base_footprint"/><child link="camera_depth_frame"/><origin xyz="0.069 -0.037 0.117" rpy="-1.57 0 -1.57"/></joint></robot>'''
    nominal,rendered=mounts(sdf,urdf)
    assert np.allclose(rendered[:3,3],[.133,-.094,.214])
    assert np.allclose(nominal[:3,3],[.069,-.037,.117])
