import pytest
from candidate_instance_association import associate


def observation():
    return dict(object_localized=True,map_pose=(0.,0.),entity_id=None,visual_category='chair')


def test_ambiguous_references_not_resolved_by_nearest_or_order():
    refs=[dict(entity_id='a',category='chair',x=.1,y=0.),dict(entity_id='b',category='chair',x=.5,y=0.)]
    result=associate(observation(),refs)
    assert result==associate(observation(),list(reversed(refs)))
    assert result['status']=='ambiguous' and result['entity_id'] is None
    assert result['joint_correctness_probability'] is None


def test_catalogue_cannot_relabel_visual_class():
    result=associate(observation(),[dict(entity_id='door',category='doorway',x=0.,y=0.)])
    assert result['status']=='unassociated' and result['visual_category']=='chair'


@pytest.mark.parametrize('change',[dict(object_localized=False),dict(map_pose=None),dict(entity_id='expected'),dict(map_pose=(float('nan'),0.))])
def test_invalid_or_oracle_input_rejected(change):
    obs=observation();obs.update(change)
    with pytest.raises(ValueError):associate(obs,[])


def test_unique_candidate_is_not_verified_identity():
    result=associate(observation(),[dict(entity_id='a',category='chair',x=.9,y=0.)])
    assert result['entity_id']=='a' and not result['identity_verified']
    assert not result['runtime_admitted'] and not result['calibration_eligible']
