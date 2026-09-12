#!/usr/bin/env python3
"""Build the 40 same-colour diagnostic candidates, without capture or approval.

Preserve every original SDF element and all non-world assets. These assets need
visual preflight; static clearance is not evidence of detector confusion.
"""
import argparse
import copy
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import yaml
from build_readable_physical_worlds import FILES, canonical, digest
from language_nav.capture_view import validate_capture_pose

ROOT = Path(__file__).resolve().parents[1]


def place_sphere(target, camera, walls, radius=.20):
    dx, dy = camera['x']-target['x'], camera['y']-target['y']
    norm = math.hypot(dx, dy)
    if norm < 1e-6:
        raise ValueError('target and camera coincide')
    # Fixed map-only candidate ordering; never consult pixels, confidence or labels.
    for distance in (.45, .55, .65, .75):
        x, y = target['x']+distance*dx/norm, target['y']+distance*dy/norm
        clearance = min(math.hypot(max(abs(x-w['x'])-w['sx']/2, 0),
                                   max(abs(y-w['y'])-w['sy']/2, 0)) for w in walls)
        if clearance >= radius+.02 and math.hypot(x-camera['x'], y-camera['y']) >= radius+.30:
            return [x, y, radius], clearance, distance
    raise ValueError('no prespecified wall/camera-clear sphere position')


def build(root, row, destination):
    match = re.fullmatch(r'r3geo_base_r(00[1-9]|010)', row['map_id'])
    if not match or row['partition'] != 'development' or row['seed'] != 1:
        raise PermissionError('development maps 1–10 and seed 1 only, before asset reads')
    if not row['candidate_id'].endswith('-s1-view0'):
        raise ValueError('prespecified original view only')
    base = 'base-r'+match[1]
    source = root/'data/physical_worlds_readable_v1'/base
    if destination.exists():
        raise FileExistsError(destination)
    raw = {name: (source/name).read_bytes() for name in FILES}
    for name, expected in row['world_sha256'].items():
        if digest(raw[name]) != expected:
            raise ValueError('approved source changed: '+name)
    prior_raw = (source/'visual_derivative_audit.json').read_bytes()
    prior = json.loads(prior_raw)
    if (prior.get('protected_content_used') is not False or
            any(prior['derivative_sha256'].get(k) != digest(v) for k,v in raw.items())):
        raise ValueError('readable source audit mismatch')
    manifest = json.loads(raw['manifest.json'])
    scene = yaml.safe_load(raw['landmark_scene.yaml'])
    if any(v.get('map_id') != row['map_id'] or v.get('partition') != 'development'
           for v in (manifest, scene, json.loads(raw['execution_catalog.json']))):
        raise ValueError('asset identity mismatch')
    targets = [v for v in scene['entities'] if v['entity_id']==row['entity_id']
               and v['category']==row['category']]
    if len(targets) != 1:
        raise ValueError('exact approved entity required')
    target = targets[0]
    marker_name = ('chair_seat' if row['category']=='chair' else
                   row['entity_id'].removesuffix('_doorway')+'_lintel'
                   if row['category']=='doorway' else row['entity_id']+'_sign')
    tree = ET.fromstring(raw['world.sdf']); world = tree.find('world')
    before = canonical(tree)
    marker = world.find(f"model[@name='{marker_name}']")
    if marker is None or marker.find('.//visual/material') is None:
        raise ValueError('source marker material missing')
    pose, clearance, offset = place_sphere(target['pose'], row['capture_pose'], manifest['layout']['walls'])
    validate_capture_pose(source, **row['capture_pose'])
    name = 'expansion_diagnostic_sphere_'+row['entity_id']
    if world.find(f"model[@name='{name}']") is not None:
        raise ValueError('diagnostic already present')
    model = ET.SubElement(world, 'model', name=name)
    ET.SubElement(model, 'static').text = 'true'
    ET.SubElement(model, 'pose').text = ' '.join(map(str, (*pose, 0, 0, 0)))
    link = ET.SubElement(model, 'link', name='visual_only')
    visual = ET.SubElement(link, 'visual', name='nonlandmark_sphere')
    geometry = ET.SubElement(visual, 'geometry')
    ET.SubElement(ET.SubElement(geometry, 'sphere'), 'radius').text = '.20'
    visual.append(copy.deepcopy(marker.find('.//visual/material')))
    ET.SubElement(visual, 'cast_shadows').text = 'false'
    if model.findall('.//collision') or model.findall('.//plugin'):
        raise AssertionError('diagnostic must be visual only')
    world.remove(model)
    if canonical(tree) != before:
        raise AssertionError('original world changed')
    world.append(model)
    new_sdf = ET.tostring(tree, encoding='utf-8', xml_declaration=True)
    output_raw = dict(raw)
    output_raw['world.sdf'] = new_sdf
    manifest['world_sha256'] = digest(new_sdf)
    output_raw['manifest.json'] = (json.dumps(manifest, sort_keys=True, indent=2)+'\n').encode()
    audit = {
        'schema_version': 'research3-expansion-diagnostic-asset/v1',
        'status': 'built_static_checked_visual_preflight_and_approval_pending',
        'panel': 'diagnostic_only', 'included_in_calibration': False,
        'primary_candidate_id': row['candidate_id'], 'map_id': row['map_id'],
        'category': row['category'], 'entity_id': row['entity_id'],
        'capture_pose': row['capture_pose'], 'source_marker_model': marker_name,
        'treatment': 'same_colour_nonlandmark_distractor',
        'sphere_radius_m': .20, 'sphere_pose': pose, 'wall_clearance_m': clearance,
        'target_xy_offset_m': offset, 'material': 'exact_source_marker_copy',
        'placement_basis': 'fixed_camera_ray_distances_using_only_geometry',
        'original_sdf_elements_unchanged': True, 'collision_geometry_unchanged': True,
        'stable_ids_unchanged': True, 'protected_content_used': False,
        'human_labels_generated': False, 'false_detection_observed': False,
        'execution_authorized': False,
        'source_sha256': {k:digest(v) for k,v in raw.items()},
        'derivative_sha256': {k:digest(v) for k,v in output_raw.items()},
    }
    if any((source/name).read_bytes() != value for name,value in raw.items()):
        raise ValueError('source changed during build')
    destination.mkdir(parents=True, exist_ok=False)
    for name,value in output_raw.items():
        with (destination/name).open('xb') as stream: stream.write(value)
    for name,value in [('source_readable_audit.json',prior_raw),
                       ('diagnostic_asset_audit.json',(json.dumps(audit,indent=2,sort_keys=True)+'\n').encode())]:
        with (destination/name).open('xb') as stream: stream.write(value)
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists(): raise FileExistsError(args.output)
    proposal = ROOT/'reports/calibration_expansion_proposal_20260911_v2'
    raw = (proposal/'plan.json').read_bytes()
    receipt = json.loads((ROOT/'reports/calibration_expansion_handoff_20260912_v1/amendment_review_decision.json').read_bytes())
    if digest(raw) != receipt['plan_sha256']:
        raise ValueError('accepted plan hash mismatch')
    rows = [r for r in json.loads(raw)['rows'] if r['partition']=='development'
            and r['seed']==1 and r['candidate_id'].endswith('-view0')]
    if len(rows)!=40 or len({r['candidate_id'] for r in rows})!=40:
        raise ValueError('exact 40 prespecified development targets required')
    args.output.mkdir(parents=True, exist_ok=False)
    results = []
    for row in rows:
        destination = args.output/row['candidate_id']
        try:
            audit = build(ROOT, row, destination)
            results.append({'candidate_id':row['candidate_id'], 'status':'built',
                            'audit_sha256':digest((destination/'diagnostic_asset_audit.json').read_bytes())})
        except (ValueError, PermissionError) as exc:
            results.append({'candidate_id':row['candidate_id'], 'status':'blocked', 'reason':str(exc)})
    summary = {'schema_version':'research3-expansion-distractor-preparation/v1',
               'plan_sha256':digest(raw), 'results':results, 'execution_authorized':False,
               'visual_preflight_completed':False, 'occluder_assets_included':False}
    with (args.output/'index.json').open('x') as stream: json.dump(summary,stream,indent=2)
    print(json.dumps({'built':sum(r['status']=='built' for r in results),
                      'blocked':[r for r in results if r['status']=='blocked'],
                      'visual_preflight_completed':False,'execution_authorized':False}))


if __name__=='__main__': main()
