"""Evaluation-only pose checks; neither a pose estimator nor a human labeler."""
import math
import numpy as np


def compare_transforms(estimated, independent_truth, *, estimate_stamp_ns,
                       truth_stamp_ns, truth_source, descriptions_bound):
    if truth_source != 'simulator_world_pose':
        raise ValueError('commanded pose and localization TF are not independent simulator truth')
    if not descriptions_bound:raise ValueError('capture-time robot/sensor description hashes required')
    if type(estimate_stamp_ns) is not int or type(truth_stamp_ns) is not int or estimate_stamp_ns<0 or estimate_stamp_ns!=truth_stamp_ns:
        raise ValueError('exact synchronized simulation timestamps required; no nearest-pose substitution')
    transforms=[np.asarray(t,dtype=float) for t in (estimated,independent_truth)]
    for t in transforms:
        if t.shape!=(4,4) or not np.isfinite(t).all() or not np.allclose(t[3],[0,0,0,1],rtol=0,atol=1e-9):raise ValueError('homogeneous transform')
        r=t[:3,:3]
        if not np.allclose(r.T@r,np.eye(3),rtol=0,atol=1e-8) or not np.isclose(np.linalg.det(r),1.,rtol=0,atol=1e-8):raise ValueError('proper rotation')
    estimate,truth=transforms
    translation=float(np.linalg.norm(estimate[:3,3]-truth[:3,3]))
    angle=math.acos(float(np.clip((np.trace(estimate[:3,:3].T@truth[:3,:3])-1)/2,-1,1)))
    return dict(translation_error_m=translation,rotation_error_rad=angle,
        engineering_screen_pass=translation<=.03 and angle<=math.pi/180,
        ground_truth_evaluation_only=True,human_verdict=None,calibration_eligible=False,
        engineering_thresholds=dict(translation_m=.03,rotation_rad=math.pi/180))


def reference_consistency(point_xy,reference_xy):
    a=np.asarray(point_xy,dtype=float);b=np.asarray(reference_xy,dtype=float)
    if a.shape!=(2,) or b.shape!=(2,) or not np.isfinite(a).all() or not np.isfinite(b).all():raise ValueError('finite planar coordinates')
    distance=float(np.linalg.norm(a-b))
    return dict(reference_point_distance_m=distance,within_existing_radius=distance<=.35,
                category_verified=False,instance_verified=False,human_verdict=None)
