#!/usr/bin/env python3
"""Build-only authorized protected derivatives and a pending runtime schedule.

No Gazebo, protected review, calibration fitting or live authorization. Failed
builds remain as immutable partial output; no replacement or automatic retry.
"""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import sys

from language_nav.physical_asset_authorization import ROOT, authorize_build, sha, FILES


def load(name):
    spec = importlib.util.spec_from_file_location('authorized_' + name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_once(path, data):
    with Path(path).open('x') as stream:
        json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def build(path, digest, *, root=ROOT):
    context = authorize_build(path, digest, root=root)
    # Sibling script import used by the existing independent geometry verifier.
    sys.path.insert(0, str(ROOT / 'scripts'))
    readable = load('build_readable_physical_worlds')
    absence = load('build_physical_absence_worlds')
    for row in context.plan['worlds']:
        fov, tolerance = row.get('camera_horizontal_fov'), row.get('camera_color_tolerance')
        if (type(fov) not in (float, int) or not .5 <= fov <= 2.
                or type(tolerance) not in (float, int) or not math.isfinite(tolerance) or tolerance <= 0):
            raise PermissionError('explicit approved finite camera recipe settings required')
        if (type(row.get('timeout_s')) not in (float, int) or not math.isfinite(row['timeout_s'])
                or row['timeout_s'] <= 0):
            raise PermissionError('explicit positive finite episode timeout required')
        context.validate_operation('readable', context.root / row['source_directory'],
                                   context.output / 'readable' / row['base_instruction_id'])
    context.output.mkdir(parents=True, exist_ok=False)
    write_once(context.output / 'build_request.json', {
        'schema_version': 'research3-protected-derivative-build-request/v1',
        'authorization_sha256': digest, 'protected_data_used': True, 'human_labels_generated': False,
        'live_execution_authorized': False})
    episodes, outputs = [], []
    paired_block_index = 0
    try:
        for row in context.plan['worlds']:
            base = row['base_instruction_id']
            source = context.root / row['source_directory']
            readable_dir = context.output / 'readable' / base
            readable.build(source, readable_dir, protected_build=context)
            absent_base = context.output / 'absence_base' / base
            report = absence.build_absence(source, absent_base, context.instructions[base]['canonical'],
                                           protected_build=context)
            context.retain_generated(absent_base)
            absent_readable = context.output / 'missing_landmark' / base
            visual = readable.build(absent_base, absent_readable, protected_build=context)
            # Visual-only additions preserve the independently verified removal.
            if visual['collision_geometry_unchanged'] is not True or visual['map_bytes_unchanged'] is not True:
                raise ValueError('readable absence derivative changed physical removal proof')
            report.update(asset_sha256={name: sha(absent_readable / name) for name in report['asset_sha256']},
                visual_derivative_audit_sha256=sha(absent_readable / 'visual_derivative_audit.json'),
                base_absence_intervention_sha256=sha(absent_base / 'absence_intervention.json'))
            write_once(absent_readable / 'absence_intervention.json', report)
            for directory in (readable_dir, absent_readable):
                outputs.append({'directory': str(directory.relative_to(context.root)),
                                'asset_sha256': {name: sha(directory / name) for name in FILES}})
            for seed in context.design['simulator_seed']['confirmatory_seed_list']:
                for variant in context.instructions[base]['deployed_variants']:
                    condition = variant['variant_id'].removeprefix(base + '-').removesuffix('-s0')
                    directory = absent_readable if condition == 'missing_landmark' else readable_dir
                    names = {'world.sdf', 'map.pgm', 'map.yaml', 'execution_catalog.json', 'landmark_scene.yaml',
                             'manifest.json', 'verified_ordered_geometry.json'}
                    if condition == 'missing_landmark':
                        names.add('absence_intervention.json')
                    for system in ('B1', 'B2', 'B4', 'B5', 'B6'):
                        identity = f'{base}-{condition}-{system}-seed{seed}'
                        episodes.append({'episode_id': identity, 'run_id': 'r3heldout-' + sha_text(identity)[:24],
                            'partition': 'held_out', 'runtime_partition': 'test', 'catalog_partition': 'held_out',
                            'map_id': 'r3geo_' + base.replace('-', '_'), 'base_instruction_id': base,
                            'variant_id': variant['variant_id'], 'instruction': variant,
                            'condition': condition, 'system_id': system, 'simulation_seed': seed,
                            'paired_block_index': paired_block_index, 'timeout_s': row['timeout_s'],
                            'camera_horizontal_fov': row['camera_horizontal_fov'],
                            'camera_color_tolerance': row['camera_color_tolerance'],
                            'world_directory': str(directory.relative_to(context.root)),
                            'asset_sha256': {name: sha(directory / name) for name in names}})
                    paired_block_index += 1
        schedule = {'schema_version': 'research3-physical-heldout-schedule/v1',
            'status': 'pending_separate_runtime_authorization', 'evidence_scope': 'physical_world_heldout',
            'design_sha256': context.design_hash, 'calibration_sha256': context.calibration_hash,
            'build_authorization_sha256': digest, 'protected_data_used': True,
            'live_execution_authorized': False, 'human_labels_generated': False,
            'execution_order_policy': 'draft listing only; freeze counterbalancing before runtime approval',
            'episodes': episodes}
        write_once(context.output / 'runtime_schedule_template.json', schedule)
        result = {'schema_version': 'research3-authorized-protected-derivatives/v1',
            'passed': True, 'protected_data_used': True, 'human_labels_generated': False,
            'live_execution_authorized': False, 'geometry_verified': True,
            'outputs': outputs, 'episode_count': len(episodes),
            'runtime_schedule_sha256': sha(context.output / 'runtime_schedule_template.json')}
        write_once(context.output / 'build_result.json', result)
        return result
    except BaseException as exc:
        write_once(context.output / 'build_failure.json', {'error_type': type(exc).__name__, 'error': str(exc),
            'partial_output_retained': True, 'live_execution_authorized': False})
        raise


def sha_text(value):
    import hashlib
    return hashlib.sha256(value.encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authorization', type=Path, required=True)
    parser.add_argument('--authorization-sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.authorization, args.authorization_sha256), indent=2))


if __name__ == '__main__':
    main()
