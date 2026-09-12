#!/usr/bin/env python3
"""Serial non-protected execution behind pinned approval gates; plan-only by default."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import runpy
import subprocess
import sys
from tempfile import TemporaryDirectory

import yaml
from language_nav.benchmark import CorruptionCondition
from language_nav.adapters.landmark_palette import adapt_scene_palette
from language_nav.camera_configuration import capture_provider_snapshot

ROOT = Path(__file__).resolve().parents[1]
DESIGN = runpy.run_path(str(ROOT / 'scripts/check_physical_design_readiness.py'))['check']
EXPORT = runpy.run_path(str(ROOT / 'scripts/export_physical_campaign_outcomes.py'))['export']
ANALYZE = runpy.run_path(str(ROOT / 'scripts/analyze_physical_campaign.py'))['analyze']
GATES = ('physical_inspection', 'condition_interventions', 'independent_measurement',
         'source_assets_models', 'resource_isolation', 'protocol_approval')
FAMILIES = {'physical_worlds_v1', 'physical_worlds_readable_v1', 'physical_absence_worlds_v1'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local(root, name):
    if not isinstance(name, str) or not name or Path(name).is_absolute() or '..' in Path(name).parts:
        raise ValueError('workspace-relative path required')
    path = root / name
    if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
        raise ValueError('regular contained input required: ' + name)
    return path


def pinned(root, reference):
    path = local(root, reference['path'])
    if sha(path) != reference['sha256']:
        raise ValueError('pinned input checksum mismatch: ' + reference['path'])
    return path


def prepare(manifest_path, approval_path, root=ROOT):
    root = Path(root).resolve()
    raw = Path(manifest_path).read_bytes()
    manifest = json.loads(raw)
    ANALYZE(manifest, [])  # protected/duplicate/identity refusal before asset access
    approval = json.loads(Path(approval_path).read_text())
    if (approval.get('schema_version') != 'research3-physical-execution-approval/v1'
            or approval.get('status') != 'approved_frozen'
            or approval.get('authorization_scope') != 'nonprotected_campaign'
            or approval.get('reviewer_type') != 'human'
            or not isinstance(approval.get('approved_by'), str) or not approval['approved_by'].strip()
            or not approval.get('approved_at_utc')
            or approval.get('manifest_sha256') != hashlib.sha256(raw).hexdigest()):
        raise ValueError('explicit pinned human design/execution approval required')
    design_path = pinned(root, approval['design'])
    design = yaml.safe_load(design_path.read_text())
    inventory = DESIGN(design)
    if design.get('status') != 'frozen' or not inventory['supplied_design_fields_valid_and_complete']:
        raise ValueError('frozen complete consistent design required')
    calibration = pinned(root, approval['calibration'])
    coverage = json.loads(pinned(root, approval['calibration_validation']).read_text())
    if (coverage.get('schema_version') != 'research3-physical-calibration-validation/v1'
            or coverage.get('passed') is not True or coverage.get('frozen') is not True
            or coverage.get('human_review_verified') is not True or coverage.get('protected_labels_used') is not False
            or coverage.get('calibration_sha256') != sha(calibration)):
        raise ValueError('new-world human-reviewed frozen calibration validation required')
    for gate in GATES:
        evidence = json.loads(pinned(root, approval.get('gates', {})[gate]).read_text())
        if evidence.get('passed') is not True:
            raise ValueError('unpassed execution gate: ' + gate)
    files = {}
    for reference in approval.get('files', []):
        if reference['path'] in files:
            raise ValueError('duplicate pinned source/asset')
        files[reference['path']] = pinned(root, reference)
    runner = 'scripts/run_approved_physical_episode.py'
    runtime_runner = 'scripts/run_physical_episode.py'
    required_sources = {runner, runtime_runner, 'src/language_nav/campaign_authorization.py',
                        'scripts/run_physical_campaign.py', 'scripts/export_physical_campaign_outcomes.py',
                        'scripts/audit_physical_interruption.py', 'src/language_nav/systems/variants.py',
                        'src/language_nav/planning/policy.py', 'src/language_nav/live.py',
                        'ros_ws/src/language_nav_runtime/language_nav_runtime/nav2_adapter.py',
                        'ros_ws/src/language_nav_bringup/launch/physical_sim.launch.py'}
    if not required_sources <= files.keys():
        raise ValueError('execution-critical source pins missing')
    campaign_id = approval.get('campaign_id', '')
    if not isinstance(campaign_id, str) or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,45}', campaign_id) is None:
        raise ValueError('safe campaign identity required')
    domain = approval.get('ros_domain_id')
    if type(domain) is not int or not 1 <= domain <= 101:
        raise ValueError('explicit isolated ROS domain required')
    if approval.get('allow_coexistence_trial', False) is not False:
        raise ValueError('campaign executor never bypasses Research 2 idleness')
    jobs, block_seeds = [], {}
    for row in manifest['episodes']:
        base = row['base_instruction_id']
        match = re.fullmatch(r'base-r(\d{3})', base)
        number = int(match[1]) if match else 0
        partition = 'development' if 1 <= number <= 10 else 'validation' if 11 <= number <= 14 else None
        if partition is None or row['partition'] != partition or row['system_id'] not in {'B1', 'B2', 'B4', 'B5', 'B6'}:
            raise ValueError('non-protected world/system membership required')
        seed, timeout = row.get('simulation_seed'), row.get('timeout_s')
        if type(seed) is not int or seed not in design['simulator_seed']['confirmatory_seed_list']:
            raise ValueError('episode seed is not frozen')
        block = (partition, row['paired_block_index'])
        if block_seeds.setdefault(block, seed) != seed:
            raise ValueError('paired systems must use the same simulator seed')
        condition = row.get('condition')
        if (condition not in {c.value for c in CorruptionCondition}
                or row['variant_id'] != base + '-' + condition + '-s0'):
            raise ValueError('scheduled condition/instruction identity mismatch')
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('positive finite episode timeout required')
        family = row.get('world_family')
        if family not in FAMILIES or (row.get('condition') == 'missing_landmark') != (family == 'physical_absence_worlds_v1'):
            raise ValueError('world family/condition mismatch')
        if 'r3geo_' + base.replace('-', '_') not in coverage.get('map_ids', []):
            raise ValueError('calibration validation does not cover scheduled map')
        world = Path('data') / family / base
        assets = {'world.sdf', 'map.pgm', 'map.yaml', 'execution_catalog.json', 'landmark_scene.yaml',
                  'manifest.json', 'verified_ordered_geometry.json'}
        if family == 'physical_absence_worlds_v1':
            assets.add('absence_intervention.json')
        if any(str(world / name) not in files for name in assets):
            raise ValueError('scheduled world asset pins missing')
        scene_path = files[str(world / 'landmark_scene.yaml')]
        base_scene_sha256 = sha(scene_path)
        runtime_scene_sha256 = base_scene_sha256
        profile_sha256 = None
        run_id = campaign_id + '-' + hashlib.sha256(row['episode_id'].encode()).hexdigest()[:24]
        command = [sys.executable, '-u', str(root / runner), '--world', str(root / world),
                   '--campaign-authorization', str(Path(approval_path).resolve()),
                   '--campaign-manifest', str(Path(manifest_path).resolve()),
                   '--campaign-episode-id', row['episode_id'],
                   '--variant-id', row['variant_id'], '--run-id', run_id, '--ros-domain-id', str(domain),
                   '--simulation-seed', str(seed), '--timeout', str(timeout), '--system-id', row['system_id'],
                   '--calibration', str(calibration)]
        # No shell strings or caller-supplied arbitrary argv/environment accepted.
        if row.get('camera_profile') is not None:
            profile = row['camera_profile']
            if profile not in files:
                raise ValueError('camera profile must be pinned')
            profile_sha256 = sha(files[profile])
            palette_source = 'src/language_nav/adapters/landmark_palette.py'
            if palette_source not in files:
                raise ValueError('palette adaptation source must be pinned')
            with TemporaryDirectory(prefix='r3-campaign-scene-') as temporary:
                runtime_scene = Path(temporary) / 'runtime_scene.yaml'
                adapt_scene_palette(scene_path, runtime_scene, files[profile])
                runtime_scene_sha256 = sha(runtime_scene)
            command.extend(['--camera-profile', str(files[profile])])
        if row.get('camera_horizontal_fov') is not None:
            fov = row['camera_horizontal_fov']
            if type(fov) not in (int, float) or not math.isfinite(fov) or not 0 < fov < math.pi:
                raise ValueError('invalid frozen camera FOV')
            command.extend(['--camera-horizontal-fov', str(fov)])
        expected_binding = {'map_id': 'r3geo_' + base.replace('-', '_'),
                            'base_scene_sha256': base_scene_sha256,
                            'runtime_scene_sha256': runtime_scene_sha256,
                            'camera_profile_sha256': profile_sha256,
                            'camera_horizontal_fov': row.get('camera_horizontal_fov')}
        matches = [binding for binding in coverage.get('scene_bindings', [])
                   if isinstance(binding, dict) and all(key in binding and binding[key] == value
                                                       for key, value in expected_binding.items())]
        if not matches:
            raise ValueError('calibration validation does not cover exact runtime scene/profile/FOV binding')
        source_minimum = {runtime_runner, 'src/language_nav/live.py', 'src/language_nav/planning/policy.py',
                          'src/language_nav/systems/variants.py',
                          'ros_ws/src/language_nav_runtime/language_nav_runtime/nav2_adapter.py',
                          'ros_ws/src/language_nav_bringup/launch/physical_sim.launch.py'}
        provider = capture_provider_snapshot()
        def sources_match(binding):
            sources = binding.get('source_sha256')
            return (isinstance(sources, dict) and source_minimum <= sources.keys()
                    and provider.get('complete') is True
                    and binding.get('provider_source_snapshot') == provider
                    and all(name in files and sha(files[name]) == digest for name, digest in sources.items()))
        if not any(sources_match(binding) for binding in matches):
            raise ValueError('reviewed runtime source binding missing or changed')
        jobs.append({'episode_id': row['episode_id'], 'run_id': run_id,
                     'run_directory': str(root / 'reports/physical_live_episodes' / run_id), 'argv': command})
    return manifest, jobs


class Lifecycle:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.sequence = 0

    def append(self, state, episode_id, **details):
        row = {'schema_version': 'research3-scheduled-lifecycle/v1', 'sequence': self.sequence,
               'state': state, 'episode_id': episode_id, **details}
        with (self.directory / f'{self.sequence:06d}-{state}.json').open('x') as stream:
            json.dump(row, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write('\n')
        self.sequence += 1


def execute(manifest_path, approval_path, lifecycle_directory, *, root=ROOT, launch=None, resource_guard=None):
    manifest, jobs = prepare(manifest_path, approval_path, root)
    authority = {'manifest_sha256': sha(Path(manifest_path)), 'approval_sha256': sha(Path(approval_path))}
    if resource_guard is None:
        from language_nav.live_resources import require_research2_idle, coexistence_headroom
        def resource_guard():
            require_research2_idle()
            coexistence_headroom()  # Also require bounded host pressure/RAM even when R2 is idle.
    if launch is None:
        launch = lambda command: subprocess.run(command, cwd=root, check=False).returncode
    lifecycle = Lifecycle(lifecycle_directory)
    scheduled_rows = {row['episode_id']: row for row in manifest['episodes']}
    for job in jobs:
        lifecycle.append('planned', job['episode_id'], assignment=job,
                         scheduled_row=scheduled_rows[job['episode_id']], authority=authority)
    for job in jobs:
        # A concurrent source/approval change or newly started R2 job stops this
        # campaign before the next run; the owned runner also guards during motion.
        try:
            if authority != {'manifest_sha256': sha(Path(manifest_path)), 'approval_sha256': sha(Path(approval_path))}:
                raise ValueError('frozen manifest/approval changed')
            _, checked = prepare(manifest_path, approval_path, root)
            if checked != jobs:
                raise ValueError('prepared schedule changed')
            resource_guard()
            if Path(job['run_directory']).exists():
                raise FileExistsError('run identity already exists; no retry/replacement')
        except (OSError, ValueError, RuntimeError, KeyError) as exc:
            lifecycle.append('blocked_before_start', job['episode_id'], reason=str(exc))
            return False
        lifecycle.append('start', job['episode_id'], run_id=job['run_id'])
        try:
            code = launch(job['argv'])
        except BaseException as exc:
            lifecycle.append('unknown', job['episode_id'], reason=str(exc),
                             execution_or_dispatch_not_inferred=True)
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            return False
        report = EXPORT(manifest, [{'episode_id': job['episode_id'], 'run_directory': job['run_directory']}])
        if not report['standalone_outcome_list_exportable']:
            lifecycle.append('unknown', job['episode_id'], returncode=code, export_report=report)
            return False
        outcome = report['outcomes'][0]
        if outcome['dispatched']:
            lifecycle.append('dispatch', job['episode_id'], established_after_run=True,
                             definition=report['dispatch_definition'])
        state = 'setupfailure' if not outcome['dispatched'] else 'outcome'
        lifecycle.append(state, job['episode_id'], returncode=code, outcome=outcome, sources=report['sources'])
        if outcome['infrastructure_failure'] or code != 0:
            return False  # retain all planned rows, never silently replace failed attempts
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--approval', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--lifecycle-directory', type=Path)
    args = parser.parse_args()
    if args.execute:
        if args.lifecycle_directory is None:
            parser.error('--execute requires a new --lifecycle-directory')
        raise SystemExit(0 if execute(args.manifest, args.approval, args.lifecycle_directory) else 1)
    _, jobs = prepare(args.manifest, args.approval)
    print(json.dumps({'status': 'validated_plan_only_no_launch', 'jobs': jobs}, indent=2))


if __name__ == '__main__':
    main()
