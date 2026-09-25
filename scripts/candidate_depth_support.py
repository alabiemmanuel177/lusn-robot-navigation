"""Candidate visible-surface estimate; no catalogue coordinates or correctness labels."""
import numpy as np


def estimate(depth, box, intrinsics, optical_to_map):
    depth=np.asarray(depth,dtype=float);k=np.asarray(intrinsics,dtype=float);transform=np.asarray(optical_to_map,dtype=float)
    if depth.ndim!=2 or k.shape!=(3,3) or transform.shape!=(4,4):raise ValueError('depth/K/transform dimensions')
    if not np.isfinite(k).all() or not np.isfinite(transform).all() or k[0,0]<=0 or k[1,1]<=0:
        raise ValueError('finite camera configuration with positive focal lengths')
    rotation=transform[:3,:3]
    if not np.allclose(rotation.T@rotation,np.eye(3),atol=1e-6) or not np.isclose(np.linalg.det(rotation),1.,atol=1e-6) or not np.allclose(transform[3],[0,0,0,1]):
        raise ValueError('proper rigid optical-to-map transform required')
    box=np.asarray(box,dtype=float)
    if box.shape!=(4,) or not np.isfinite(box).all() or box[2]<=box[0] or box[3]<=box[1]:
        raise ValueError('finite positive-area predicted box required')
    height,width=depth.shape
    centre=(box[:2]+box[2:])/2;half=(box[2:]-box[:2])*.2
    low=np.maximum(np.ceil(centre-half).astype(int),[0,0]);high=np.minimum(np.ceil(centre+half).astype(int),[width,height])
    if np.any(high<=low):return dict(status='no_in_frame_depth_support',map_pose=None,calibration_eligible=False)
    vv,uu=np.mgrid[low[1]:high[1],low[0]:high[0]];z=depth[vv,uu]
    valid=np.isfinite(z)&(z>.05)&(z<12.)
    support=int(valid.sum());fraction=support/valid.size
    if support<16 or fraction<.5:
        return dict(status='insufficient_depth_support',valid_pixels=support,valid_fraction=fraction,map_pose=None,calibration_eligible=False)
    zz=z[valid];u=uu[valid];v=vv[valid]
    optical=np.stack(((u-k[0,2])*zz/k[0,0],(v-k[1,2])*zz/k[1,1],zz),axis=1)
    mapped=optical@rotation.T+transform[:3,3]
    point=np.median(mapped,axis=0);mad=np.median(np.abs(mapped-point),axis=0)
    scatter=(1.4826*mad)**2+.02**2
    q25,q75=np.quantile(zz,[.25,.75]);spread=float(q75-q25)
    return dict(status='visible_surface_estimate',map_pose=point[:2].tolist(),point_xyz=point.tolist(),
        descriptive_scatter_diagonal=scatter.tolist(),valid_pixels=support,valid_fraction=fraction,
        depth_iqr_m=spread,multiple_surfaces_possible=spread>.1*float(np.median(zz)),
        point_semantics='central_predicted_box_visible_depth_support_not_catalogue_reference',
        covariance_calibrated=False,object_identity_verified=False,calibration_eligible=False,
        systematic_reference_offset_estimated=False)
