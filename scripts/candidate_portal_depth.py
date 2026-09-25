"""Engineering hypothesis: estimate an opening from two side strips, not its hole."""
import numpy as np
from candidate_depth_support import estimate


def portal_estimate(depth, box, intrinsics, optical_to_map):
    # Reuse checked dimensions/calibration/rigid-transform contract.
    base=estimate(depth,box,intrinsics,optical_to_map)
    depth=np.asarray(depth,float);k=np.asarray(intrinsics,float);t=np.asarray(optical_to_map,float)
    x0,y0,x1,y1=map(float,box);w=x1-x0;h=y1-y0
    strips=[[x0,y0+.15*h,x0+.15*w,y1-.15*h],
            [x1-.15*w,y0+.15*h,x1,y1-.15*h]]
    medians=[];supports=[]
    for strip in strips:
        low=np.maximum(np.ceil(strip[:2]).astype(int),[0,0]);high=np.minimum(np.ceil(strip[2:]).astype(int),[depth.shape[1],depth.shape[0]])
        if np.any(high<=low):return dict(status='portal_side_out_of_frame',map_pose=None,calibration_eligible=False)
        z=depth[low[1]:high[1],low[0]:high[0]]
        valid=np.isfinite(z)&(z>.05)&(z<12.)
        if valid.sum()<16 or valid.mean()<.5:return dict(status='insufficient_portal_side_depth',map_pose=None,calibration_eligible=False)
        medians.append(float(np.median(z[valid])));supports.append(int(valid.sum()))
    disagreement=abs(medians[0]-medians[1])/np.median(medians)
    if disagreement>.15:return dict(status='portal_sides_disagree',map_pose=None,side_depths_m=medians,calibration_eligible=False)
    z=float(np.mean(medians));u=(x0+x1)/2;v=(y0+y1)/2
    optical=np.array([(u-k[0,2])*z/k[0,0],(v-k[1,2])*z/k[1,1],z])
    point=t[:3,:3]@optical+t[:3,3]
    return dict(status='portal_side_surface_candidate',map_pose=point[:2].tolist(),point_xyz=point.tolist(),
        side_depths_m=medians,side_support_pixels=supports,relative_side_disagreement=float(disagreement),
        central_depth_status=base['status'],point_semantics='box_center_ray_at_mean_side_strip_depth_not_verified_reference',
        covariance_calibrated=False,object_identity_verified=False,calibration_eligible=False,runtime_admitted=False)
