#!/usr/bin/env python3
"""Default-deny post-execution physical audit; never launches or fits on held-out data."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import re
import runpy

import yaml
from language_nav.physical_heldout_authorization import HeldoutEvaluationContext, SOURCE_FILES

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_EXECUTION_SOURCES = {
    'scripts/run_physical_episode.py', 'src/language_nav/live.py',
    'src/language_nav/evaluation/ordered.py', 'src/language_nav/benchmark/physical_catalog.py',
    'src/language_nav/systems/variants.py', 'src/language_nav/planning/policy.py',
    'src/language_nav/grounding/routes.py',
    'ros_ws/src/language_nav_runtime/language_nav_runtime/nav2_adapter.py',
    'ros_ws/src/language_nav_planner/language_nav_planner/node.py',
}
REQUIRED_EXECUTION_SOURCES |= SOURCE_FILES
EVALUATOR_SOURCES = ('scripts/run_physical_episode.py', 'src/language_nav/live.py',
                     'src/language_nav/evaluation/ordered.py',
                     'src/language_nav/physical_heldout_authorization.py')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def local(root, name):
    if not isinstance(name, str) or Path(name).is_absolute() or '..' in Path(name).parts:
        raise ValueError('contained relative evidence path required')
    path = root / name
    if any(p.is_symlink() for p in [path, *path.parents] if p.is_relative_to(root)):
        raise ValueError('symlink evidence rejected')
    if not path.resolve().is_relative_to(root) or not path.is_file():
        raise ValueError('regular contained evidence required')
    return path


def pinned(root, ref):
    path = local(root, ref['path'])
    if digest(path) != ref['sha256']:
        raise ValueError('evidence checksum mismatch')
    return path


def audit(manifest_path, assignments_path, approval_path, *, root=ROOT):
    root = Path(root).resolve()
    # Approval metadata is deliberately the FIRST file read. No protected
    # schedule, assignment, catalogue, outcome or image is opened before this.
    approval = json.loads(Path(approval_path).read_text())
    if (approval.get('schema_version') != 'research3-physical-heldout-authorization/v1'
            or approval.get('status') != 'approved_frozen'
            or approval.get('authorization_scope') != 'physical_heldout_measurement_audit'
            or approval.get('reviewer_type') != 'human'
            or not approval.get('approved_by') or not approval.get('approved_at_utc')
            or not re.fullmatch(r'[0-9a-f]{64}', str(approval.get('manifest_sha256', '')))):
        raise PermissionError('explicit frozen human held-out audit authorization required')
    design_path = pinned(root, approval['design'])
    design = yaml.safe_load(design_path.read_text())
    check = runpy.run_path(str(ROOT / 'scripts/check_physical_design_readiness.py'))['check'](design)
    if design.get('status') != 'frozen' or not check['supplied_design_fields_valid_and_complete']:
        raise PermissionError('complete frozen scientific design required before protected access')
    calibration_path = pinned(root, approval['calibration'])
    calibration = json.loads(calibration_path.read_text())
    if (calibration.get('schema_version') != 'landmark-calibration/v1'
            or calibration.get('partition') not in {'development', 'validation'}):
        raise PermissionError('non-protected calibration required before protected access')
    sources = approval.get('execution_source_sha256', {})
    if not isinstance(sources, dict) or not REQUIRED_EXECUTION_SOURCES <= sources.keys():
        raise PermissionError('complete frozen execution source identity required before protected access')
    for name, value in sources.items():
        if not (name.startswith(('scripts/', 'src/', 'ros_ws/src/')) and name.endswith('.py')):
            raise PermissionError('only explicit execution Python sources may be pinned here')
        pinned(root, {'path': name, 'sha256': value})
    # Staging source consistency is not enough: recomputation executes this
    # checkout's evaluator and imported modules, not the staging Python files.
    # Check that identity before opening any protected schedule or evidence.
    for name in EVALUATOR_SOURCES:
        if digest(ROOT / name) != sources[name]:
            raise PermissionError('actual evaluator source differs from approved execution source: ' + name)
    for module_name, name in (('language_nav.live', 'src/language_nav/live.py'),
                              ('language_nav.evaluation.ordered', 'src/language_nav/evaluation/ordered.py'),
                              ('language_nav.physical_heldout_authorization', 'src/language_nav/physical_heldout_authorization.py')):
        module = importlib.import_module(module_name)
        if Path(module.__file__).resolve() != (ROOT / name).resolve():
            raise PermissionError('actual evaluator source imported from an unapproved location: ' + module_name)
    if digest(manifest_path) != approval['manifest_sha256']:
        raise ValueError('authorized schedule checksum mismatch')
    manifest = json.loads(Path(manifest_path).read_text())
    if (manifest.get('schema_version') != 'research3-physical-heldout-schedule/v1'
            or manifest.get('evidence_scope') != 'physical_world_heldout'
            or manifest.get('design_sha256') != digest(design_path)
            or manifest.get('calibration_sha256') != digest(calibration_path)):
        raise ValueError('physical held-out schedule with frozen provenance required')
    episodes = manifest.get('episodes', [])
    ids = [r.get('episode_id') for r in episodes]
    if not ids or any(not isinstance(i, str) or not i for i in ids) or len(ids) != len(set(ids)):
        raise ValueError('unique nonempty scheduled episode IDs required')
    for row in episodes:
        if (row.get('partition') != 'held_out'
                or not re.fullmatch(r'r3geo_base_r0(?:1[5-9]|20)', str(row.get('map_id', '')))
                or row.get('system_id') not in {'B1', 'B2', 'B4', 'B5', 'B6'}
                or type(row.get('simulation_seed')) is not int
                or row['simulation_seed'] not in design['simulator_seed']['confirmatory_seed_list']):
            raise ValueError('frozen physical held-out schedule membership required')
    assignments = json.loads(Path(assignments_path).read_text())
    if not isinstance(assignments, list):
        raise ValueError('explicit assignment list required')
    by_id = {}
    for item in assignments:
        if item.get('episode_id') not in ids or item['episode_id'] in by_id:
            raise ValueError('unknown or duplicate assignment')
        by_id[item['episode_id']] = item
    evaluate = runpy.run_path(str(ROOT / 'scripts/run_physical_episode.py'))['evaluate']
    audited, unresolved = [], []
    seen_runs = set()
    keys = ('collision', 'timeout', 'instruction_completion', 'navigation_success',
            'terminal_identity_correct', 'goal_error_m', 'distance_travelled_m',
            'ordered_instruction_score', 'trajectory_quality')
    for row in episodes:
        identity = row['episode_id']
        item = by_id.get(identity)
        if item is None:
            unresolved.append({'episode_id': identity, 'reason': 'missing_assignment'})
            continue
        try:
            request_path = pinned(root, item['request'])
            summary_path = pinned(root, item['summary'])
            measurements_path = pinned(root, item['measurements'])
            sealed_path = pinned(root, item['sealed_measurements'])
            request = json.loads(request_path.read_text())
            summary = json.loads(summary_path.read_text())
            measurements = json.loads(measurements_path.read_text())
            sealed = json.loads(sealed_path.read_text())
            if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,95}', str(request.get('run_id', '')))
                    or measurements.get('run_id') != request.get('run_id')
                    or measurements.get('schema_version') != 'research3-live-measurements/v2'
                    or sealed.get('run_id') != request.get('run_id')
                    or sealed.get('schema_version') != 'research3-live-measurements/v2'
                    or summary.get('pre_evaluation_measurements_sha256') != digest(sealed_path)
                    or any(measurements.get(k) != v for k, v in sealed.items())
                    or request.get('source_sha256') != sources):
                raise ValueError('measurement run identity or frozen execution source mismatch')
            if request.get('run_id') in seen_runs:
                raise ValueError('one physical run cannot fill multiple scheduled episodes')
            seen_runs.add(request.get('run_id'))
            if (request.get('schema_version') != 'research3-physical-live-request/v1'
                    or summary.get('schema_version') != 'research3-live-summary/v3'
                    or request.get('partition') != 'held_out'
                    or request.get('protected_test_routes_used') is not True
                    or summary.get('evidence_scope') != 'physical_world_heldout'
                    or summary.get('protected_test_routes_used') is not True
                    or request.get('calibration_sha256') != digest(calibration_path)
                    or request.get('allow_coexistence_trial', False) is not False
                    or summary.get('run_id') != request.get('run_id')
                    or any(request.get(k) != row.get(k) for k in ('map_id', 'variant_id', 'system_id', 'simulation_seed'))
                    or any(summary.get(k) != request.get(k) for k in ('partition', 'map_id', 'variant_id', 'system_id'))
                    or request.get('asset_sha256') != row.get('asset_sha256')
                    or summary.get('measurements_sha256') != digest(measurements_path)
                    or summary.get('infrastructure_failure') is not False):
                raise ValueError('physical measurement identity/provenance mismatch')
            world = Path(request['world_directory'])
            if not world.is_absolute():
                world = root / world
            if not world.resolve().is_relative_to(root):
                raise ValueError('held-out evaluator assets must remain in the authorized workspace')
            for name in request.get('asset_sha256', {}):
                local(root, str((world / name).relative_to(root)))
            required = {'world.sdf', 'map.pgm', 'map.yaml', 'execution_catalog.json',
                        'landmark_scene.yaml', 'manifest.json', 'verified_ordered_geometry.json'}
            if not required <= request.get('asset_sha256', {}).keys():
                raise ValueError('complete evaluator asset pins required')
            request['world_directory'] = str(world)
            context = HeldoutEvaluationContext(request['run_id'], request['map_id'],
                dict(request['asset_sha256']), sealed_path, digest(sealed_path), digest(approval_path))
            recomputed = evaluate(request, sealed, heldout_context=context)
            if sealed != measurements:
                raise ValueError('post-evaluation measurements do not match sealed telemetry and recomputed annotations')
            if any(recomputed.get(k) != summary.get(k) for k in keys):
                raise ValueError('stored summary differs from independent physical measurements')
            if recomputed.get('trajectory_quality', {}).get('valid') is not True:
                raise ValueError('unknown trajectory quality')
            if any(type(recomputed.get(k)) is not bool for k in
                   ('collision', 'timeout', 'instruction_completion', 'navigation_success', 'terminal_identity_correct')):
                raise ValueError('unknown physical endpoint retained unresolved')
            audited.append({'episode_id': identity, 'run_id': request['run_id'],
                            'outcomes': {k: recomputed.get(k) for k in keys},
                            'measurements_sha256': digest(measurements_path),
                            'pre_evaluation_measurements_sha256': digest(sealed_path)})
        except (ValueError, KeyError, OSError, TypeError) as exc:
            unresolved.append({'episode_id': identity, 'reason': str(exc)})
    complete = len(audited) == len(episodes) and not unresolved
    return {'schema_version': 'research3-physical-heldout-audit/v1',
            'evidence_scope': 'physical_world_heldout', 'authorized': True,
            'human_identity_authenticated': False, 'protected_data_used': True,
            'human_labels_generated': False, 'calibration_fitted': False,
            'manifest_sha256': digest(manifest_path), 'design_sha256': digest(design_path),
            'calibration_sha256': digest(calibration_path), 'approval_sha256': digest(approval_path),
            'execution_source_sha256': sources,
            'scheduled_episode_ids': ids, 'audited_episode_ids': [r['episode_id'] for r in audited],
            'scheduled_count': len(ids), 'audited_count': len(audited),
            'passed': complete, 'complete': complete,
            'independent_measurement_verified': complete, 'episodes': audited,
            'unresolved': unresolved, 'inferential_analysis_complete': False,
            'live_execution_implemented_by_this_tool': False,
            'claim_limit': 'Post-execution measurement audit only; no graph-to-physical substitution, inference or release approval.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest', 'assignments', 'approval', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = audit(args.manifest, args.assignments, args.approval)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    raise SystemExit(0 if result['complete'] else 1)


if __name__ == '__main__':
    main()
