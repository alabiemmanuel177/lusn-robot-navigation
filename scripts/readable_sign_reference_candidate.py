"""Authored-world reference conversion, NOT general entrance localization.

The readable-world builder puts corridor text at entrance_reference.x - .53,
and at side*(corridor_half_width-.10). The reference is side*(half+.30).
Only corridor-side views of this exact template are supported. These constants
are taken from source geometry, not fitted against detector errors or labels.
"""
import math


def reference_from_text(point_xy, camera_xy, *, template):
    if template!='research3-readable-corridor-sign-v1':raise ValueError('unsupported authored template')
    if len(point_xy)!=2 or len(camera_xy)!=2 or not all(math.isfinite(x) for x in (*point_xy,*camera_xy)):
        raise ValueError('finite planar inputs required')
    x,y=point_xy
    if abs(y)<.5 or abs(camera_xy[1])>=abs(y):raise ValueError('corridor-side geometry not established')
    return dict(map_pose=[x+.53,y+math.copysign(.40,y)],
        reference_semantics='authored offset from readable text centre to original sign reference',
        uses_authored_geometry_prior=True,general_scene_method=False,
        identity_verified=False,calibration_eligible=False)
