#!/usr/bin/env python3
"""Rebuild the 80 diagnostic candidates with the verified rendering camera model.

Revision reason: the v1 occluders were placed with the localization transform of
`camera_depth_frame`, which sits about 0.06 m behind, 0.05 m left of and 0.11 m
below the Gazebo sensor that renders pixels; rendered v1 screens therefore miss
the projected marker-box strip. The v1 spheres could also intrude into the
target silhouette from the bound viewpoint. This builder keeps every v1 rule
(marker box, 20% of the projected convex silhouette, neutral visual-only screen,
same-colour visual-only sphere, unchanged source subtree and non-world assets)
and changes only the camera model and the sphere placement search. Rendered
verification and human acceptance remain required; no label is produced.
"""
from __future__ import annotations

import argparse
import copy
import itertools
import json
import math
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_readable_physical_worlds import FILES, canonical, digest  # noqa: E402
from prepare_expansion_occluders import hull, area, clip_left, area_cut  # noqa: E402
from expansion_camera_model import rendering_camera, sdf_rpy, MODEL_ID  # noqa: E402
from expansion_rendered_checks import polygon_mask  # noqa: E402

WIDTH, HEIGHT, HFOV = 640, 480, 2.0
SCHEMA = 'research3-expansion-diagnostic-candidate/v2'
SPHERE_RADIUS = .20
IMAGE_MARGIN_PX = 6
SILHOUETTE_MARGIN_PX = 4
V1 = {'occluder': ROOT / 'reports/calibration_expansion_occluder_assets_20260912_v1',
      'sphere': ROOT / 'reports/calibration_expansion_distractor_assets_20260912_v1'}


def intrinsics():
    fx = (WIDTH / 2) / math.tan(HFOV / 2)
    return dict(k=[fx, 0., WIDTH / 2, 0., fx, HEIGHT / 2, 0., 0., 1.], width=WIDTH, height=HEIGHT)


def pose_matrix(text):
    values = [float(v) for v in (text or '0 0 0 0 0 0').split()]
    if len(values) != 6:
        raise ValueError('six-value pose required')
    from expansion_camera_model import rotation_from_rpy
    matrix = np.eye(4)
    matrix[:3, :3] = rotation_from_rpy(*values[3:])
    matrix[:3, 3] = values[:3]
    return matrix


def box_visuals(model):
    """Absolute corners of every box visual in a model (model ∘ link ∘ visual poses)."""
    boxes = []
    model_pose = pose_matrix(model.findtext('pose'))
    for link in model.findall('link'):
        link_pose = model_pose @ pose_matrix(link.findtext('pose'))
        for visual in link.findall('visual'):
            size_text = visual.findtext('geometry/box/size')
            if size_text is None:
                continue
            visual_pose = link_pose @ pose_matrix(visual.findtext('pose'))
            size = np.array([float(v) for v in size_text.split()])
            corners = [visual_pose @ np.array([*(np.array(signs) * size / 2), 1.]) for signs in itertools.product((-1, 1), repeat=3)]
            boxes.append(np.array(corners)[:, :3])
    return boxes


def marker_name(row):
    return ('chair_seat' if row['category'] == 'chair' else
            row['entity_id'].removesuffix('_doorway') + '_lintel' if row['category'] == 'doorway'
            else row['entity_id'] + '_sign')


def entity_models(world, row):
    if row['category'] == 'chair':
        prefix = 'chair_'
        return [m for m in world.findall('model') if m.get('name', '').startswith(prefix)]
    key = re.sub(r'_(doorway|entrance)$', '', row['entity_id'])
    return [m for m in world.findall('model') if key in m.get('name', '')]


def project(points, centre, rotation, camera):
    optical = (np.asarray(points) - centre) @ rotation
    if np.min(optical[:, 2]) <= .10:
        return None
    normalized = optical[:, :2] / optical[:, 2, None]
    k = camera['k']
    return [(k[0] * x + k[2], k[4] * y + k[5]) for x, y in normalized], normalized, optical


def silhouette_mask(models, centre, rotation, camera):
    mask = np.zeros((HEIGHT, WIDTH), bool)
    for model in models:
        for corners in box_visuals(model):
            projected = project(corners, centre, rotation, camera)
            if projected is None:
                continue
            mask |= polygon_mask(hull(projected[0]), (HEIGHT, WIDTH))
    return mask


def wall_clearance(x, y, walls):
    return min(math.hypot(max(abs(x - w['x']) - w['sx'] / 2, 0), max(abs(y - w['y']) - w['sy'] / 2, 0)) for w in walls)


def segment_hits_wall(a, b, walls, margin=0.):
    """2D segment against axis-aligned wall boxes, sampled finely; walls are full height."""
    a, b = np.asarray(a[:2]), np.asarray(b[:2])
    for t in np.linspace(0., 1., 400):
        p = a + t * (b - a)
        for w in walls:
            if abs(p[0] - w['x']) <= w['sx'] / 2 + margin and abs(p[1] - w['y']) <= w['sy'] / 2 + margin:
                return True
    return False


def sphere_candidates(target, capture_pose):
    dx, dy = capture_pose['x'] - target['x'], capture_pose['y'] - target['y']
    norm = math.hypot(dx, dy)
    if norm < 1e-6:
        raise ValueError('target and camera coincide')
    along = (dx / norm, dy / norm)
    across = (-along[1], along[0])
    ordered = []
    for distance in (.45, .55, .65, .75):
        ordered.append(dict(along=distance, across=0.))
    for across_m in (.6, -.6, .8, -.8, 1.0, -1.0):
        for distance in (.45, .55, .65, .75, .2, 0.):
            ordered.append(dict(along=distance, across=across_m))
    for candidate in ordered:
        candidate['x'] = target['x'] + candidate['along'] * along[0] + candidate['across'] * across[0]
        candidate['y'] = target['y'] + candidate['along'] * along[1] + candidate['across'] * across[1]
    return ordered


def load_source(row):
    match = re.fullmatch(r'r3geo_base_r(00[1-9]|010)', row['map_id'])
    if not match or row['partition'] != 'development' or row['seed'] != 1 or not row['candidate_id'].endswith('-s1-view0'):
        raise PermissionError('development maps 1-10, seed 1, view 0 only')
    source = ROOT / 'data/physical_worlds_readable_v1' / ('base-r' + match[1])
    raw = {name: (source / name).read_bytes() for name in FILES}
    for name, expected in row['world_sha256'].items():
        if digest(raw[name]) != expected:
            raise ValueError('approved source changed: ' + name)
    manifest = json.loads(raw['manifest.json'])
    scene = yaml.safe_load(raw['landmark_scene.yaml'])
    if any(v.get('map_id') != row['map_id'] or v.get('partition') != 'development'
           for v in (manifest, scene, json.loads(raw['execution_catalog.json']))):
        raise ValueError('asset identity mismatch')
    targets = [v for v in scene['entities'] if v['entity_id'] == row['entity_id'] and v['category'] == row['category']]
    if len(targets) != 1:
        raise ValueError('exact approved entity required')
    return source, raw, manifest, targets[0]


def build(row, treatment, destination):
    source, raw, manifest, target = load_source(row)
    tree = ET.fromstring(raw['world.sdf'])
    world = tree.find('world')
    before = canonical(tree)
    marker = world.find(f"model[@name='{marker_name(row)}']")
    if marker is None or marker.find('.//visual/material') is None:
        raise ValueError('source marker missing')
    centre, rotation = rendering_camera(row['capture_pose'])
    camera = intrinsics()
    walls = manifest['layout']['walls']
    previous = V1[treatment] / row['candidate_id'] / ('occluder_candidate_audit.json' if treatment == 'occluder' else 'diagnostic_asset_audit.json')
    audit = dict(schema_version=SCHEMA, treatment=treatment, revision='v2', map_id=row['map_id'], entity_id=row['entity_id'],
                 category=row['category'], capture_pose=row['capture_pose'], marker_model=marker.get('name'),
                 camera_model=dict(model_id=MODEL_ID, centre=centre.tolist(), rpy=list(sdf_rpy(rotation)),
                                   intrinsics=camera, horizontal_fov=HFOV),
                 previous_candidate_audit_sha256=digest(previous.read_bytes()) if previous.exists() else None,
                 revision_reason='v1 used the localization camera_depth_frame transform instead of the rendering sensor pose',
                 panel='diagnostic_only', included_in_primary_calibration=False, human_labels_generated=False,
                 execution_authorized=False, rendered_fraction_verified=False, full_object_occlusion_claimed=False)
    if treatment == 'occluder':
        corners = box_visuals(marker)
        if len(corners) != 1:
            raise ValueError('single-box marker required')
        projected = project(corners[0], centre, rotation, camera)
        if projected is None:
            raise ValueError('marker behind or too close to camera')
        pixels, normalized, optical = projected
        poly = hull(normalized)
        boundary = area_cut(poly)
        x0 = min(p[0] for p in poly)
        y0, y1 = min(p[1] for p in poly), max(p[1] for p in poly)
        depth = float(np.min(optical[:, 2]) * .7)
        thickness = .002
        screen_centre = centre + rotation @ np.array([(x0 + boundary) * depth / 2, (y0 + y1) * depth / 2, depth]) + rotation[:, 2] * thickness / 2
        roll, pitch, yaw = sdf_rpy(rotation)
        dimensions = [(boundary - x0) * depth, (y1 - y0) * depth, thickness]
        model = ET.SubElement(world, 'model', name='expansion_occluder_' + row['entity_id'])
        ET.SubElement(model, 'static').text = 'true'
        ET.SubElement(model, 'pose').text = ' '.join(str(float(v)) for v in (*screen_centre, roll, pitch, yaw))
        link = ET.SubElement(model, 'link', name='visual_only')
        visual = ET.SubElement(link, 'visual', name='neutral_occluder')
        ET.SubElement(ET.SubElement(ET.SubElement(visual, 'geometry'), 'box'), 'size').text = ' '.join(map(str, dimensions))
        material = ET.SubElement(visual, 'material')
        for key in ('ambient', 'diffuse'):
            ET.SubElement(material, key).text = '.45 .45 .45 1'
        ET.SubElement(visual, 'cast_shadows').text = 'false'
        screen_corners = np.array([screen_centre + rotation @ (np.array(s) * np.array(dimensions) / 2)
                                   for s in itertools.product((-1, 1), repeat=3)])
        lo, hi = screen_corners.min(0), screen_corners.max(0)
        issues = ['below_ground'] if lo[2] < 0 else []
        issues += [f'conservative_wall_aabb_overlap_{i}' for i, w in enumerate(walls)
                   if all(lo[j] < w[k] + w[sz] / 2 and hi[j] > w[k] - w[sz] / 2 for j, k, sz in [(0, 'x', 'sx'), (1, 'y', 'sy')])]
        if issues:
            raise ValueError('occluder placement issues: ' + ','.join(issues))
        audit.update(area_reference='projected_convex_silhouette_of_provider_marker_box_not_full_semantic_object',
                     analytic_occluded_fraction=area(clip_left(poly, boundary)) / area(poly), requested_fraction=.2,
                     polygon_normalized_camera=poly, polygon_pixels=[list(p) for p in hull(pixels)], cut_x=boundary,
                     screen_center=screen_centre.tolist(), screen_size=dimensions, camera_plane_depth=depth,
                     screen_rpy=[roll, pitch, yaw], screen_wall_intersection_checked=True)
    else:
        models = entity_models(world, row)
        silhouette = silhouette_mask(models, centre, rotation, camera)
        from scipy import ndimage
        guarded = ndimage.binary_dilation(silhouette, iterations=SILHOUETTE_MARGIN_PX)
        target_boxes = [c for m in models for c in box_visuals(m)]
        chosen, tried = None, []
        for candidate in sphere_candidates(target['pose'], row['capture_pose']):
            x, y = candidate['x'], candidate['y']
            position = np.array([x, y, SPHERE_RADIUS])
            reasons = []
            clearance = wall_clearance(x, y, walls)
            if clearance < SPHERE_RADIUS + .02:
                reasons.append('wall_clearance')
            distance = float(np.linalg.norm(position - centre))
            if math.hypot(x - centre[0], y - centre[1]) < SPHERE_RADIUS + .30:
                reasons.append('camera_clearance')
            for corners in target_boxes:
                lo, hi = corners.min(0), corners.max(0)
                nearest = np.clip(position, lo, hi)
                if np.linalg.norm(nearest - position) < SPHERE_RADIUS + .02:
                    reasons.append('target_geometry_clearance')
                    break
            optical = (position - centre) @ rotation
            if optical[2] <= SPHERE_RADIUS + .10:
                reasons.append('behind_camera')
            else:
                u = camera['k'][0] * optical[0] / optical[2] + camera['k'][2]
                v = camera['k'][4] * optical[1] / optical[2] + camera['k'][5]
                radius_px = camera['k'][0] * math.tan(math.asin(min(1., SPHERE_RADIUS / distance)))
                if not (IMAGE_MARGIN_PX + radius_px <= u <= WIDTH - IMAGE_MARGIN_PX - radius_px
                        and IMAGE_MARGIN_PX + radius_px <= v <= HEIGHT - IMAGE_MARGIN_PX - radius_px):
                    reasons.append('outside_image')
                else:
                    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH]
                    disc = (xx - u) ** 2 + (yy - v) ** 2 <= (radius_px + SILHOUETTE_MARGIN_PX) ** 2
                    if (disc & guarded).any():
                        reasons.append('silhouette_overlap')
                    if segment_hits_wall(centre, position, walls):
                        reasons.append('line_of_sight_blocked')
                    candidate.update(pixel_centre=[u, v], pixel_radius=radius_px)
            candidate.update(clearance=clearance, reasons=reasons)
            tried.append(candidate)
            if not reasons:
                chosen = candidate
                break
        if chosen is None:
            raise ValueError('no prespecified sphere position satisfies visibility and separation')
        pose = [chosen['x'], chosen['y'], SPHERE_RADIUS]
        model = ET.SubElement(world, 'model', name='expansion_diagnostic_sphere_' + row['entity_id'])
        ET.SubElement(model, 'static').text = 'true'
        ET.SubElement(model, 'pose').text = ' '.join(map(str, (*pose, 0, 0, 0)))
        link = ET.SubElement(model, 'link', name='visual_only')
        visual = ET.SubElement(link, 'visual', name='nonlandmark_sphere')
        ET.SubElement(ET.SubElement(ET.SubElement(visual, 'geometry'), 'sphere'), 'radius').text = '.20'
        visual.append(copy.deepcopy(marker.find('.//visual/material')))
        ET.SubElement(visual, 'cast_shadows').text = 'false'
        audit.update(sphere_radius_m=SPHERE_RADIUS, sphere_pose=pose, wall_clearance_m=chosen['clearance'],
                     target_along_offset_m=chosen['along'], target_across_offset_m=chosen['across'],
                     sphere_pixel_centre=chosen['pixel_centre'], sphere_pixel_radius=chosen['pixel_radius'],
                     silhouette_models=[m.get('name') for m in models], silhouette_pixels=int(silhouette.sum()),
                     placement_candidates_tried=tried, material='exact_source_marker_copy',
                     placement_basis='fixed ordered map-only offsets; first position clear of walls, camera, target geometry and the projected target silhouette',
                     treatment_name='same_colour_nonlandmark_distractor')
    if model.findall('.//collision') or model.findall('.//plugin'):
        raise AssertionError('visual-only required')
    world.remove(model)
    if canonical(tree) != before:
        raise AssertionError('original geometry changed')
    world.append(model)
    output_raw = dict(raw)
    output_raw['world.sdf'] = ET.tostring(tree, encoding='utf-8', xml_declaration=True)
    manifest['world_sha256'] = digest(output_raw['world.sdf'])
    output_raw['manifest.json'] = (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode()
    audit.update(original_sdf_subtree_unchanged=True, collision_geometry_unchanged=True,
                 source_sha256={k: digest(v) for k, v in raw.items()},
                 derivative_sha256={k: digest(v) for k, v in output_raw.items()},
                 status='built_static_checked_rendered_preflight_and_human_approval_pending')
    if any((source / name).read_bytes() != value for name, value in raw.items()):
        raise ValueError('source changed during build')
    destination.mkdir(parents=True, exist_ok=False)
    for name, value in output_raw.items():
        with (destination / name).open('xb') as stream:
            stream.write(value)
    with (destination / 'diagnostic_candidate_audit_v2.json').open('x') as stream:
        json.dump(audit, stream, indent=2, sort_keys=True)
        stream.write('\n')
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--occluder-output', type=Path, required=True)
    parser.add_argument('--sphere-output', type=Path, required=True)
    args = parser.parse_args()
    for output in (args.occluder_output, args.sphere_output):
        if output.exists():
            raise FileExistsError(output)
    plan_raw = (ROOT / 'reports/calibration_expansion_handoff_20260912_v1/plan.json').read_bytes()
    approval = json.loads((ROOT / 'reports/calibration_expansion_handoff_20260912_v1/amendment_review_decision.json').read_bytes())
    if digest(plan_raw) != approval['plan_sha256']:
        raise ValueError('accepted plan hash mismatch')
    rows = [r for r in json.loads(plan_raw)['rows'] if r['partition'] == 'development' and r['seed'] == 1
            and r['candidate_id'].endswith('-view0')]
    if len(rows) != 40 or len({r['candidate_id'] for r in rows}) != 40:
        raise ValueError('40 development targets required')
    for treatment, output in (('occluder', args.occluder_output), ('sphere', args.sphere_output)):
        output.mkdir(parents=True, exist_ok=False)
        results = []
        for row in rows:
            try:
                audit = build(row, treatment, output / row['candidate_id'])
                results.append(dict(candidate_id=row['candidate_id'], status='candidate_built',
                                    audit_sha256=digest((output / row['candidate_id'] / 'diagnostic_candidate_audit_v2.json').read_bytes()),
                                    analytic_fraction=audit.get('analytic_occluded_fraction')))
            except (ValueError, PermissionError) as exc:
                results.append(dict(candidate_id=row['candidate_id'], status='blocked', reason=str(exc)))
        summary = dict(schema_version='research3-expansion-diagnostic-preparation/v2', treatment=treatment,
                       plan_sha256=digest(plan_raw), camera_model=MODEL_ID, results=results,
                       execution_authorized=False, rendered_preflight_completed=False, human_labels_generated=False)
        with (output / 'index.json').open('x') as stream:
            json.dump(summary, stream, indent=2)
        (output / 'README.md').write_text(f'# Diagnostic {treatment} candidates (v2)\n\n{__doc__}\n'
                                          'Not an observation review kit. Rendered preflight and human acceptance pending.\n')
        print(json.dumps(dict(treatment=treatment, built=sum(r['status'] == 'candidate_built' for r in results),
                              blocked=[r for r in results if r['status'] == 'blocked'])))


if __name__ == '__main__':
    main()
