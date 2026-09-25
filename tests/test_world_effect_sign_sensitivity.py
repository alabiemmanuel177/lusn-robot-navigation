import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from world_effect_sign_sensitivity import sign_limit


def test_shared_world_effect_has_positive_alternative_in_every_world():
    assert sign_limit(.85,.1,.1,1.)['limiting_unanimous_sign_rejection_probability']==1.


def test_uncorrelated_world_effects_can_prevent_target_even_with_many_repeats():
    value=sign_limit(.85,.1,.1,0.)
    assert .5<value['positive_true_world_contrast_probability']<1
    assert value['limiting_unanimous_sign_rejection_probability']<.8


def test_perfect_target_and_invalid_correlation():
    assert sign_limit(.9,.1,.1,0.)['positive_true_world_contrast_probability']==1.
    with pytest.raises(ValueError):sign_limit(.85,.1,.1,2.)
