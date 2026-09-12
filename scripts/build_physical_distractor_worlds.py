#!/usr/bin/env python3
"""Append one visual-only shape to a readable non-protected stress world."""
import argparse
import copy
import importlib.util
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import yaml

SPEC = importlib.util.spec_from_file_location('readable_builder',
    Path(__file__).with_name('build_readable_physical_worlds.py'))
READABLE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(READABLE)
ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = ('chair', 'doorway', 'laboratory_entrance', 'office_entrance')
ALLOWED = {'base-r010': 'development', 'base-r011': 'validation'}


def build(source, destination, category, *, controlled_occlusion=False,
          controlled_material_occlusion=False, controlled_chair_material_occlusion=False):
    source, destination = Path(source), Path(destination)
    if source.name not in ALLOWED:
        raise PermissionError('only base-r010 and base-r011 non-protected sources permitted')
    if category not in CATEGORIES:
        raise ValueError('unsupported stress category')
    if controlled_occlusion and (source.name != 'base-r010' or category != 'chair'):
        raise ValueError('controlled occlusion is restricted to the development base-r010 chair')
    if controlled_material_occlusion and (
            source.name != 'base-r010' or category == 'chair' or controlled_occlusion):
        raise ValueError('controlled material occlusion is restricted to dev10 doorway/entrance conditions')
    if controlled_chair_material_occlusion and (
            source.name != 'base-r010' or category != 'chair' or controlled_material_occlusion
            or controlled_occlusion):
        raise ValueError('chair material occlusion is restricted to dev10 chair as a separate condition')
    if destination.exists():
        raise FileExistsError(destination)
    raw = {name: (source / name).read_bytes() for name in READABLE.FILES}
    prior_path = source / 'visual_derivative_audit.json'
    prior_raw = prior_path.read_bytes()
    prior = json.loads(prior_raw)
    if (prior.get('schema_version') != 'research3-readable-visual-derivative/v1'
            or prior.get('protected_content_used') is not False
            or any(prior['derivative_sha256'].get(name) != READABLE.digest(value)
                   for name, value in raw.items())):
        raise ValueError('source is not an intact readable-world derivative')
    manifest = json.loads(raw['manifest.json'])
    catalog = json.loads(raw['execution_catalog.json'])
    scene = yaml.safe_load(raw['landmark_scene.yaml'])
    expected_map = 'r3geo_' + source.name.replace('-', '_')
    if any(item.get('partition') != ALLOWED[source.name] or item.get('map_id') != expected_map
           for item in (manifest, catalog, scene)):
        raise PermissionError('source map/split identity mismatch')
    if manifest.get('base_instruction_id') != source.name:
        raise ValueError('source instruction identity mismatch')
    original_hashes = {name: READABLE.digest(value) for name, value in raw.items()}
    tree = ET.fromstring(raw['world.sdf'])
    world = tree.find('world')
    original_tree = READABLE.canonical(tree)
    targets = sorted((item for item in scene['entities'] if item['category'] == category),
                     key=lambda item: item['entity_id'])
    if not targets:
        raise ValueError('stress category absent from scene')
    target = targets[0]  # Prespecified single target, never selected by detector outcome.
    identifier = target['entity_id']
    marker_name = ('chair_seat' if category == 'chair' else identifier.removesuffix('_doorway')
                   + '_lintel' if category == 'doorway' else identifier + '_sign')
    marker = world.find(f"model[@name='{marker_name}']")
    if marker is None or marker.find('.//visual/material') is None:
        raise ValueError('original target material unavailable')
    material = marker.find('.//visual/material')
    x, y = target['pose']['x'], target['pose']['y']
    side = 1 if y > 0 else -1
    half = manifest['layout']['corridor_half_width']
    if category == 'chair':
        pose, shape, radius = (x-.5, y-side*.4, .25), 'sphere', .25
        if controlled_occlusion or controlled_chair_material_occlusion:
            pose, radius = (2.0, .6, .45), .30
    elif category == 'doorway':
        pose, shape, radius = (x, side*(half-.58), .25), 'sphere', .25
    else:
        pose, shape, radius = (x, side*(half-.45), .25), 'cylinder', .22
        if controlled_material_occlusion:
            pose = (x, side*1.0, .25)
    error = math.hypot(pose[0]-x, pose[1]-y)
    wall_clearance = min(math.hypot(max(abs(pose[0]-wall['x'])-wall['sx']/2, 0),
                                  max(abs(pose[1]-wall['y'])-wall['sy']/2, 0))
                         for wall in manifest['layout']['walls'])
    if error >= .9 or wall_clearance < radius:
        raise ValueError('shape not within association radius or clips corridor wall')
    name = 'stress_shape_' + identifier
    if world.find(f"model[@name='{name}']") is not None:
        raise ValueError('distractor already present')
    model = ET.SubElement(world, 'model', name=name)
    ET.SubElement(model, 'static').text = 'true'
    ET.SubElement(model, 'pose').text = ' '.join(map(str, (*pose, 0, 0, 0)))
    link = ET.SubElement(model, 'link', name='visual_only_shape')
    visual = ET.SubElement(link, 'visual', name='unmistakable_' + shape)
    geometry = ET.SubElement(visual, 'geometry')
    primitive = ET.SubElement(geometry, shape)
    ET.SubElement(primitive, 'radius').text = str(radius)
    if shape == 'cylinder':
        ET.SubElement(primitive, 'length').text = '.5'
    visual.append(copy.deepcopy(material))
    ET.SubElement(visual, 'cast_shadows').text = 'true'
    world.remove(model)
    if READABLE.canonical(tree) != original_tree:
        raise AssertionError('canonical source subtree changed')
    world.append(model)
    if model.findall('.//collision') or model.findall('.//plugin'):
        raise AssertionError('distractor must remain visual-only')
    shell_audit = None
    chair_shell_audits = []
    if controlled_material_occlusion:
        # Append a separate shell, never alter or remove the coloured source
        # marker, its collisions, or any readable lettering model.
        dimensions = [float(value) for value in marker.findtext('.//visual/geometry/box/size').split()]
        shell = ET.SubElement(world, 'model', name='stress_neutral_shell_' + identifier)
        ET.SubElement(shell, 'static').text = 'true'
        shell.append(copy.deepcopy(marker.find('pose')))
        shell_link = ET.SubElement(shell, 'link', name='visual_only_shell')
        shell_visual = ET.SubElement(shell_link, 'visual', name='neutral_material_occlusion')
        geometry = ET.SubElement(shell_visual, 'geometry')
        ET.SubElement(ET.SubElement(geometry, 'box'), 'size').text = ' '.join(
            str(value+.01) for value in dimensions)
        shell_material = ET.SubElement(shell_visual, 'material')
        for field in ('ambient', 'diffuse'):
            ET.SubElement(shell_material, field).text = '.45 .45 .45 1'
        shell_audit = {'model_name': shell.get('name'), 'source_marker_model': marker_name,
                       'pose': [float(value) for value in marker.findtext('pose').split()],
                       'source_box_size': dimensions,
                       'shell_box_size': [value+.01 for value in dimensions],
                       'dimension_expansion_m': .01, 'material_rgba': [.45, .45, .45, 1],
                       'collision_count': 0, 'readable_lettering_models_modified': False}
        world.remove(model)
        world.remove(shell)
        if READABLE.canonical(tree) != original_tree:
            raise AssertionError('original subtree changed by shell intervention')
        world.append(model)
        world.append(shell)
    if controlled_chair_material_occlusion:
        shells = []
        for source_name in ('chair_back', 'chair_seat'):
            original = world.find(f"model[@name='{source_name}']")
            if original is None:
                raise ValueError('missing original coloured chair component')
            dimensions = [float(value) for value in original.findtext('.//visual/geometry/box/size').split()]
            original_material = original.find('.//visual/material')
            shell = ET.SubElement(world, 'model', name='stress_neutral_shell_'+source_name)
            ET.SubElement(shell, 'static').text = 'true'
            shell.append(copy.deepcopy(original.find('pose')))
            shell_link = ET.SubElement(shell, 'link', name='visual_only_shell')
            shell_visual = ET.SubElement(shell_link, 'visual', name='neutral_material_occlusion')
            shell_geometry = ET.SubElement(shell_visual, 'geometry')
            ET.SubElement(ET.SubElement(shell_geometry, 'box'), 'size').text = ' '.join(
                str(value+.01) for value in dimensions)
            neutral = ET.SubElement(shell_visual, 'material')
            for field in ('ambient', 'diffuse'):
                ET.SubElement(neutral, field).text = '.45 .45 .45 1'
            chair_shell_audits.append({'model_name': shell.get('name'),
                'source_marker_model': source_name,
                'source_material': {field: original_material.findtext(field) for field in ('ambient', 'diffuse')},
                'pose': [float(value) for value in original.findtext('pose').split()],
                'source_box_size': dimensions, 'shell_box_size': [value+.01 for value in dimensions],
                'dimension_expansion_m': .01, 'material_rgba': [.45, .45, .45, 1], 'collision_count': 0})
            shells.append(shell)
        for added in (model, *shells):
            if added.findall('.//collision') or added.findall('.//plugin'):
                raise AssertionError('chair colour masks must remain visual-only')
            world.remove(added)
        if READABLE.canonical(tree) != original_tree:
            raise AssertionError('chair material occlusion changed original models')
        for added in (model, *shells):
            world.append(added)
    ET.indent(tree, space='  ')
    raw['world.sdf'] = ET.tostring(tree, encoding='utf-8') + b'\n'
    for filename in ('manifest.json', 'execution_catalog.json'):
        value = json.loads(raw[filename])
        value['world_sha256'] = READABLE.digest(raw['world.sdf'])
        raw[filename] = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    audit = {'schema_version': 'research3-readable-shape-stress/v1',
             'base_instruction_id': source.name, 'partition': ALLOWED[source.name],
             'source_directory': str(source.resolve()), 'source_sha256': original_hashes,
             'readable_source_audit_sha256': READABLE.digest(prior_raw),
             'derivative_sha256': {name: READABLE.digest(value) for name, value in raw.items()},
             'target_category': category, 'target_entity_id': identifier,
             'controlled_occlusion': controlled_occlusion,
             'controlled_material_occlusion': controlled_material_occlusion,
             'neutral_shell': shell_audit,
             'controlled_chair_material_occlusion': controlled_chair_material_occlusion,
             'chair_neutral_shells': chair_shell_audits,
             'condition_version': ('development-chair-material-occlusion-v3' if controlled_chair_material_occlusion
                                   else 'development-material-occlusion-v2' if controlled_material_occlusion
                                   else 'development-chair-occlusion-v2' if controlled_occlusion else 'shape-stress-v1'),
             'source_marker_model': marker_name, 'shape_model': name, 'shape': shape,
             'shape_pose': list(pose), 'radius_m': radius,
             'center_association_distance_m': error,
             'shape_footprint_wall_clearance_m': wall_clearance,
             'association_policy': 'unchanged provider category/attribute matching, nearest unused entity, 0.9m XY radius',
             'material_source': 'exact copy of original target visual material',
             'target_selection': 'lexicographically first stable entity ID within requested category',
             'original_elements_unchanged': True, 'collision_geometry_unchanged': True,
             'map_scene_and_task_ids_unchanged': True, 'visual_only': True,
             'protected_content_used': False, 'labels_generated': False,
             'live_visual_review_completed': False, 'false_positive_observed': False,
             'claim_scope': 'targeted same-material shape stress; not natural error prevalence',
             'context_policy': 'retain all original chairs, four doorways, signs, rooms and corridor; full-frame capture required'}
    if original_hashes != {name: READABLE.digest((source/name).read_bytes()) for name in raw}:
        raise ValueError('source changed during build')
    destination.mkdir(parents=True, exist_ok=False)
    for filename, value in raw.items():
        with (destination/filename).open('xb') as stream:
            stream.write(value)
    with (destination/'source_readable_audit.json').open('xb') as stream:
        stream.write(prior_raw)
    with (destination/'shape_stress_audit.json').open('x') as stream:
        json.dump(audit, stream, indent=2, sort_keys=True)
        stream.write('\n')
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=ROOT/'data/physical_worlds_readable_v1')
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--base', choices=tuple(ALLOWED), default='base-r010')
    parser.add_argument('--category', choices=CATEGORIES, action='append')
    parser.add_argument('--controlled-chair-occlusion', action='store_true',
                        help='prespecified dev10 chair-only v2 sphere pose/radius; no detector changes')
    parser.add_argument('--controlled-material-occlusion', action='store_true',
                        help='dev10 doorway/entrance only: neutral shell over original colour marker')
    parser.add_argument('--controlled-chair-material-occlusion', action='store_true',
                        help='dev10 chair v3: neutral shells over original seat and back, unchanged v2 sphere')
    args = parser.parse_args()
    if sum((args.controlled_chair_occlusion, args.controlled_material_occlusion,
            args.controlled_chair_material_occlusion)) > 1:
        parser.error('choose one controlled intervention')
    categories = args.category or (['chair'] if args.controlled_chair_occlusion
                                  or args.controlled_chair_material_occlusion else
                                  list(CATEGORIES[1:]) if args.controlled_material_occlusion else CATEGORIES)
    for category in categories:
        result = build(args.source_root/args.base, args.output_root/category/args.base, category,
                       controlled_occlusion=args.controlled_chair_occlusion,
                       controlled_material_occlusion=args.controlled_material_occlusion,
                       controlled_chair_material_occlusion=args.controlled_chair_material_occlusion)
        print(f'{args.base} {category}: {result["shape"]}, visual-only, no live accuracy claim')


if __name__ == '__main__':
    main()
