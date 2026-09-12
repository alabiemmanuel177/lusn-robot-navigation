#!/usr/bin/env python3
"""Create and audit non-protected absent-chair derivatives; never authorize live use."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import yaml

from language_nav.world.physical import build_world
from verify_physical_world import verify

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_absence(original, destination, instruction):
    original, destination = Path(original), Path(destination)
    # Match split to stable ID before touching source assets.
    base = instruction['base_instruction_id']
    allowed = {f'base-r{i:03}': 'development' if i <= 10 else 'validation' for i in range(1, 15)}
    if allowed.get(base) != instruction['partition'] or base not in allowed:
        raise PermissionError('non-protected instruction identity required')
    names = ('world.sdf', 'map.pgm', 'map.yaml', 'manifest.json', 'landmark_scene.yaml',
             'execution_catalog.json', 'verified_ordered_geometry.json')
    before = {name: sha(original / name) for name in names}
    baseline = json.loads((original / 'manifest.json').read_text())
    if baseline['base_instruction_id'] != base or baseline['partition'] != allowed[base]:
        raise ValueError('source identity mismatch')
    result = build_world(destination, instruction, anchor_present=False)
    old_models = {m.attrib['name']: ET.tostring(m) for m in ET.parse(original / 'world.sdf').findall('./world/model')}
    new_models = {m.attrib['name']: ET.tostring(m) for m in ET.parse(destination / 'world.sdf').findall('./world/model')}
    removed = sorted(set(old_models) - set(new_models))
    if (len(removed) != 6 or not all(name.startswith('chair_') for name in removed)
            or any(old_models.get(name) != value for name, value in new_models.items())):
        raise ValueError('derivative changed geometry other than the six chair components')
    for key in ('start', 'candidates', 'expected_route_id', 'terminal_entities', 'anchor_pose', 'layout'):
        if baseline[key] != result[key]:
            raise ValueError('canonical task changed: ' + key)
    scene = yaml.safe_load((destination / 'landmark_scene.yaml').read_text())
    if any(entity['category'] == 'chair' for entity in scene['entities']):
        raise ValueError('chair remains in perception truth')
    audit = verify(destination)
    if before != {name: sha(original / name) for name in names}:
        raise ValueError('original source changed during derivative build')
    report = {'schema_version': 'research3-physical-absence-intervention/v1',
              'base_instruction_id': base, 'partition': allowed[base],
              'source_sha256': before, 'removed_models': removed,
              'removed_entity_id': instruction['anchor_entity_id'],
              'map_policy': 'remove_chair_occupancy_for_all_systems',
              'task_policy': 'retain_original_goals_and_ordered_reference_plane_at_former_chair_location',
              'interpretation': 'reference-plane progress is not proof of observing an absent chair',
              'geometry_audit_passed': audit['passed'],
              'asset_sha256': {name: sha(destination / name) for name in names},
              'live_validation_completed': False, 'execution_authorized': False,
              'protected_content_used': False}
    with (destination / 'absence_intervention.json').open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--base-id', choices=[f'base-r{i:03}' for i in range(1, 15)])
    args = parser.parse_args()
    rows = json.loads((ROOT / 'data/manifests/instruction_benchmark_v0.1.json').read_text())['instructions']
    rows = [row for row in rows if row['partition'] in {'development', 'validation'}
            and (args.base_id is None or row['base_instruction_id'] == args.base_id)]
    args.output.mkdir(parents=True, exist_ok=False)
    for row in rows:
        base = row['base_instruction_id']
        result = build_absence(ROOT / 'data/physical_worlds_v1' / base, args.output / base, row)
        print(base, 'geometry_audit_passed=', result['geometry_audit_passed'])


if __name__ == '__main__':
    main()
