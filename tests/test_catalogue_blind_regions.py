import math
import pytest
from catalogue_blind_regions import regions, evidence, PROMPTS


def test_fixed_rgb_dimension_only_regions():
    values = regions(640,480)
    assert len(values) == 10 and len(set(b for _,b in values)) == 10
    assert values[0] == ('full',(0,0,640,480))
    assert all(0<=a<c<=640 and 0<=b<d<=480 for _,(a,b,c,d) in values)
    with pytest.raises(ValueError): regions(0,480)


def test_visual_evidence_never_fabricates_identity_pose_or_calibration():
    result = evidence('full',(0,0,640,480),dict.fromkeys(PROMPTS, .1),100.)
    assert sum(result['relative_prompt_scores'].values()) == pytest.approx(1.)
    assert result['entity_id'] is result['map_pose'] is result['human_verdict'] is None
    assert not result['object_localized'] and not result['calibration_eligible'] and not result['runtime_admitted']


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), 2.])
def test_invalid_scores_rejected(bad):
    values = dict.fromkeys(PROMPTS,.1); values['chair'] = bad
    with pytest.raises(ValueError): evidence('full',(0,0,4,4),values,100.)


def test_stable_softmax_and_missing_classes_rejected():
    values = dict.fromkeys(PROMPTS,-1.); values['chair'] = 1.
    assert evidence('full',(0,0,4,4),values,1e4)['relative_prompt_scores']['chair'] == 1.
    values.pop('background')
    with pytest.raises(ValueError): evidence('full',(0,0,4,4),values,100.)
