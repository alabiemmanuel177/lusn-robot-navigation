import importlib.util
from pathlib import Path
import numpy as np

spec=importlib.util.spec_from_file_location('laser_audit', Path(__file__).parents[1]/'scripts/audit_physical_laser.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_ray_box_front_back_and_parallel():
    result=module.ranges_to_boxes((0,0), np.array([0., np.pi, np.pi/2]), [(2,3,-1,1)], 20.)
    assert np.allclose(result,[2,20,20])


def test_nearest_box_and_inside_box():
    assert np.allclose(module.ranges_to_boxes((0,0), np.array([0.]), [(4,5,-1,1),(2,3,-1,1)],20),[2])
    assert np.allclose(module.ranges_to_boxes((0,0), np.array([0.]), [(-1,1,-1,1)],20),[0])
