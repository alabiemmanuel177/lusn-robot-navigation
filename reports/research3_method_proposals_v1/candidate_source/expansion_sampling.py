"""ROS-independent prospective sampling candidate outside the frozen core tree.

Never wait for a target detection to choose an image. Missing detections are
explicit observations of absence of emission, not incorrect probability labels.
"""
import math


def first_synchronized_pair(rgb_stamps, depth_stamps, tolerance_ns):
    if type(tolerance_ns) is not int or tolerance_ns < 0:
        raise ValueError('nonnegative integer synchronization tolerance required')
    rgb, depth = sorted(set(rgb_stamps)), sorted(set(depth_stamps))
    if any(type(s) is not int or s < 0 for s in rgb+depth):
        raise ValueError('nonnegative integer timestamps required')
    if not depth:return None
    for stamp in rgb:
        closest=min(depth,key=lambda candidate:(abs(candidate-stamp),candidate))
        if abs(closest-stamp)<=tolerance_ns:return stamp,closest
    return None


def select_target(observations, *, frame_stamp_ns, entity_id, category,
                  frame_observation_window_complete):
    """Keep all same-frame emissions; select only the preassigned exact entity.

    A closed, evidenced collection window is required before calling no emission
    a nondetection. This boolean is a caller obligation, not proof by itself.
    """
    if type(frame_stamp_ns) is not int or frame_stamp_ns<0 or not entity_id:
        raise ValueError('explicit frame and target identity required')
    if not frame_observation_window_complete:
        raise ValueError('cannot declare nondetection before observation window closes')
    rows=list(observations)
    identifiers=[]
    for row in rows:
        if row.get('frame_stamp_ns')!=frame_stamp_ns:
            raise ValueError('other-frame emission must not enter retained frame')
        identifier=row.get('observation_id')
        if not isinstance(identifier,str) or not identifier:raise ValueError('stable observation ID required')
        identifiers.append(identifier)
        probability=row.get('confidence')
        if type(probability) not in (int,float) or not math.isfinite(probability) or not 0<=probability<=1:
            raise ValueError('finite probability required; do not repair scores')
    if len(set(identifiers))!=len(identifiers):raise ValueError('duplicate/conflicting observation identities')
    matching=[r for r in rows if r.get('entity_id')==entity_id and r.get('category')==category]
    return {
        'status':'emitted' if len(matching)==1 else 'nondetection' if not matching else 'ambiguous_emissions',
        'retained_observations':rows,
        'selected_observation':matching[0] if len(matching)==1 else None,
        'human_verdict':None,
        'calibration_row_available':len(matching)==1,
        'confidence_used_for_selection':False,
    }
