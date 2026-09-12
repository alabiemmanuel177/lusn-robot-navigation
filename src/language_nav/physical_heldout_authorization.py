"""Explicit, default-deny physical held-out admission. No implicit test access.

Approval metadata is read first; protected schedules/assets are opened only after
the frozen non-protected design, calibration and actual source pins pass.
Attestations record human approval, not cryptographic identity authentication.
"""
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import runpy

import yaml

ROOT = Path(__file__).resolve().parents[2]
R1 = Path('/home/eao/risk-calibrated-nav')
SOURCE_FILES = {
    'scripts/run_physical_episode.py', 'scripts/run_authorized_heldout_episode.py',
    'src/language_nav/physical_heldout_authorization.py',
    'src/language_nav/benchmark/physical_catalog.py', 'src/language_nav/live.py',
    'src/language_nav/evaluation/ordered.py', 'src/language_nav/systems/variants.py',
    'src/language_nav/planning/policy.py', 'src/language_nav/grounding/routes.py',
    'src/language_nav/live_resources.py', 'scripts/run_live_episode.py',
    'src/language_nav/campaign_authorization.py',
    'ros_ws/src/language_nav_bringup/launch/physical_sim.launch.py',
    'ros_ws/src/language_nav_bringup/launch/heldout_adapters.launch.py',
    'ros_ws/src/language_nav_bringup/language_nav_bringup/heldout_landmark_bridge.py',
    'ros_ws/src/language_nav_runtime/language_nav_runtime/nav2_adapter.py',
    'ros_ws/src/language_nav_runtime/language_nav_runtime/semantic_routes.py',
    'ros_ws/src/language_nav_planner/language_nav_planner/node.py',
    'ros_ws/src/language_interface/language_interface/node.py',
    'ros_ws/src/semantic_belief_map/semantic_belief_map/node.py',
    'ros_ws/src/language_nav_runtime/language_nav_runtime/monitor_bridge.py',
    'src/language_nav/parsing/__init__.py', 'src/language_nav/parsing/rule_based.py',
    'src/language_nav/belief/__init__.py', 'src/language_nav/belief/store.py',
    'src/language_nav/belief/update.py', 'src/language_nav/adapters/__init__.py',
    'src/language_nav/adapters/ros.py', 'src/language_nav/adapters/nav2.py',
    'src/language_nav/adapters/research1.py', 'src/language_nav/adapters/research2.py',
    'src/language_nav/models.py', 'src/language_nav/contracts.py', 'src/language_nav/safety.py',
}
# Retain the existing metadata field name provider_source_sha256, but its exact
# allowlist includes both Python code and the named runtime YAML configuration.
# This is a bounded direct-dependency inventory, not complete external model,
# ROS binary, environment or dependency closure.
PROVIDER_FILES = {
    'extensions/research3_landmark_bridge/research3_landmark_bridge/node.py',
    'extensions/research3_landmark_bridge/research3_landmark_bridge/core.py',
    'src/semantic_perception/semantic_perception/live_risk_node.py',
    'src/semantic_perception/semantic_perception/projection.py',
    'src/experiment_controller/experiment_controller/run_episode.py',
    'src/experiment_controller/experiment_controller/preflight.py',
    'src/episode_logger/episode_logger/monitor.py',
    'rcn/collisions.py', 'rcn/perception_metrics.py',
    'rcn/metrics.py', 'rcn/schema.py', 'rcn/shifts.py',
    'configs/nav2/nav2_common.yaml', 'configs/systems/s0.yaml', 'configs/sim/physics.yaml',
}
ASSETS = {'world.sdf', 'map.pgm', 'map.yaml', 'execution_catalog.json',
          'landmark_scene.yaml', 'manifest.json', 'verified_ordered_geometry.json'}
EVALUATOR_ASSETS = {'manifest.json', 'verified_ordered_geometry.json'}
GATES = {'nonprotected_detector_validation_complete', 'calibration_frozen',
         'scientific_protocol_frozen', 'heldout_launch_authorized',
         'nonprotected_runtime_regression_passed', 'research2_idle_required'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def contained(root, name):
    if not isinstance(name, str) or Path(name).is_absolute() or '..' in Path(name).parts:
        raise PermissionError('contained relative authorized path required')
    path = Path(root) / name
    if any(p.is_symlink() for p in (path, *path.parents) if p.is_relative_to(root)):
        raise PermissionError('symlink authorized paths are forbidden')
    if not path.resolve().is_relative_to(Path(root).resolve()):
        raise PermissionError('authorized path escapes root')
    return path


def pinned(root, ref):
    path = contained(root, ref['path'])
    if not re.fullmatch('[0-9a-f]{64}', str(ref.get('sha256', ''))) or sha(path) != ref['sha256']:
        raise PermissionError('authorized checksum mismatch: ' + str(path))
    return path


@dataclass(frozen=True)
class HeldoutAuthorization:
    path: Path
    digest: str
    episode_id: str
    root: Path
    approval: dict
    episode: dict

    def binding(self):
        return {'path': str(self.path), 'sha256': self.digest,
                'episode_id': self.episode_id, 'runtime_partition': 'test',
                'human_identity_authenticated': False}

    def asset(self, path, *, evaluator=False):
        world = contained(self.root, self.episode['world_directory'])
        path = Path(path).resolve()
        if path.parent != world.resolve() or path.name not in self.episode['asset_sha256']:
            raise PermissionError('asset outside explicitly authorized episode')
        if path.name in EVALUATOR_ASSETS and not evaluator:
            raise PermissionError('evaluator assets are unavailable during policy execution')
        return pinned(self.root, {'path': str(path.relative_to(self.root)),
                                  'sha256': self.episode['asset_sha256'][path.name]})


def authorize(path, digest, episode_id, *, root=ROOT, provider_root=R1):
    root, path = Path(root).resolve(), Path(path).resolve()
    raw = path.read_bytes()  # Only explicitly supplied non-protected approval metadata.
    if hashlib.sha256(raw).hexdigest() != digest:
        raise PermissionError('held-out authorization hash mismatch')
    approval = json.loads(raw)
    if (approval.get('schema_version') != 'research3-physical-heldout-runtime-authorization/v1'
            or approval.get('status') != 'approved_frozen'
            or approval.get('authorization_scope') != 'physical_heldout_live_execution'
            or approval.get('reviewer_type') != 'human'
            or not approval.get('approved_by') or not approval.get('approved_at_utc')
            or any(approval.get('gates', {}).get(gate) is not True for gate in GATES)):
        raise PermissionError('explicit frozen human held-out runtime approval required')
    design_path = pinned(root, approval['design'])
    design = yaml.safe_load(design_path.read_text())
    check = runpy.run_path(str(ROOT / 'scripts/check_physical_design_readiness.py'))['check'](design)
    if design.get('status') != 'frozen' or not check['supplied_design_fields_valid_and_complete']:
        raise PermissionError('complete frozen scientific design required')
    calibration = json.loads(pinned(root, approval['calibration']).read_text())
    if (calibration.get('schema_version') != 'landmark-calibration/v1'
            or calibration.get('partition') not in {'development', 'validation'}):
        raise PermissionError('only frozen non-protected calibration is admissible')
    sources = approval.get('execution_source_sha256', {})
    if not SOURCE_FILES <= sources.keys():
        raise PermissionError('complete held-out source pins required')
    for name, digest_value in sources.items():
        if not name.startswith(('src/', 'scripts/', 'ros_ws/src/')) or not name.endswith('.py'):
            raise PermissionError('only execution source pins are permitted')
        # Actual checkout, not shadow source copies from staging.
        pinned(ROOT, {'path': name, 'sha256': digest_value})
    provider_sources = approval.get('provider_source_sha256', {})
    if set(provider_sources) != PROVIDER_FILES:
        raise PermissionError('unchanged provider callback, control, measurement and configuration pins required')
    for name, value in provider_sources.items():
        pinned(provider_root, {'path': name, 'sha256': value})
    schedule = json.loads(pinned(root, approval['schedule']).read_text())
    if (schedule.get('schema_version') != 'research3-physical-heldout-schedule/v1'
            or schedule.get('evidence_scope') != 'physical_world_heldout'
            or schedule.get('design_sha256') != sha(design_path)
            or schedule.get('calibration_sha256') != approval['calibration']['sha256']):
        raise PermissionError('held-out schedule must bind approved design and calibration')
    rows = schedule.get('episodes', [])
    ids = [row.get('episode_id') for row in rows]
    if not ids or len(set(ids)) != len(ids) or any(not isinstance(i, str) or not i for i in ids):
        raise PermissionError('unique scheduled episode identities required')
    matches = [row for row in rows if row['episode_id'] == episode_id]
    if len(matches) != 1:
        raise PermissionError('episode is not explicitly authorized')
    row = matches[0]
    if (row.get('partition') != 'held_out' or row.get('runtime_partition') != 'test'
            or not re.fullmatch(r'r3geo_base_r0(?:1[5-9]|20)', str(row.get('map_id', '')))
            or row.get('system_id') not in {'B1', 'B2', 'B4', 'B5', 'B6'}
            or type(row.get('simulation_seed')) is not int
            or row['simulation_seed'] not in design['simulator_seed']['confirmatory_seed_list']
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,95}', str(row.get('run_id', '')))):
        raise PermissionError('invalid held-out runtime episode identity')
    if (type(row.get('timeout_s')) not in (int, float) or not math.isfinite(row['timeout_s'])
            or row['timeout_s'] <= 0 or type(approval.get('ros_domain_id')) is not int
            or not 1 <= approval['ros_domain_id'] <= 101):
        raise PermissionError('positive bounded timeout and isolated domain required')
    if (type(row.get('camera_horizontal_fov')) not in (int, float)
            or not .5 <= row['camera_horizontal_fov'] <= 2.
            or type(row.get('camera_color_tolerance')) not in (int, float)
            or not math.isfinite(row['camera_color_tolerance']) or row['camera_color_tolerance'] <= 0):
        raise PermissionError('explicit finite approved camera settings required')
    if any(row.get(key) for key in ('camera_profile', 'capture_only', 'capture_review', 'capture_perception',
                                     'capture_context', 'allow_coexistence_trial')):
        raise PermissionError('held-out runtime accepts final scenes only; capture/adaptation is forbidden')
    base = 'base-r' + row['map_id'][-3:]
    from language_nav.benchmark import CorruptionCondition
    if (row.get('variant_id') not in {base + '-' + c.value + '-s0' for c in CorruptionCondition}
            or row.get('instruction', {}).get('variant_id') != row['variant_id']
            or row['instruction'].get('base_instruction_id') != base
            or not isinstance(row['instruction'].get('raw_text'), str) or not row['instruction']['raw_text'].strip()
            or not isinstance(row['instruction'].get('provenance'), str)
            or set(row['instruction']) != {'variant_id', 'base_instruction_id', 'raw_text', 'provenance'}):
        raise PermissionError('deployable instruction identity/text required; evaluator fields forbidden')
    assets = row.get('asset_sha256', {})
    if not ASSETS <= assets.keys() or not set(assets) <= ASSETS | {'absence_intervention.json'}:
        raise PermissionError('complete exact held-out asset pins required')
    if any(not re.fullmatch('[0-9a-f]{64}', str(value)) for value in assets.values()):
        raise PermissionError('invalid held-out asset hash')
    contained(root, row['world_directory'])  # No asset open yet.
    return HeldoutAuthorization(path, digest, episode_id, root, approval, row)


@dataclass(frozen=True)
class HeldoutEvaluationContext:
    """Internal capability minted AFTER independent live or audit authorization.

    This is not a CLI permission. Caller must finish its respective authorization
    gate first, and supply an immutable measured record before evaluator access.
    """
    run_id: str
    map_id: str
    asset_sha256: dict
    sealed_measurements: Path
    sealed_measurements_sha256: str
    authorization_sha256: str

    def validate(self, request, evidence):
        if (request.get('run_id') != self.run_id or request.get('map_id') != self.map_id
                or request.get('asset_sha256') != self.asset_sha256
                or not re.fullmatch('[0-9a-f]{64}', self.authorization_sha256)
                or sha(self.sealed_measurements) != self.sealed_measurements_sha256):
            raise PermissionError('held-out evaluation needs authorized immutable measurements')
        sealed = json.loads(Path(self.sealed_measurements).read_text())
        if (sealed != evidence or sealed.get('schema_version') != 'research3-live-measurements/v2'
                or sealed.get('run_id') != self.run_id):
            raise PermissionError('evaluator trajectory differs from sealed measured record')


def node_authorization(node):
    """Empty parameters preserve the ordinary dev/validation behavior."""
    values = {}
    for key in ('heldout_authorization', 'heldout_authorization_sha256', 'heldout_episode_id'):
        node.declare_parameter(key, '')
        values[key] = str(node.get_parameter(key).value)
    if not any(values.values()):
        return None
    if not all(values.values()):
        raise PermissionError('complete held-out authorization parameters required')
    authorization = authorize(values['heldout_authorization'], values['heldout_authorization_sha256'],
                              values['heldout_episode_id'])
    validate_runtime_isolation(authorization)
    return authorization


def validate_runtime_isolation(authorization):
    if os.environ.get('ROS_DOMAIN_ID') != str(authorization.approval['ros_domain_id']):
        raise PermissionError('actual ROS domain differs from authorized isolated domain')
    worker = 'research3-' + authorization.episode['run_id']
    if any(os.environ.get(name) != worker for name in ('RCN_WORKER_ID', 'GZ_PARTITION', 'IGN_PARTITION')):
        raise PermissionError('actual transport worker differs from authorized isolated episode')
