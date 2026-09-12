import pytest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from expansion_sampling import first_synchronized_pair, select_target


def test_earliest_synchronized_not_latest_or_detection_triggered():
    assert first_synchronized_pair([30,10,20],[31,21,11],1)==(10,11)
    assert first_synchronized_pair([10,20],[21],1)==(20,21)
    assert first_synchronized_pair([10],[],1) is None


def test_tie_is_deterministic():
    assert first_synchronized_pair([10],[11,9],1)==(10,9)


def test_no_emission_not_negative_label():
    result=select_target([],frame_stamp_ns=10,entity_id='fixture',category='chair',
                         frame_observation_window_complete=True)
    assert result['status']=='nondetection'
    assert result['human_verdict'] is None
    assert result['calibration_row_available'] is False


def test_wait_for_evidenced_closed_window():
    with pytest.raises(ValueError,match='window'):
        select_target([],frame_stamp_ns=10,entity_id='fixture',category='chair',
                      frame_observation_window_complete=False)


def test_prespecified_target_not_highest_score():
    rows=[dict(frame_stamp_ns=10,entity_id='fixture',category='chair',observation_id='a',confidence=.1),
          dict(frame_stamp_ns=10,entity_id='other',category='chair',observation_id='b',confidence=.99)]
    r=select_target(rows,frame_stamp_ns=10,entity_id='fixture',category='chair',frame_observation_window_complete=True)
    assert r['selected_observation']==rows[0] and len(r['retained_observations'])==2


def test_duplicate_matches_are_not_cherry_picked():
    rows=[dict(frame_stamp_ns=10,entity_id='fixture',category='chair',observation_id=k,confidence=p)
          for k,p in [('a',.1),('b',.9)]]
    r=select_target(rows,frame_stamp_ns=10,entity_id='fixture',category='chair',frame_observation_window_complete=True)
    assert r['status']=='ambiguous_emissions' and r['selected_observation'] is None
