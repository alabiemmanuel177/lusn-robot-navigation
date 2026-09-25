import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_stage1_view_feasibility import wall_ray_clear


def test_intersecting_and_disjoint_walls():
    wall=dict(x=2,y=0,sx=.2,sy=2)
    assert not wall_ray_clear([wall],(0,0),(4,0))
    assert wall_ray_clear([wall],(0,2),(4,2))


def test_wall_beyond_target_not_obstruction():
    assert wall_ray_clear([dict(x=5,y=0,sx=.2,sy=2)],(0,0),(4,0))


def test_vertical_ray_and_close_target():
    assert not wall_ray_clear([dict(x=0,y=2,sx=2,sy=.2)],(0,0),(0,4))
    assert not wall_ray_clear([],(0,0),(.2,0))


def test_no_walls_does_not_claim_visibility():
    assert wall_ray_clear([],(0,0),(4,0))
