"""Fixed-width near-depth support, robust to sparse samples bridging surfaces.

Select the nearest 0.10 m band with >=16 pixels and >=10% of valid central-box
support. No gap/threshold sweep, catalogue input, or inference of correctness.
"""
import numpy as np
from candidate_depth_support import estimate


def chair_surface_estimate(depth,box,intrinsics,optical_to_map):
    checked=estimate(depth,box,intrinsics,optical_to_map)
    if checked['map_pose'] is None:return checked
    depth=np.asarray(depth,float);k=np.asarray(intrinsics,float);t=np.asarray(optical_to_map,float)
    box=np.asarray(box,float);centre=(box[:2]+box[2:])/2;half=(box[2:]-box[:2])*.2
    low=np.maximum(np.ceil(centre-half).astype(int),[0,0]);high=np.minimum(np.ceil(centre+half).astype(int),[depth.shape[1],depth.shape[0]])
    vv,uu=np.mgrid[low[1]:high[1],low[0]:high[0]];z=depth[vv,uu]
    valid=np.isfinite(z)&(z>.05)&(z<12);zz=z[valid];u=uu[valid];v=vv[valid]
    order=np.argsort(zz,kind='stable');ordered=zz[order];minimum=max(16,int(np.ceil(.10*len(zz))))
    ends=np.searchsorted(ordered,ordered+.10,side='right');starts=np.flatnonzero(ends-np.arange(len(ordered))>=minimum)
    if not len(starts):return dict(status='no_supported_foreground_band',map_pose=None,calibration_eligible=False)
    start=int(starts[0]);chosen=order[start:ends[start]];selected=zz[chosen]
    q25,q75=np.quantile(selected,[.25,.75]);median=float(np.median(selected));iqr=float(q75-q25)
    if iqr>.1*median:return dict(status='foreground_band_still_mixed',map_pose=None,calibration_eligible=False)
    points=np.stack(((u[chosen]-k[0,2])*selected/k[0,0],(v[chosen]-k[1,2])*selected/k[1,1],selected),axis=1)
    mapped=points@t[:3,:3].T+t[:3,3];point=np.median(mapped,axis=0)
    return dict(status='chair_foreground_band_candidate',map_pose=point[:2].tolist(),point_xyz=point.tolist(),
        depth_iqr_m=iqr,median_depth_m=median,valid_fraction=float(valid.mean()),
        selected_support_fraction=len(chosen)/len(zz),selected_pixels=len(chosen),
        selected_depth_range_m=[float(selected.min()),float(selected.max())],
        band_width_m=.10,minimum_support_pixels=minimum,multiple_surfaces_possible=False,
        discarded_depth_pixels=len(zz)-len(chosen),foreground_selection_verified=False,
        point_semantics='nearest_supported_fixed_depth_band_inside_predicted_chair_box',
        covariance_calibrated=False,calibration_eligible=False)
