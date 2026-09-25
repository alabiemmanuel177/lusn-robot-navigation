"""Fixed-width chair foreground band; other three class estimators unchanged."""
from four_class_perception_candidate import localize as previous_localize,associate_observations,frame_gate,CLASSES
from chair_foreground_band_candidate import chair_surface_estimate


def localize(depth,k,optical_to_map,detector_boxes,ocr_texts,*,camera_xy,template):
    rows=previous_localize(depth,k,optical_to_map,detector_boxes,ocr_texts,camera_xy=camera_xy,template=template)
    for obs in rows:
        if obs['visual_category']=='chair':
            surface=chair_surface_estimate(depth,obs['box'],k,optical_to_map)
            obs.update(surface=surface,map_pose=surface['map_pose'],status=surface['status'])
    return rows
