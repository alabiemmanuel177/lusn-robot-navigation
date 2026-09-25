import numpy as np
from four_class_perception_candidate import localize,associate_observations,frame_gate,CLASSES


def test_no_target_input_and_no_forced_output():
    result=localize(np.ones((30,30)),np.eye(3),np.eye(4),[],[],camera_xy=[0,0],template='research3-readable-corridor-sign-v1')
    assert result==[]
    assert frame_gate([])==dict.fromkeys(CLASSES,False)


def test_repeated_candidates_remain_ambiguous_and_not_gate_pass():
    obs=dict(visual_category='chair',map_pose=[0,0],status='candidate',entity_id=None)
    refs=[dict(entity_id='one',category='chair',x=.1,y=0),dict(entity_id='two',category='chair',x=.2,y=0)]
    rows=associate_observations([obs],refs)
    assert rows[0]['status']=='ambiguous'
    assert rows[0]['association']['entity_id'] is None
    assert not frame_gate(rows)['chair']


def test_catalogue_never_repairs_visual_class():
    rows=associate_observations([dict(visual_category='chair',map_pose=[0,0],status='candidate')],
        [dict(entity_id='door',category='doorway',x=0,y=0)])
    assert rows[0]['status']=='unassociated'


def test_duplicate_geometry_counts_only_once_and_no_claim():
    row=dict(visual_category='chair',association=dict(status='unique_geometric_candidate',candidates=[dict(reference_distance_m=.35)]))
    assert frame_gate([row,row])['chair'] is True


def test_text_and_detector_scores_never_joint_probabilities():
    k=np.array([[100,0,15],[0,100,15],[0,0,1.]])
    boxes=[dict(visual_category='chair',xyxy=[0,0,30,30],raw_score=.8),
           dict(visual_category='office_entrance',xyxy=[0,0,30,30],raw_score=.9)]
    rows=localize(np.ones((30,30)),k,np.eye(4),boxes,[],camera_xy=[0,0],template='research3-readable-corridor-sign-v1')
    assert len(rows)==1 and rows[0]['visual_category']=='chair'
    assert rows[0]['joint_probability'] is None and not rows[0]['runtime_admitted']
