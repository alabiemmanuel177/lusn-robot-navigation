#!/usr/bin/env python3
"""Revise retained nonprotected views, dispatch one guarded case, or audit sources."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import runpy

import yaml
from language_nav.camera_configuration import (validate_capture_source_freeze, validate_camera_freeze,
                                               validate_frozen_capture_view)
from language_nav.capture_view import validate_capture_pose

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'reports/physical_live_episodes'
RUNNER = ROOT / 'scripts/run_physical_episode.py'
SMOKE = runpy.run_path(str(ROOT / 'scripts/physical_engineering_smoke.py'))
PACK = runpy.run_path(str(ROOT / 'scripts/package_physical_engineering.py'))
ASSETS = {'world.sdf', 'execution_catalog.json', 'landmark_scene.yaml', 'map.pgm', 'map.yaml',
          'manifest.json', 'verified_ordered_geometry.json'}
STRESS = {'chair': 'v3', 'doorway': 'v2', 'laboratory_entrance': 'v2', 'office_entrance': 'v2'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, payload):
    with Path(path).open('x') as stream:
        json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def nonprotected(request):
    match = re.fullmatch(r'r3geo_base_r(\d{3})', request.get('map_id', ''))
    number = int(match[1]) if match else 0
    expected = 'development' if 1 <= number <= 10 else 'validation' if 11 <= number <= 14 else None
    if expected is None or request.get('partition') != expected or request.get('protected_test_routes_used') is not False:
        raise ValueError('explicit nonprotected request required before world access')
    return f'base-r{number:03}'


def prepare(directory, historical_request, prefix='r3-current-v1'):
    directory = Path(directory).resolve()
    if (directory / 'recapture_plan.json').exists() or (directory / 'stress_commands.json').exists():
        raise FileExistsError('recapture plan and stress commands are create-once')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,40}', prefix):
        raise ValueError('safe new prefix required')
    source_hash = validate_capture_source_freeze(directory / 'current_source_snapshot.json')
    original = read(directory / 'plan.json')
    if original.get('schema_version') != 'research3-stationary-capture-plan/v1' or len(original.get('views', [])) != 42:
        raise ValueError('existing complete 42-view plan required')
    histories = read(historical_request)['runs']
    if len(histories) != 46:
        raise ValueError('explicit 42 ordinary plus four final stress references required')
    ordinary = {(view['base_instruction_id'], view['category']): view for view in original['views']}
    views, profiles = [], {}
    stress_profile_raw = None
    for reference in histories:
        request_path = PACK['safe_path'](ROOT, reference['request_member'])
        if request_path.name != 'request.json' or request_path.parent.parent != RUNS:
            raise ValueError('historical reference must be an owned request')
        previous = read(request_path)
        base = nonprotected(previous)
        categories = previous.get('capture_target_categories')
        if (previous.get('capture_only') is not True or previous.get('capture_frame_budget') != 1
                or not isinstance(categories, list) or len(categories) != 1
                or previous.get('camera_horizontal_fov') != 2.0 or previous.get('simulation_seed') != 1):
            raise ValueError('historical capture settings outside preserved scope')
        category = categories[0]
        world = Path(previous['world_directory']).resolve()
        expected = ROOT / 'data/physical_worlds_readable_v1' / base
        stress = world != expected
        if stress:
            if category not in STRESS or base != 'base-r010' or world != ROOT / 'data' / ('physical_shape_stress_dev10_' + STRESS[category]) / category / base:
                raise ValueError('only the four final development stress derivatives are permitted')
            run_id = prefix + '-stress-' + category
            profile_name = 'profiles/stress-dev10.yaml'
        else:
            new_view = ordinary[(base, category)]
            if new_view['capture_pose'] != previous['capture_pose']:
                raise ValueError('new ordinary pose differs from original retained view')
            run_id = new_view['run_id']
            profile_name = 'profiles/' + base + '.yaml'
        if run_id == previous['run_id'] or not run_id.startswith(prefix + '-'):
            raise ValueError('fresh run identity must not reuse historical run')
        old_profile = PACK['safe_path'](ROOT, reference['profile_member'])
        if sha(old_profile) != previous['camera_profile_sha256']:
            raise ValueError('historical profile bytes differ from request')
        old_settings = yaml.safe_load(old_profile.read_text())
        if stress:
            raw = old_profile.read_bytes()
            if stress_profile_raw is not None and raw != stress_profile_raw:
                raise ValueError('stress profiles are not identical')
            stress_profile_raw = raw
            profile_hash = hashlib.sha256(raw).hexdigest()
        else:
            settings = yaml.safe_load((directory / profile_name).read_text())
            if any(settings.get(key) != old_settings.get(key) for key in ('camera_palette', 'color_tolerance', 'map_scope')):
                raise ValueError('new camera palette/tolerance/map differs from retained settings')
            profile_hash = sha(directory / profile_name)
        profiles[profile_name] = profile_hash
        pose = validate_capture_pose(world, **previous['capture_pose'])
        if set(previous['asset_sha256']) != ASSETS or any(sha(world / name) != expected for name, expected in previous['asset_sha256'].items()):
            raise ValueError('world differs from retained capture assets')
        views.append({'run_id': run_id, 'original_run_id': previous['run_id'], 'base_instruction_id': base,
            'map_id': previous['map_id'], 'partition': previous['partition'], 'category': category,
            'phase': 'stress' if stress else previous['partition'], 'capture_pose': pose,
            'world_directory': str(world), 'asset_sha256': previous['asset_sha256'],
            'profile_file': profile_name, 'profile_sha256': profile_hash,
            'historical_profile_sha256': previous['camera_profile_sha256'],
            'camera_horizontal_fov': 2.0, 'camera_color_tolerance': old_settings['color_tolerance'],
            'simulation_seed': 1, 'timeout_s': 25, 'frame_budget': 1,
            'original_request_sha256': sha(request_path), 'command_argv': None,
            'execution_gate': 'fresh_development_visual_checks_and_new_validation_freeze_required'
                if previous['partition'] == 'validation' else 'one_case_lock_source_and_resource_checks_required'})
    if len({view['run_id'] for view in views}) != 46 or len(profiles) != 15:
        raise ValueError('complete distinct 46-view/15-profile revision required')
    plan = {'schema_version': 'research3-current-source-recapture-plan/v1',
            'status': 'engineering_recapture_not_calibration_or_protocol_approval',
            'protected_data_used': False, 'human_labels_generated': False, 'qa_attestations_generated': False,
            'original_plan_sha256': sha(directory / 'plan.json'), 'snapshot_sha256': source_hash,
            'historical_request_sha256': sha(historical_request), 'profile_files': profiles,
            'views': views, 'ros_domain_id': 89,
            'orchestration_source_sha256': {str(path.relative_to(ROOT)): sha(path) for path in
                (Path(__file__).resolve(), ROOT / 'scripts/physical_engineering_smoke.py')},
            'limits': ['No old QA or verdicts carry forward. New captures require exact join and fresh individual visual QA.',
                       'The source guard observes hashes at checkpoints, not continuously.',
                       'Four stress views are deliberate engineering conditions, not natural-error prevalence.']}
    if stress_profile_raw is not None:
        with (directory / 'profiles/stress-dev10.yaml').open('xb') as stream:
            stream.write(stress_profile_raw)
    for view in views:
        if view['partition'] == 'development':
            view['command_argv'] = command(plan, view, directory, False, validate_sources=False)
    stress_commands = {'schema_version': 'research3-current-source-stress-commands/v1',
                       'protected_data_used': False, 'human_labels_generated': False,
                       'commands': [view for view in views if view['phase'] == 'stress']}
    write(directory / 'stress_commands.json', stress_commands)
    plan['stress_commands_sha256'] = sha(directory / 'stress_commands.json')
    write(directory / 'recapture_plan.json', plan)
    return plan


def command(plan, view, directory, coexistence, settings=None, *, validate_sources=True):
    directory = Path(directory).resolve()
    if validate_sources:
        if validate_capture_source_freeze(directory / 'current_source_snapshot.json') != plan['snapshot_sha256']:
            raise ValueError('current capture snapshot differs from plan')
    if plan['protected_data_used'] is not False or view not in plan['views']:
        raise ValueError('unbound/nonprotected view required')
    base = nonprotected({'map_id': view['map_id'], 'partition': view['partition'], 'protected_test_routes_used': False})
    profile = directory / view['profile_file']
    expected_profile = view['profile_sha256']
    world = Path(view['world_directory'])
    expected_world = ROOT / 'data/physical_worlds_readable_v1' / base
    if view['phase'] == 'stress':
        expected_world = ROOT / 'data' / ('physical_shape_stress_dev10_' + STRESS[view['category']]) / view['category'] / 'base-r010'
    if world != expected_world or not str(view['run_id']).startswith('r3-current-'):
        raise ValueError('world/run outside fresh capture scope')
    freeze = None
    if view['partition'] == 'validation':
        if settings is None:
            raise ValueError('fresh validation settings freeze required')
        settings = Path(settings).resolve()
        freeze = settings / 'camera_settings_freeze.json'
        profile = settings / 'profiles' / (base + '.yaml')
        expected_profile = view['historical_profile_sha256']
        frozen = read(freeze)
        fresh_ids = {row['run_id'] for row in plan['views'] if row['phase'] == 'development'}
        snapshot = read(directory / 'current_source_snapshot.json')
        for evidence in frozen.get('development_evidence', []):
            evidence_run = Path(evidence['run_directory'])
            if evidence_run.parent != RUNS or evidence_run.name not in fresh_ids:
                raise ValueError('validation freeze must use fresh planned development evidence')
            request = read(evidence_run / 'request.json')
            if any(request.get(key) != snapshot[key] for key in ('source_sha256', 'provider_source_snapshot')):
                raise ValueError('validation development evidence has different frozen sources')
        validate_camera_freeze(freeze, map_id=view['map_id'], profile=profile, horizontal_fov=2.0)
        validate_frozen_capture_view(freeze, map_id=view['map_id'], category=view['category'], pose=view['capture_pose'], world=world)
    if sha(profile) != expected_profile or any(sha(world / name) != expected for name, expected in view['asset_sha256'].items()):
        raise ValueError('planned profile/world changed')
    argv = ['nice', '-n', '15', 'python3', str(RUNNER), '--world', str(world),
            '--variant-id', base + '-truthful_original-s0', '--run-id', view['run_id'],
            '--ros-domain-id', '89', '--simulation-seed', '1', '--timeout', '25',
            '--capture-only', '--capture-frame-budget', '1', '--capture-target-category', view['category'],
            '--capture-pose', *[str(view['capture_pose'][key]) for key in ('x', 'y', 'yaw')],
            '--camera-horizontal-fov', '2.0', '--camera-profile', str(profile),
            '--capture-source-freeze', str(directory / 'current_source_snapshot.json')]
    if freeze is not None:
        argv.extend(['--camera-settings-freeze', str(freeze)])
    if coexistence:
        argv.append('--allow-coexistence-trial')
    return argv


def dispatch(directory, run_id, expected_plan_hash, output, *, coexistence=False, settings=None):
    directory, output = Path(directory).resolve(), Path(output)
    path = directory / 'recapture_plan.json'
    if sha(path) != expected_plan_hash:
        raise ValueError('explicit recapture plan hash mismatch')
    plan = read(path)
    matches = [view for view in plan['views'] if view['run_id'] == run_id]
    if len(matches) != 1 or (RUNS / run_id).exists():
        raise ValueError('one new planned run required; existing runs are never relaunched')
    if sha(directory / 'plan.json') != plan['original_plan_sha256']:
        raise ValueError('base plan changed')
    for name, expected in plan['orchestration_source_sha256'].items():
        if sha(ROOT / name) != expected:
            raise ValueError('orchestration changed since plan')
    fd = os.open(SMOKE['LOCK'], os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        SMOKE['require_no_live_runner']()
        argv = command(plan, matches[0], directory, coexistence, settings)
        SMOKE['coexistence_headroom']()
        if not coexistence:
            SMOKE['require_research2_idle']()
        output.mkdir(parents=True, exist_ok=False)
        event = {'schema_version': 'research3-single-capture-dispatch/v1', 'run_id': run_id,
                 'plan_sha256': expected_plan_hash, 'argv': argv, 'source_snapshot_sha256': plan['snapshot_sha256'],
                 'child_lifetime_lock': True, 'human_labels_generated': False}
        write(output / 'start.json', event)
        env = dict(os.environ)
        env.update({name: '2' for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')})
        try:
            if sha(path) != expected_plan_hash:
                raise ValueError('plan changed before dispatch')
            with (output / 'capture.log').open('x') as log:
                code = SMOKE['run_locked'](argv, env, log, fd)
            write(output / 'finish.json', {**event, 'returncode': code, 'capture_correctness_established': False})
            return code
        except BaseException as exc:
            write(output / 'failure.json', {**event, 'error_type': type(exc).__name__, 'error': str(exc)})
            raise
    finally:
        os.close(fd)  # No LOCK_UN: a surviving child retains the inherited lock.


def audit(directory, archive, expected_archive_hash):
    directory = Path(directory).resolve()
    snapshot = read(directory / 'current_source_snapshot.json')
    plan = read(directory / 'recapture_plan.json')
    if sha(directory / 'current_source_snapshot.json') != plan['snapshot_sha256']:
        raise ValueError('recorded source snapshot changed')
    if sha(archive) != expected_archive_hash:
        raise ValueError('source archive checksum mismatch')
    PACK['capture_source_archive_paths'](ROOT, Path(archive))
    manifest = PACK['verify_archive'](Path(archive))
    if manifest['capture_source_snapshot'] != snapshot or manifest.get('source_snapshot_input_sha256') != plan['snapshot_sha256']:
        raise ValueError('retained source archive differs from capture snapshot')
    rows = []
    for view in plan['views']:
        run = RUNS / view['run_id']
        gaps = []
        if not (run / 'request.json').is_file():
            rows.append({'run_id': view['run_id'], 'status': 'pending', 'gaps': ['missing_request']})
            continue
        request = read(run / 'request.json')
        nonprotected(request)
        for key in ('source_sha256', 'provider_source_snapshot'):
            if request.get(key) != snapshot[key]:
                gaps.append('missing_or_mismatched_' + key)
        for key in ('map_id', 'run_id', 'partition', 'capture_pose', 'asset_sha256'):
            if request.get(key) != view[key]:
                gaps.append('mismatched_' + key)
        expected_profile = view['historical_profile_sha256'] if view['partition'] == 'validation' else view['profile_sha256']
        if request.get('camera_profile_sha256') != expected_profile or request.get('camera_horizontal_fov') != 2.0:
            gaps.append('profile_or_fov_mismatch')
        if request.get('capture_source_freeze_sha256') != plan['snapshot_sha256']:
            gaps.append('missing_or_mismatched_prelaunch_source_freeze')
        summary = read(run / 'capture_summary.json') if (run / 'capture_summary.json').is_file() else {}
        checks = summary.get('capture_source_checks', [])
        if (len(checks) < 3 or any(row.get('snapshot_sha256') != plan['snapshot_sha256'] for row in checks)
                or summary.get('capture_source_freeze_sha256') != plan['snapshot_sha256']):
            gaps.append('source_guard_checkpoint_evidence_missing_or_mismatched')
        if summary.get('complete') is not True:
            gaps.append('capture_incomplete')
        rows.append({'run_id': view['run_id'], 'status': 'source_bound_capture' if not gaps else 'blocked',
                     'gaps': gaps, 'request_sha256': sha(run / 'request.json'),
                     'capture_summary_sha256': sha(run / 'capture_summary.json') if summary else None})
    return {'schema_version': 'research3-current-capture-source-audit/v1', 'rows': rows,
            'plan_sha256': sha(directory / 'recapture_plan.json'), 'archive_sha256': expected_archive_hash,
            'all_46_source_bound': len(rows) == 46 and all(row['status'] == 'source_bound_capture' for row in rows),
            'historical_current_source_hashes_not_substituted': True, 'human_labels_generated': False,
            'qa_attestations_generated': False, 'calibration_validated': False,
            'limit': 'Request/archive/checkpoint source bindings only; no continuous attestation, media QA or labels.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'dispatch', 'audit'))
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--historical-request', type=Path)
    parser.add_argument('--run-prefix', default='r3-current-v1')
    parser.add_argument('--run-id')
    parser.add_argument('--plan-sha256')
    parser.add_argument('--allow-coexistence', action='store_true')
    parser.add_argument('--validation-settings', type=Path)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--archive-sha256')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.mode == 'prepare':
        prepare(args.directory, args.historical_request, args.run_prefix)
        print(sha(args.directory / 'recapture_plan.json'))
    elif args.mode == 'dispatch':
        raise SystemExit(dispatch(args.directory, args.run_id, args.plan_sha256, args.output,
            coexistence=args.allow_coexistence, settings=args.validation_settings))
    else:
        report = audit(args.directory, args.archive, args.archive_sha256)
        write(args.output, report)
        raise SystemExit(0 if report['all_46_source_bound'] else 2)


if __name__ == '__main__':
    main()
