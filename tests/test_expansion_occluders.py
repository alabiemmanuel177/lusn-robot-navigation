import importlib.util
from pathlib import Path
import sys
import pytest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
SPEC=importlib.util.spec_from_file_location('occluders',ROOT/'scripts/prepare_expansion_occluders.py')
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)


@pytest.mark.parametrize('points',[[(0,0),(1,0),(1,1),(0,1)],[(0,0),(3,0),(2,2),(.2,1)]])
def test_projected_area_not_width_fraction(points):
    poly=M.hull(points)
    cut=M.area_cut(poly)
    assert M.area(M.clip_left(poly,cut))/M.area(poly)==pytest.approx(.2,abs=1e-12)


def test_degenerate_projection_refused():
    with pytest.raises(ValueError):M.area_cut([(0,0),(1,0)])


def test_rotation_identity_and_reject_invalid():
    assert np.allclose(M.rotation(dict(x=0,y=0,z=0,w=1)),np.eye(3))
    with pytest.raises(ValueError):M.rotation(dict(x=0,y=0,z=0,w=2))
