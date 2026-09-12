"""Offline diagnostic construction safety; no simulator or human labels."""
import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
SPEC = importlib.util.spec_from_file_location('expansion_shapes', ROOT/'scripts/prepare_expansion_distractors.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def test_fixed_map_only_sphere_placement():
    pose, clearance, offset = M.place_sphere({'x':2.,'y':0.}, {'x':0.,'y':0.},
        [{'x':0.,'y':2.,'sx':20.,'sy':.1}])
    assert pose == [1.55,0.,.2]
    assert offset == .45
    assert clearance >= .22


def test_no_safe_candidate_fails_closed():
    with pytest.raises(ValueError, match='no prespecified'):
        M.place_sphere({'x':2.,'y':0.}, {'x':0.,'y':0.},
                      [{'x':1.,'y':0.,'sx':20.,'sy':20.}])


def test_coincident_camera_rejected():
    with pytest.raises(ValueError, match='coincide'):
        M.place_sphere({'x':0.,'y':0.}, {'x':0.,'y':0.}, [])


@pytest.mark.parametrize('number,partition', [(11,'validation'),(15,'test'),(1,'test')])
def test_scope_rejected_before_missing_source_reads(tmp_path, number, partition):
    with pytest.raises(PermissionError):
        M.build(tmp_path, {'map_id':f'r3geo_base_r{number:03}',
                          'partition':partition,'seed':1},tmp_path/'output')


def test_nonzero_view_rejected_before_source_reads(tmp_path):
    with pytest.raises(ValueError,match='original view'):
        M.build(tmp_path, {'map_id':'r3geo_base_r001','partition':'development',
                          'seed':1,'candidate_id':'expansion-v1-r001-chair-s1-view1'},tmp_path/'output')
