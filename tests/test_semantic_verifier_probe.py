import math
import pytest
from semantic_verifier_probe import crop_box,PROMPTS


@pytest.mark.parametrize('u,v',[(0,0),(639,479),(320,240),(10,240)])
def test_context_preserves_target_and_fixed_size(u,v):
    x0,y0,x1,y1=crop_box(640,480,u,v)
    assert x1-x0==y1-y0==256
    assert 0<=x0<=u<x1<=640 and 0<=y0<=v<y1<=480


@pytest.mark.parametrize('u,v',[(-1,0),(640,100),(0,480),(math.nan,0)])
def test_bad_pixel_rejected(u,v):
    with pytest.raises(ValueError):crop_box(640,480,u,v)


def test_prompt_bank_has_nontarget_alternatives():
    assert set(PROMPTS)=={'chair','doorway','laboratory_entrance','office_entrance','sign','background'}
    assert len(set(PROMPTS.values()))==6
