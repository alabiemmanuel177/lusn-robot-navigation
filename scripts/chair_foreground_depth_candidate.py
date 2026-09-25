"""Catalogue-blind near-surface hypothesis within a predicted chair box.

Depth discontinuities separate object support from background. This does not
verify object identity: an occluding foreground object can still be mistaken.
All cluster sizes/ranges are retained; the nearest supported cluster is explicit.
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
    order=np.argsort(zz,kind='stable');splits=np.flatnonzero(np.diff(zz[order])>.08)+1
    groups=np.split(order,splits);minimum=max(16,int(np.ceil(.10*len(zz))))
    descriptors=[dict(pixels=len(g),minimum_depth_m=float(zz[g].min()),maximum_depth_m=float(zz[g].max()),
                      eligible=len(g)>=minimum) for g in groups]
    supported=[g for g in groups if len(g)>=minimum]
    if not supported:return dict(status='no_supported_foreground_cluster',map_pose=None,clusters=descriptors,calibration_eligible=False)
    chosen=supported[0];selected=zz[chosen];q25,q75=np.quantile(selected,[.25,.75]);median=float(np.median(selected))
    iqr=float(q75-q25)
    if iqr>.1*median:
        return dict(status='foreground_cluster_still_mixed',map_pose=None,clusters=descriptors,
                    depth_iqr_m=iqr,median_depth_m=median,calibration_eligible=False)
    points=np.stack(((u[chosen]-k[0,2])*selected/k[0,0],(v[chosen]-k[1,2])*selected/k[1,1],selected),axis=1)
    mapped=points@t[:3,:3].T+t[:3,3];point=np.median(mapped,axis=0)
    return dict(status='chair_foreground_surface_candidate',map_pose=point[:2].tolist(),point_xyz=point.tolist(),
        depth_iqr_m=iqr,median_depth_m=median,valid_fraction=float(valid.mean()),
        selected_support_fraction=len(chosen)/len(zz),selected_pixels=len(chosen),clusters=descriptors,
        depth_gap_m=.08,minimum_cluster_pixels=minimum,multiple_surfaces_possible=False,
        other_depth_surfaces_present=len(supported)>1,foreground_selection_verified=False,
        point_semantics='nearest_supported_central_box_depth_cluster_not_verified_identity',
        covariance_calibrated=False,calibration_eligible=False)
