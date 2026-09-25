"""R3-only static-extrinsic correction of a recorded nominal optical TF.

Candidate contract, not live admission. Mount descriptions must be externally
hash-bound and verified for the actual capture/runtime before use.
"""
import numpy as np
from expansion_camera_model import rotation_from_rpy


def rigid(rotation, translation):
    result=np.eye(4); result[:3,:3]=rotation; result[:3,3]=translation
    return result


def correction(nominal_map_tf, nominal_mount, rendering_mount):
    """T_map_render = T_map_nominal inv(T_base_nominal) T_base_render."""
    matrices=[np.asarray(x,dtype=float) for x in (nominal_map_tf,nominal_mount,rendering_mount)]
    for t in matrices:
        if t.shape!=(4,4) or not np.isfinite(t).all():raise ValueError('finite 4x4 transform')
        if not np.allclose(t[3],[0,0,0,1],atol=1e-10,rtol=0) or not np.allclose(t[:3,:3].T@t[:3,:3],np.eye(3),atol=1e-8,rtol=0) or not np.isclose(np.linalg.det(t[:3,:3]),1.,atol=1e-8,rtol=0):
            raise ValueError('proper rigid transform')
    a,b,c=matrices
    return a@np.linalg.inv(b)@c


def described_mounts():
    """Current inspected mount definitions; not automatic historical provenance."""
    nominal=rigid(rotation_from_rpy(-1.57,0.,-1.57),[.069,-.037,.117])
    rendered=rigid(np.array([[0,0,1],[-1,0,0],[0,-1,0]]),[.133,-.094,.224])
    return nominal,rendered
