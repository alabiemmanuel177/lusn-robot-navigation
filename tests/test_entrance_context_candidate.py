import pytest
from entrance_context_candidate import text_category, contextual_candidates


def test_exact_context_only():
    assert text_category(' LAB ') == 'laboratory_entrance'
    assert text_category('office') == 'office_entrance'
    assert text_category('LAB OFFICE') is None
    assert text_category('OFF1CE') is None


def test_ambiguity_is_retained_not_nearest_selected():
    door=dict(xyxy=[10,10,30,50],raw_score=.4)
    texts=[dict(quad=[[10,10],[20,10],[20,20],[10,20]],text=t,score=.9) for t in ('LAB','OFFICE')]
    result=contextual_candidates([door],texts)[0]
    assert result['status']=='ambiguous_context'
    assert len(result['context'])==2
    assert result['joint_probability'] is None


def test_no_context_and_bad_geometry():
    assert contextual_candidates([dict(xyxy=[0,0,1,1],raw_score=.1)],[])[0]['status']=='no_context'
    with pytest.raises(ValueError):contextual_candidates([dict(xyxy=[0,0,0,1],raw_score=.1)],[])
