#!/usr/bin/env python3
"""Pure image checks for rendered diagnostic candidates; no ROS, no labels.

These compare a same-session control render of the unmodified source world with
a candidate render at the identical camera pose. They quantify what the added
visual actually covers in pixels. They are agent preflight measurements, not a
human acceptance verdict and not detector correctness labels.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

MASK_TOLERANCE = 12       # per-channel absolute tolerance for palette colour masks
CHANGE_TOLERANCE = 8      # per-channel change that counts as a rendered difference
OCCLUDER_BOX_TOLERANCE = .06   # allowed |rendered box coverage - 0.20|
SPHERE_MIN_RETAINED = .97


def decode_frame(frame_json: Path):
    """Decode a retained RGB sample after verifying its checksum."""
    frame_json = Path(frame_json)
    info = json.loads(frame_json.read_bytes())
    rgb = info['rgb']
    raw = (frame_json.parent / rgb['file']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != rgb['sha256']:
        raise ValueError('camera sample checksum mismatch')
    if rgb['encoding'] not in ('rgb8', 'bgr8'):
        raise ValueError('unsupported camera encoding')
    array = np.frombuffer(raw, dtype=np.uint8).reshape(rgb['height'], rgb['step'])[:, :rgb['width'] * 3]
    array = array.reshape(rgb['height'], rgb['width'], 3)
    if rgb['encoding'] == 'bgr8':
        array = array[..., ::-1]
    return np.ascontiguousarray(array), info


def palette_key(category, attributes=None):
    if category == 'chair':
        color = (attributes or {}).get('color')
        if not color:
            raise ValueError('chair palette requires a colour attribute')
        return f'chair:color={color}'
    return category


def colour_mask(image, rgb, tolerance=MASK_TOLERANCE):
    diff = np.abs(image.astype(np.int16) - np.asarray(rgb, dtype=np.int16)[None, None, :])
    return np.all(diff <= tolerance, axis=2)


def changed_mask(control, candidate, tolerance=CHANGE_TOLERANCE):
    if control.shape != candidate.shape:
        raise ValueError('control and candidate renders differ in shape')
    return np.any(np.abs(control.astype(np.int16) - candidate.astype(np.int16)) > tolerance, axis=2)


def project_polygon(polygon_normalized, camera_info):
    k = camera_info['k']
    fx, fy, cx, cy = k[0], k[4], k[2], k[5]
    return [(fx * x + cx, fy * y + cy) for x, y in polygon_normalized]


def polygon_mask(points, shape):
    canvas = Image.new('1', (shape[1], shape[0]), 0)
    ImageDraw.Draw(canvas).polygon([(float(x), float(y)) for x, y in points], fill=1)
    return np.array(canvas, dtype=bool)


def components(mask):
    labels, count = ndimage.label(mask)
    sizes = ndimage.sum(mask, labels, range(1, count + 1)) if count else []
    return labels, [int(s) for s in sizes]


def occluder_checks(control, candidate, *, polygon_normalized, camera_info, target_rgb):
    box = polygon_mask(project_polygon(polygon_normalized, camera_info), control.shape[:2])
    changed = changed_mask(control, candidate)
    target_control = colour_mask(control, target_rgb)
    target_candidate = colour_mask(candidate, target_rgb)
    box_area = int(box.sum())
    box_changed = int((box & changed).sum())
    control_in_box = int((box & target_control).sum())
    covered_in_box = int((box & target_control & changed).sum())
    # Occlusion is measured as rendered change over the control's pixels, not
    # palette re-membership, which flickers at the tolerance boundary on shaded faces.
    result = dict(
        projected_box_pixels=box_area,
        rendered_box_coverage=(box_changed / box_area) if box_area else None,
        changed_pixels=int(changed.sum()),
        changed_pixels_outside_box=int((changed & ~box).sum()),
        control_target_pixels=int(target_control.sum()),
        candidate_target_pixels=int(target_candidate.sum()),
        control_target_pixels_in_box=control_in_box,
        control_target_pixels_in_box_covered=covered_in_box,
        target_pixels_in_box_occluded_fraction=(covered_in_box / control_in_box) if control_in_box else None,
        box_unchanged_fraction=(1 - box_changed / box_area) if box_area else None,
        screen_visible=bool(box_changed >= 50),
        target_identifiable=bool(box_area > 0 and box_changed <= .5 * box_area
                                 and (target_control.sum() - (target_control & changed).sum()) >= 50),
    )
    result['box_coverage_within_tolerance'] = (result['rendered_box_coverage'] is not None
        and abs(result['rendered_box_coverage'] - .2) <= OCCLUDER_BOX_TOLERANCE)
    result['passed'] = bool(result['screen_visible'] and result['box_coverage_within_tolerance']
                            and result['target_identifiable'] and box_area > 0
                            and result['changed_pixels_outside_box'] <= max(1, box_changed))
    # The screen is the bounding rectangle of the left silhouette strip, so its
    # corners legitimately spill outside the convex hull; a misplaced screen has
    # more changed pixels outside the box than inside.
    return result, dict(box=box, changed=changed, target_control=target_control, target_candidate=target_candidate)


def sphere_checks(control, candidate, *, target_rgb):
    changed = changed_mask(control, candidate)
    target_control = colour_mask(control, target_rgb)
    target_candidate = colour_mask(candidate, target_rgb)
    sphere = changed & target_candidate
    covered = int((target_control & changed).sum())
    retained = int(target_control.sum()) - covered
    labels, sizes = components(target_candidate)
    control_labels = set(int(v) for v in np.unique(labels[target_control & (labels > 0)]))
    sphere_labels = set(int(v) for v in np.unique(labels[sphere & (labels > 0)]))
    result = dict(
        changed_pixels=int(changed.sum()),
        sphere_pixels=int(sphere.sum()),
        control_target_pixels=int(target_control.sum()),
        candidate_target_pixels=int(target_candidate.sum()),
        control_target_pixels_retained=retained,
        control_target_pixels_covered=covered,
        target_retained_fraction=(retained / int(target_control.sum())) if target_control.sum() else None,
        candidate_components=len(sizes),
        sphere_visible=bool(sphere.sum() >= 100),
        sphere_and_target_disjoint=bool(sphere_labels and not (sphere_labels & control_labels)),
        target_identifiable=bool(retained >= 100),
    )
    result['passed'] = bool(result['sphere_visible'] and result['sphere_and_target_disjoint']
                            and result['target_identifiable']
                            and (result['target_retained_fraction'] or 0) >= SPHERE_MIN_RETAINED)
    return result, dict(changed=changed, target_control=target_control, target_candidate=target_candidate, sphere=sphere)


def control_drift(control, pilot):
    """Compare a same-session control with the bound pilot frame at the same pose."""
    if control.shape != pilot.shape:
        return dict(comparable=False, reason='shape differs')
    changed = changed_mask(control, pilot)
    return dict(comparable=True, changed_pixels=int(changed.sum()),
                changed_fraction=float(changed.mean()))


def outline(mask):
    eroded = ndimage.binary_erosion(mask)
    return mask & ~eroded


def composite(control, candidate, masks, *, polygon_pixels=None, title=''):
    """Side-by-side PNG: control | candidate with overlays | change map."""
    h, w = control.shape[:2]
    overlay = candidate.copy()
    if 'box' in masks:
        overlay[outline(masks['box'])] = (255, 255, 0)
    overlay[outline(masks['target_candidate'])] = (0, 255, 255)
    if 'sphere' in masks:
        overlay[outline(masks['sphere'])] = (255, 0, 255)
    change = np.zeros_like(control)
    change[masks['changed']] = (255, 255, 255)
    change[outline(masks['target_control'])] = (0, 255, 255)
    sheet = Image.new('RGB', (w * 3 + 8, h + 24), (32, 32, 32))
    for index, array in enumerate((control, overlay, change)):
        sheet.paste(Image.fromarray(array), (index * (w + 4), 24))
    draw = ImageDraw.Draw(sheet)
    draw.text((4, 4), f'{title}   left: control render   middle: candidate + overlays   right: changed pixels', fill=(255, 255, 255))
    if polygon_pixels:
        draw.polygon([(x + w + 4, y + 24) for x, y in polygon_pixels], outline=(255, 255, 0))
    return sheet
