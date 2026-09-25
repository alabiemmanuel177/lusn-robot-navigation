from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from analyze_score_feasibility_bounds import confidence_floor,error_needed_below_half


def test_high_colour_pose_consistent_detection_cannot_reach_low_bin():
    assert confidence_floor(.89,.35)>.5
    assert .35<error_needed_below_half(.89)<.9


def test_boundary_is_exact_half_and_low_colour_can_be_low_at_zero_error():
    boundary=error_needed_below_half(.89)
    assert confidence_floor(.89,boundary)==pytest.approx(.5)
    assert confidence_floor(.02,0)<.5


@pytest.mark.parametrize('c,d',[(-.1,0),(1.1,0),(.9,-1),(.9,1)])
def test_invalid_domain_rejected(c,d):
    with pytest.raises(ValueError):confidence_floor(c,d)
