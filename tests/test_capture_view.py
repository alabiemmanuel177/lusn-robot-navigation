from pathlib import Path
import pytest
from language_nav.capture_view import validate_capture_pose

WORLD=Path(__file__).parents[1]/'data/physical_worlds_v1/base-r010'


def test_clear_hall_view_and_explicit_yaw():
    assert validate_capture_pose(WORLD,7.5,-.6,1.57)==dict(x=7.5,y=-.6,yaw=1.57)


@pytest.mark.parametrize('pose',[(0,0,0),(-5,0,0),(2.2,.8,0),(1,0,float('nan'))])
def test_occupied_outside_nonfinite_capture_refused(pose):
    with pytest.raises(ValueError):
        validate_capture_pose(WORLD,*pose)
