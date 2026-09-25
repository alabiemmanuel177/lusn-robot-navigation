import numpy as np
import pytest
from four_class_candidate_runtime import process_frame


def inputs():
    return dict(frame_id='fixture',rgb_stamp_ns=123,depth_stamp_ns=123,depth=np.ones((20,20)),
        k=np.eye(3),optical_to_map=np.eye(4),detector_boxes=[],ocr_texts=[],catalogue=[],camera_xy=[0,0],
        template='research3-readable-corridor-sign-v1',partition='development')


def test_nondetection_is_not_a_negative_label():
    r=process_frame(**inputs())
    assert r['status']=='nondetection' and r['hypotheses']==[]
    assert not r['human_labels_generated'] and not r['calibrated_runtime_admitted']


@pytest.mark.parametrize('change',[dict(depth_stamp_ns=124),dict(k=np.zeros((3,3))),
    dict(optical_to_map=np.zeros((4,4))),dict(template='unknown'),dict(frame_id='')])
def test_infrastructure_input_failures_not_nondetections(change):
    a=inputs();a.update(change)
    with pytest.raises(ValueError):process_frame(**a)


@pytest.mark.parametrize('partition',['validation','held_out','test'])
def test_unapproved_partitions_rejected(partition):
    a=inputs();a['partition']=partition
    with pytest.raises(PermissionError):process_frame(**a)


def test_oracle_identity_and_nan_score_rejected():
    for extra in [dict(entity_id='expected'),dict(raw_score=float('nan'))]:
        a=inputs();a['detector_boxes']=[dict(visual_category='chair',xyxy=[0,0,10,10],raw_score=.4)|extra]
        with pytest.raises(ValueError):process_frame(**a)
