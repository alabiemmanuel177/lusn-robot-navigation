import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from expansion_sampling import classify_attempt


def classify(rows,**changes):
    args=dict(frame_stamp_ns=10,entity_id='target',category='chair',armed=True,
              frame_present=True,synchronization_valid=True,transform_valid=True,
              observation_window_complete=True,interrupted=False)
    args.update(changes)
    return classify_attempt(rows,**args)


def emission(entity='target'):
    return dict(frame_stamp_ns=10,observation_id='fixture',entity_id=entity,category='chair',confidence=.1)


def test_empty_semantic_stream_is_infrastructure_not_nondetection():
    r=classify([])
    assert r['status']=='infrastructure_failure' and r['human_verdict'] is None


def test_other_entity_in_processed_frame_is_target_nondetection():
    r=classify([emission('other')])
    assert r['status']=='nondetection' and not r['calibration_row_available']


@pytest.mark.parametrize('gap',[
    {'armed':False},{'frame_present':False},{'synchronization_valid':False},
    {'transform_valid':False},{'observation_window_complete':False},
    {'interrupted':True},{'overflow_count':1},{'conflict_count':1}])
def test_stream_failure_cannot_be_correct_label(gap):
    r=classify([emission()],**gap)
    assert r['status']=='infrastructure_failure'
    assert not r['calibration_row_available'] and r['human_verdict'] is None


def test_valid_low_confidence_emission_retained():
    assert classify([emission()])['selected_observation']['confidence']==.1
