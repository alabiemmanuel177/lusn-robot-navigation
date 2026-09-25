"""Development-only four-class visual/depth integration, without target inputs."""
import numpy as np
from candidate_depth_support import estimate
from candidate_portal_depth import portal_estimate
from candidate_instance_association import associate
from entrance_context_candidate import text_category
from readable_sign_reference_candidate import reference_from_text

CLASSES=('chair','doorway','laboratory_entrance','office_entrance')


def localize(depth,k,optical_to_map,detector_boxes,ocr_texts,*,camera_xy,template):
    """Inference has no catalogue, acquisition target, entity ID or truth input."""
    observations=[]
    for i,box in enumerate(detector_boxes):
        category=box.get('visual_category')
        if category not in ('chair','doorway'):continue
        surface=(estimate if category=='chair' else portal_estimate)(depth,box['xyxy'],k,optical_to_map)
        status=surface['status'];point=surface['map_pose']
        if surface.get('multiple_surfaces_possible'):status='unresolved_multiple_surfaces';point=None
        observations.append(dict(source='grounding_dino',source_index=i,visual_category=category,
            raw_score=box['raw_score'],raw_score_meaning='text_matching_not_joint_probability',
            box=box['xyxy'],surface=surface,map_pose=point,status=status))
    for i,text in enumerate(ocr_texts):
        category=text_category(text['text'])
        if category is None:continue
        quad=np.asarray(text['quad'],dtype=float)
        if quad.shape!=(4,2) or not np.isfinite(quad).all():raise ValueError('finite OCR quadrilateral')
        box=np.concatenate([quad.min(axis=0),quad.max(axis=0)]).tolist()
        surface=estimate(depth,box,k,optical_to_map);point=None;converted=None;status=surface['status']
        if surface['map_pose'] is not None and not surface['multiple_surfaces_possible']:
            try:
                converted=reference_from_text(surface['map_pose'],camera_xy,template=template)
                point=converted['map_pose'];status='authored_reference_candidate'
            except ValueError:status='unsupported_template_view'
        elif surface.get('multiple_surfaces_possible'):status='unresolved_multiple_surfaces'
        observations.append(dict(source='rapidocr',source_index=i,visual_category=category,raw_score=text['score'],
            raw_score_meaning='text_recognition_not_joint_probability',box=box,text=text['text'],
            surface=surface,converted=converted,map_pose=point,status=status))
    for obs in observations:
        obs.update(entity_id=None,human_verdict=None,joint_probability=None,
            calibration_eligible=False,runtime_admitted=False,identity_verified=False)
    return observations


def associate_observations(observations,catalogue):
    result=[]
    for obs in observations:
        row=dict(obs,association=None)
        if obs['map_pose'] is not None:
            association=associate(dict(object_localized=True,map_pose=obs['map_pose'],
                visual_category=obs['visual_category'],entity_id=None),catalogue)
            row.update(association=association,status=association['status'])
        result.append(row)
    return result


def frame_gate(observations):
    """Necessary geometric gate, not identity accuracy; duplicates count once."""
    result={c:False for c in CLASSES}
    for row in observations:
        association=row.get('association')
        if association and association['status']=='unique_geometric_candidate':
            if association['candidates'][0]['reference_distance_m']<=.35:
                result[row['visual_category']]=True
    return result
