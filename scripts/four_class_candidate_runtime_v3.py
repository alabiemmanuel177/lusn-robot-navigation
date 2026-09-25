"""Fail-closed development adapter; not the calibrated semantic-observation feed."""
import math
import numpy as np
from four_class_perception_candidate_v3 import localize,associate_observations
from candidate_rendering_transform import correction


def process_frame(*,frame_id,rgb_stamp_ns,depth_stamp_ns,depth,k,optical_to_map,
                  detector_boxes,ocr_texts,catalogue,camera_xy,template,partition):
    if partition!='development':raise PermissionError('candidate runtime is development only')
    if not isinstance(frame_id,str) or not frame_id:raise ValueError('frame identity required')
    if type(rgb_stamp_ns) is not int or rgb_stamp_ns<0 or type(depth_stamp_ns) is not int or rgb_stamp_ns!=depth_stamp_ns:
        raise ValueError('exact RGB-D synchronization required')
    d=np.asarray(depth);intrinsics=np.asarray(k,float);t=np.asarray(optical_to_map,float)
    if d.ndim!=2 or min(d.shape)<1 or intrinsics.shape!=(3,3) or not np.isfinite(intrinsics).all():raise ValueError('sensor dimensions')
    if intrinsics[0,0]<=0 or intrinsics[1,1]<=0:raise ValueError('positive focal lengths')
    correction(t,np.eye(4),np.eye(4))  # existing strict proper-rigid checks
    if template!='research3-readable-corridor-sign-v1':raise ValueError('approved authored template required')
    if len(camera_xy)!=2 or not all(math.isfinite(x) for x in camera_xy):raise ValueError('camera position')
    for box in detector_boxes:
        if box.get('entity_id') is not None:raise ValueError('detector cannot carry catalogue identity')
        score=box.get('raw_score');xyxy=np.asarray(box.get('xyxy'),float)
        if type(score) not in (int,float) or not math.isfinite(score) or not 0<=score<=1:raise ValueError('raw detector score')
        if xyxy.shape!=(4,) or not np.isfinite(xyxy).all() or np.any(xyxy[2:]<=xyxy[:2]):raise ValueError('box geometry')
    for text in ocr_texts:
        score=text.get('score');quad=np.asarray(text.get('quad'),float)
        if not isinstance(text.get('text'),str) or type(score) not in (int,float) or not math.isfinite(score) or not 0<=score<=1:
            raise ValueError('OCR fields')
        if quad.shape!=(4,2) or not np.isfinite(quad).all():raise ValueError('OCR geometry')
    hypotheses=associate_observations(localize(d,intrinsics,t,detector_boxes,ocr_texts,
        camera_xy=camera_xy,template=template),catalogue)
    status='nondetection' if not hypotheses else 'hypotheses_available'
    return dict(schema_version='research3-four-class-development-candidate/v1',frame_id=frame_id,
        observed_at_ns=rgb_stamp_ns,status=status,hypotheses=hypotheses,
        human_labels_generated=False,joint_probability_model=None,
        calibration_eligible=False,calibrated_runtime_admitted=False)
