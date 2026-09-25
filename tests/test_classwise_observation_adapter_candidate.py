from dataclasses import asdict,replace
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from classwise_observation_adapter_candidate import candidate_mapping,candidate_batch
from classwise_temperature_candidate import CLASSES,GRID,probability
from language_nav.contracts import SemanticObservationContract,Pose2D


def observation(category='chair',p=.8):
    return SemanticObservationContract('semantic-observation/v1','synthetic-observation','synthetic-entity',
        category,{'color':'red'},Pose2D(1,2,.3),(.1,0,0,.1),p,100,'map','synthetic-provider',1,'synthetic-region')


@pytest.mark.parametrize('category',CLASSES)
@pytest.mark.parametrize('p',[0.,1e-9,.1,.5,.8,1-1e-9,1.])
def test_mapping_matches_p2_and_changes_only_confidence(category,p):
    temperatures={c:GRID[200+i*200] for i,c in enumerate(CLASSES)}
    value=observation(category,p)
    result=candidate_mapping(value,temperatures,model_sha256='a'*64)
    before=asdict(value);after=asdict(result.calibrated)
    assert after.pop('confidence')==probability(p,temperatures[category])
    before.pop('confidence');assert before==after
    assert result.raw==value
    assert result.receipt['runtime_authorized'] is False
    assert result.receipt['model_approved'] is False


def test_identity_temperature_and_no_input_mutation():
    value=observation();result=candidate_mapping(value,{c:1. for c in CLASSES},model_sha256='a'*64)
    assert result.calibrated.confidence==pytest.approx(value.confidence)
    result.calibrated.attributes['color']='blue'
    assert value.attributes['color']==result.raw.attributes['color']=='red'


def test_nondetection_preserved_and_duplicates_rejected():
    temps={c:1. for c in CLASSES}
    assert candidate_batch([],temps,model_sha256='a'*64)==[]
    with pytest.raises(ValueError,match='duplicate'):candidate_batch([observation()]*2,temps,model_sha256='a'*64)
    with pytest.raises(ValueError):candidate_batch([],{},model_sha256='a'*64)


def test_calibrated_channel_preserves_belief_store_replay_guards():
    from language_nav.belief import SemanticBeliefStore
    from language_nav.grounding.routes import ObservationIdentityLedger
    value=candidate_mapping(observation(),{c:GRID[800] for c in CLASSES},model_sha256='a'*64)
    store=SemanticBeliefStore()
    assert store.apply(value.calibrated)
    assert not store.apply(value.calibrated)
    assert store.snapshot()['synthetic-entity']['confidence']==value.calibrated.confidence
    assert store.update_index==1
    ledger=ObservationIdentityLedger()
    assert ledger.accept([value.calibrated],now_ns=100)==1
    assert ledger.accept([value.calibrated],now_ns=100)==1
    # Raw and calibrated messages must not be mixed on the same consumer topic.
    with pytest.raises(ValueError,match='identity changed'):
        ledger.accept([value.raw],now_ns=100)


def test_mapped_wrapper_cannot_be_reapplied():
    temps={c:1. for c in CLASSES}
    value=candidate_mapping(observation(),temps,model_sha256='a'*64)
    with pytest.raises(TypeError):candidate_mapping(value,temps,model_sha256='a'*64)


@pytest.mark.parametrize('change',['unsupported','missing_class','off_grid','boolean','invalid_p','no_hash'])
def test_invalid_inputs_fail_closed(change):
    value=observation();temps={c:1. for c in CLASSES};digest='a'*64
    if change=='unsupported':value=replace(value,category='sign')
    elif change=='missing_class':temps.pop('chair')
    elif change=='off_grid':temps['chair']=7.
    elif change=='boolean':temps['chair']=True
    elif change=='invalid_p':value=replace(value,confidence=True)
    elif change=='no_hash':digest=''
    with pytest.raises(ValueError):candidate_mapping(value,temps,model_sha256=digest)
