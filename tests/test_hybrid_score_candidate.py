import math
import pytest
from hybrid_score_candidate import score,PASS_THROUGH
from joint_score_components import FEATURE_ORDER


@pytest.mark.parametrize('category',PASS_THROUGH)
@pytest.mark.parametrize('p',[0.,.4,.5,.8,1.])
def test_exact_passthrough_is_not_joint_probability(category,p):
    r=score(dict(category=category,raw_score=p),{})
    assert r['input_score']==p
    assert r['score_meaning']=='uncalibrated_matching_score'
    assert not r['calibration_validated'] and not r['runtime_admitted']


@pytest.mark.parametrize('p',[float('nan'),float('inf'),-.1,1.1,True])
def test_invalid_scores_fail_closed(p):
    with pytest.raises(ValueError):score(dict(category='chair',raw_score=p),{})


def test_fixed_doorway_model():
    e=dict(category='doorway',raw_score=.7,features=[1,0,.5,.2,.3],feature_order=list(FEATURE_ORDER))
    model=dict(coefficients=[0,0,0,0,0],feature_order=list(FEATURE_ORDER))
    assert score(e,model)['input_score']==.5
    e['feature_order']=list(reversed(FEATURE_ORDER))
    with pytest.raises(ValueError):score(e,model)


def test_no_unknown_class_fallback():
    with pytest.raises(ValueError):score(dict(category='sign',raw_score=.9),{})
