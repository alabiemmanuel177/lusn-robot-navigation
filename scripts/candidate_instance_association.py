"""Offline association candidate: expose ambiguity, never infer visual class from IDs."""
import math


def associate(localized, catalogue, radius=.9):
    if localized.get('object_localized') is not True or localized.get('map_pose') is None:
        raise ValueError('independently localized visual evidence required; grid centres are not objects')
    if localized.get('entity_id') is not None:
        raise ValueError('visual input must not carry a preselected catalogue identity')
    if not math.isfinite(radius) or radius <= 0:
        raise ValueError('positive finite association radius required')
    category = localized.get('visual_category')
    if category not in ('chair','doorway','laboratory_entrance','office_entrance'):
        raise ValueError('explicit visual category required')
    x,y = localized['map_pose']
    if not all(math.isfinite(v) for v in (x,y)):
        raise ValueError('finite localization required')
    candidates=[]; seen=set()
    for ref in catalogue:
        identity=ref['entity_id']
        if not isinstance(identity,str) or not identity or identity in seen:
            raise ValueError('unique catalogue IDs required')
        seen.add(identity)
        if not all(math.isfinite(v) for v in (ref['x'],ref['y'])):
            raise ValueError('finite reference coordinates required')
        if ref['category'] != category: continue
        distance=math.hypot(x-ref['x'],y-ref['y'])
        if distance <= radius:
            candidates.append(dict(entity_id=identity,reference_distance_m=distance))
    candidates.sort(key=lambda r:r['entity_id'])
    return dict(schema_version='research3-instance-association-candidate/v1',
        visual_category=category,candidates=candidates,
        status='unassociated' if not candidates else 'ambiguous' if len(candidates)>1 else 'unique_geometric_candidate',
        entity_id=candidates[0]['entity_id'] if len(candidates)==1 else None,
        joint_correctness_probability=None,identity_verified=False,calibration_eligible=False,
        runtime_admitted=False,rule='retain_all_same_visual_class_references_within_fixed_radius')
