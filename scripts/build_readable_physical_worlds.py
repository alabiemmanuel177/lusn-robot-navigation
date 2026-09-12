#!/usr/bin/env python3
"""Create-once non-protected visual signage derivatives; never launches Gazebo."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import yaml

ROOT = Path(__file__).resolve().parents[1]
FILES = ('world.sdf', 'map.pgm', 'map.yaml', 'manifest.json', 'execution_catalog.json',
         'landmark_scene.yaml', 'ordered_geometry.json', 'verified_ordered_geometry.json',
         'geometry_audit.json')
FONT = {
    'L': ('10000','10000','10000','10000','10000','10000','11111'),
    'A': ('01110','10001','10001','11111','10001','10001','10001'),
    'B': ('11110','10001','10001','11110','10001','10001','11110'),
    'O': ('01110','10001','10001','10001','10001','10001','01110'),
    'F': ('11111','10000','10000','11110','10000','10000','10000'),
    'I': ('11111','00100','00100','00100','00100','00100','11111'),
    'C': ('01111','10000','10000','10000','10000','10000','01111'),
    'E': ('11111','10000','10000','11110','10000','10000','11111'),
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(node):
    return (node.tag, tuple(sorted(node.attrib.items())), (node.text or '').strip(),
            tuple(canonical(child) for child in node))


def box(link, name, pose, size, color):
    visual = ET.SubElement(link, 'visual', name=name)
    ET.SubElement(visual, 'pose').text = ' '.join(f'{v:.9g}' for v in pose)
    geometry = ET.SubElement(visual, 'geometry')
    ET.SubElement(ET.SubElement(geometry, 'box'), 'size').text = ' '.join(map(str, size))
    material = ET.SubElement(visual, 'material')
    for field in ('ambient', 'diffuse', 'emissive'):
        ET.SubElement(material, field).text = color
    ET.SubElement(visual, 'cast_shadows').text = 'false'


def sign(world, name, text, x, y, yaw):
    model = ET.SubElement(world, 'model', name=name)
    ET.SubElement(model, 'static').text = 'true'
    ET.SubElement(model, 'pose').text = f'{x:.9g} {y:.9g} 1.43 0 0 {yaw:.12g}'
    link = ET.SubElement(model, 'link', name='lettering')
    box(link, 'backboard', (0,0,0,0,0,0), (1.02,.018,.30), '.015 .015 .015 1')
    pixel = .026
    columns = len(text) * 6 - 1
    for index, letter in enumerate(text):
        for row, values in enumerate(FONT[letter]):
            for column, value in enumerate(values):
                if value != '1':
                    continue
                # Local front is -Y. +X reads left-to-right from this face.
                px = (index * 6 + column - (columns-1)/2) * pixel
                pz = (3-row) * pixel
                box(link, f'letter_{index}_{row}_{column}', (px,-.014,pz,0,0,0),
                    (pixel*.94,.008,pixel*.94), '.96 .96 .96 1')
    return {'model_name': name, 'text': text, 'position': [x,y,1.43],
            'yaw': yaw, 'front_normal': [math.sin(yaw), -math.cos(yaw), 0],
            'width_m': 1.02, 'height_m': .30, 'collision_count': 0}


def build(source: Path, destination: Path, *, protected_build=None) -> dict:
    source, destination = Path(source), Path(destination)
    match = re.fullmatch(r'base-r(\d{3})', source.name)
    if protected_build is not None:
        from language_nav.physical_asset_authorization import ProtectedBuild
        if not isinstance(protected_build, ProtectedBuild):
            raise PermissionError('validated protected build context required')
        protected_build.validate_operation('readable', source, destination)
    allowed = range(15, 21) if protected_build is not None else range(1, 15)
    if not match or int(match[1]) not in allowed:
        raise PermissionError('only known development/validation source IDs may be opened')
    if destination.exists():
        raise FileExistsError(destination)
    raw = {name: (source / name).read_bytes() for name in FILES}
    manifest = json.loads(raw['manifest.json'])
    catalog = json.loads(raw['execution_catalog.json'])
    scene = yaml.safe_load(raw['landmark_scene.yaml'])
    expected_partition = 'held_out' if protected_build is not None else 'development' if int(match[1]) <= 10 else 'validation'
    if (any(item.get('partition') != expected_partition for item in (manifest,catalog))
            or scene.get('partition') != ('test' if protected_build is not None else expected_partition)):
        raise PermissionError('non-protected source partition mismatch')
    if any(item.get('world_sha256') != digest(raw['world.sdf']) for item in (manifest,catalog)):
        raise ValueError('source world hash mismatch')
    tree = ET.fromstring(raw['world.sdf'])
    world = tree.find('world')
    original_children = [canonical(child) for child in world]
    model_names = {model.get('name') for model in world.findall('model')}
    entrances = [entity for entity in scene['entities']
                 if entity['category'] in ('laboratory_entrance','office_entrance')]
    if len(entrances) != 4:
        raise ValueError('expected four existing entrance categories')
    half = manifest['layout']['corridor_half_width']
    added = []
    for entity in entrances:
        marker = world.find(f"model[@name='{entity['entity_id']}_sign']")
        if marker is None:
            raise ValueError('missing original entrance marker')
        side = 1 if entity['pose']['y'] > 0 else -1
        x = entity['pose']['x'] - .53
        text = 'LAB' if entity['category'] == 'laboratory_entrance' else 'OFFICE'
        for face, y, yaw in (
            ('corridor', side*(half-.10), 0 if side > 0 else math.pi),
            ('room', side*(half+.10), math.pi if side > 0 else 0)):
            name = f"readable_{entity['entity_id']}_{face}"
            if name in model_names:
                raise ValueError('readable derivative already present')
            added.append(sign(world, name, text, x, y, yaw))
    if [canonical(child) for child in list(world)[:len(original_children)]] != original_children:
        raise AssertionError('original simulation elements changed')
    for model in list(world)[len(original_children):]:
        if model.findall('.//collision') or model.findall('.//plugin'):
            raise AssertionError('added signage must be visual-only')
    ET.indent(tree, space='  ')
    raw['world.sdf'] = ET.tostring(tree, encoding='utf-8') + b'\n'
    updated_hash = digest(raw['world.sdf'])
    for name in ('manifest.json','execution_catalog.json'):
        payload = json.loads(raw[name])
        payload['world_sha256'] = updated_hash
        raw[name] = (json.dumps(payload,indent=2,sort_keys=True)+'\n').encode()
    audit = {
        'schema_version': 'research3-readable-visual-derivative/v1',
        'partition': expected_partition, 'source_directory': str(source.resolve()),
        'protected_content_used': protected_build is not None, 'visual_only': True,
        'original_elements_unchanged': True, 'collision_geometry_unchanged': True,
        'map_bytes_unchanged': True, 'task_and_entity_ids_unchanged': True,
        'live_readability_validated': False,
        'prior_geometry_audit_scope': 'original world hash; inherited collision proof only',
        'prior_geometry_audit_sha256': digest(raw['geometry_audit.json']),
        'source_sha256': {name: digest((source/name).read_bytes()) for name in FILES},
        'derivative_sha256': {name: digest(data) for name,data in raw.items()},
        'signs': added,
    }
    destination.mkdir(parents=True, exist_ok=False)
    for name,data in raw.items():
        with (destination/name).open('xb') as stream:
            stream.write(data)
    with (destination/'visual_derivative_audit.json').open('x') as stream:
        json.dump(audit, stream, indent=2, sort_keys=True)
        stream.write('\n')
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=ROOT/'data/physical_worlds_v1')
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--base', default='base-r010')
    parser.add_argument('--all-nonprotected', action='store_true')
    args = parser.parse_args()
    bases = [f'base-r{i:03}' for i in range(1,15)] if args.all_nonprotected else [args.base]
    for base in bases:
        audit = build(args.source_root/base, args.output_root/base)
        print(f'{base}: {len(audit["signs"])} visual-only signs, no live readability claim')


if __name__ == '__main__':
    main()
