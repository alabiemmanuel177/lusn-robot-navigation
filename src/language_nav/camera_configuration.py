"""Validate a pre-validation engineering camera freeze, never confidence calibration."""
import hashlib
import json
import math
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAPTURE_SOURCE_PATHS = (
    'scripts/run_physical_episode.py', 'scripts/run_live_episode.py', 'scripts/physical_perception_capture.py',
    'scripts/run_stationary_capture_plan.py', 'src/language_nav/live.py',
    'src/language_nav/evaluation/ordered.py', 'src/language_nav/benchmark/physical_catalog.py',
    'src/language_nav/systems/variants.py', 'src/language_nav/planning/policy.py',
    'src/language_nav/grounding/routes.py', 'src/language_nav/live_resources.py',
    'src/language_nav/capture_view.py', 'src/language_nav/camera_configuration.py',
    'src/language_nav/adapters/landmark_palette.py',
    'ros_ws/src/language_nav_bringup/launch/live_adapters.launch.py',
    'ros_ws/src/language_nav_bringup/launch/physical_sim.launch.py',
    'ros_ws/src/language_nav_runtime/language_nav_runtime/nav2_adapter.py',
    'ros_ws/src/language_nav_runtime/language_nav_runtime/semantic_routes.py',
    'ros_ws/src/language_nav_runtime/language_nav_runtime/monitor_bridge.py',
    'ros_ws/src/language_interface/language_interface/node.py',
    'ros_ws/src/semantic_belief_map/semantic_belief_map/node.py',
    'ros_ws/src/language_nav_bringup/language_nav_bringup/landmark_bridge_runner.py',
    'ros_ws/src/language_nav_planner/language_nav_planner/node.py')
BRIDGE_SOURCE_FILES = tuple('extensions/research3_landmark_bridge/research3_landmark_bridge/' + name
                            for name in ('__init__.py', 'core.py', 'node.py'))
PROVIDER_SOURCE_FILES = (*BRIDGE_SOURCE_FILES,
    'src/semantic_perception/semantic_perception/live_risk_node.py',
    'src/semantic_perception/semantic_perception/projection.py',
    'src/experiment_controller/experiment_controller/run_episode.py',
    'src/experiment_controller/experiment_controller/preflight.py',
    'src/episode_logger/episode_logger/monitor.py',
    'rcn/collisions.py', 'rcn/perception_metrics.py', 'rcn/metrics.py', 'rcn/schema.py', 'rcn/shifts.py',
    'configs/nav2/nav2_common.yaml', 'configs/systems/s0.yaml', 'configs/sim/physics.yaml')


def capture_source_snapshot(root=ROOT):
    root = Path(root).resolve()
    names = set(CAPTURE_SOURCE_PATHS)
    # Pin the bounded owned core Python tree and interface definitions too;
    # this is code, not a data/results sweep or a full environment closure.
    for directory, suffix in (('src/language_nav', '*.py'), ('ros_ws/src/language_nav_interfaces/msg', '*.msg')):
        names.update(str(path.relative_to(root)) for path in (root / directory).rglob(suffix)
                     if '__pycache__' not in path.parts)
    result = {}
    for name in sorted(names):
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('capture source must be a contained regular file')
        result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def capture_provider_snapshot(r1_root=None, build_root=None):
    r1_root = Path(r1_root) if r1_root is not None else ROOT.parent / 'risk-calibrated-nav'
    provider_root = r1_root / 'extensions/research3_landmark_bridge/research3_landmark_bridge'
    build_root = Path(build_root) if build_root is not None else ROOT / 'ros_ws/build/research3_landmark_bridge/research3_landmark_bridge'
    def record(path):
        return {'path': str(path), 'resolved_path': str(path.resolve()),
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None}
    sources = {Path(name).name: record(provider_root / Path(name).name) for name in BRIDGE_SOURCE_FILES}
    installed = {name: record(build_root / name) for name in sources}
    matches = {name: sources[name]['sha256'] is not None and sources[name]['sha256'] == installed[name]['sha256']
               for name in sources}
    files = {name: record(r1_root / name)['sha256'] for name in PROVIDER_SOURCE_FILES}
    transforms = {name: record(r1_root / 'build/semantic_perception/semantic_perception' / name)
                  for name in ('live_risk_node.py', 'projection.py')}
    transform_matches = {name: transforms[name]['sha256'] is not None and transforms[name]['sha256'] ==
                         files['src/semantic_perception/semantic_perception/' + name] for name in transforms}
    return {'schema_version': 'research3-capture-provider-source/v1',
            'files': files,
            'source_files': sources, 'active_build_files': installed,
            'source_build_match': matches, 'active_transform_files': transforms,
            'transform_source_build_match': transform_matches,
            'complete': all(matches.values()) and all(transform_matches.values()) and all(files.values()),
            'scope': 'explicit provider source/build bytes only; not full ROS/R1/R2/environment closure'}


def validate_capture_source_freeze(path, *, check_import_resolution=False):
    raw = Path(path).read_bytes()
    payload = json.loads(raw)
    if (payload.get('schema_version') != 'research3-capture-source-snapshot/v1'
            or payload.get('protected_data_used') is not False
            or payload.get('human_labels_generated') is not False):
        raise ValueError('invalid capture source snapshot scope')
    if payload.get('source_sha256') != capture_source_snapshot():
        raise ValueError('capture source snapshot changed')
    provider = capture_provider_snapshot()
    if provider.get('complete') is not True or payload.get('provider_source_snapshot') != provider:
        raise ValueError('capture provider source/build snapshot changed or incomplete')
    if check_import_resolution:
        expected = {'research3_landmark_bridge.' + Path(name).stem: value
                    for name, value in provider['active_build_files'].items() if name != '__init__.py'}
        expected.update({'semantic_perception.' + Path(name).stem: value
                         for name, value in provider['active_transform_files'].items()})
        for module, record in expected.items():
            spec = importlib.util.find_spec(module)
            if spec is None or spec.origin is None or Path(spec.origin).resolve() != Path(record['resolved_path']):
                raise ValueError('active provider import resolution differs from source freeze: ' + module)
    return hashlib.sha256(raw).hexdigest()


def validate_camera_freeze(path, *, map_id, profile, horizontal_fov):
    allowed = {f'r3geo_base_r{i:03d}' for i in range(1, 15)}
    if map_id not in allowed:
        raise ValueError('camera freeze requires non-protected map identity before reading inputs')
    path, profile = Path(path), Path(profile)
    payload = json.loads(path.read_text())
    if (payload.get('schema_version') not in {'research3-engineering-camera-freeze/v1', 'research3-engineering-camera-freeze/v2'}
            or payload.get('protected_data_used') is not False
            or payload.get('confidence_calibration_frozen') is not False
            or payload.get('human_labels_generated') is not False):
        raise ValueError('invalid engineering camera freeze scope')
    if map_id not in allowed or set(payload.get('profiles', {})) != allowed:
        raise ValueError('camera freeze requires exact non-protected map scope')
    if (not isinstance(horizontal_fov, (int, float)) or not math.isfinite(horizontal_fov)
            or not .5 <= horizontal_fov <= 2.
            or payload.get('horizontal_fov') != horizontal_fov):
        raise ValueError('camera FOV differs from frozen configuration')
    if hashlib.sha256(profile.read_bytes()).hexdigest() != payload['profiles'][map_id]:
        raise ValueError('camera profile differs from frozen configuration')
    evidence = payload.get('development_evidence', [])
    if not evidence:
        raise ValueError('development camera evidence required before validation')
    for row in evidence:
        directory = Path(row['run_directory'])
        request = json.loads((directory / 'request.json').read_text())
        if (request.get('partition') != 'development'
                or request.get('map_id') not in {f'r3geo_base_r{i:03d}' for i in range(1, 11)}
                or request.get('protected_test_routes_used') is not False):
            raise ValueError('only stable non-protected development evidence may establish camera configuration')
        for name, digest in row['sha256'].items():
            file = (directory / name).resolve()
            if not file.is_relative_to(directory.resolve()):
                raise ValueError('camera evidence path escapes run')
            if hashlib.sha256(file.read_bytes()).hexdigest() != digest:
                raise ValueError('development camera evidence changed')
        if 'request.json' not in row['sha256'] or not any(
                name.endswith('-rgb.bin') for name in row['sha256']):
            raise ValueError('camera evidence must bind request and raw RGB')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_frozen_capture_view(path, *, map_id, category, pose, world):
    if map_id not in {f'r3geo_base_r{i:03}' for i in range(11, 15)}:
        raise ValueError('explicit non-protected validation map required before freeze access')
    payload = json.loads(Path(path).read_text())
    if payload.get('schema_version') != 'research3-engineering-camera-freeze/v2':
        raise ValueError('validation execution requires v2 bound view/source freeze; v1 is historical only')
    if payload.get('source_sha256') != capture_source_snapshot():
        raise ValueError('frozen capture source identity changed')
    views = [row for row in payload.get('validation_views', [])
             if row.get('map_id') == map_id and row.get('category') == category]
    if len(views) != 1 or views[0].get('capture_pose') != pose:
        raise ValueError('validation capture pose/category differs from frozen view')
    expected_world = ROOT / 'data/physical_worlds_readable_v1' / map_id.removeprefix('r3geo_').replace('_', '-')
    if Path(world).resolve() != expected_world.resolve():
        raise ValueError('validation world differs from frozen readable world')
    required = {'world.sdf', 'execution_catalog.json', 'landmark_scene.yaml', 'map.pgm', 'map.yaml'}
    hashes = views[0].get('world_sha256', {})
    if set(hashes) != required:
        raise ValueError('frozen view requires complete world asset pins')
    for name, digest in hashes.items():
        if hashlib.sha256((Path(world) / name).read_bytes()).hexdigest() != digest:
            raise ValueError('frozen validation world changed')
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
