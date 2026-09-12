#!/usr/bin/env python3
"""Exact nonprotected catalogue differential; not runtime equivalence approval."""
import argparse
import ast
from dataclasses import asdict, is_dataclass
from enum import Enum
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tarfile
from tempfile import TemporaryDirectory
import types

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'src/language_nav/benchmark/physical_catalog.py'
FAMILIES = ('physical_worlds_v1', 'physical_worlds_readable_v1', 'physical_absence_worlds_v1')
ASSETS = ('execution_catalog.json', 'world.sdf', 'map.pgm', 'map.yaml', 'landmark_scene.yaml')
CALLBACK_SOURCES = ('ros_ws/src/language_nav_runtime/language_nav_runtime/nav2_adapter.py',
                    'ros_ws/src/language_nav_planner/language_nav_planner/node.py',
                    'ros_ws/src/language_nav_runtime/language_nav_runtime/semantic_routes.py')
ORDINARY_LAUNCH = 'ros_ws/src/language_nav_bringup/launch/live_adapters.launch.py'
BASELINE_ENV = 'reports/engineering_environment_20260911_v2.json'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def file_sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def archived_source(path, expected_hash, member_name=SOURCE):
    if member_name not in (SOURCE, *CALLBACK_SOURCES, ORDINARY_LAUNCH, BASELINE_ENV):
        raise ValueError('source/member not explicitly allowlisted')
    if file_sha(path) != expected_hash:
        raise ValueError('baseline archive checksum mismatch')
    with tarfile.open(path, 'r:gz') as archive:
        entries = archive.getmembers()
        if len({entry.name for entry in entries}) != len(entries):
            raise ValueError('duplicate archive members')
        def read(name):
            member = archive.getmember(name)
            if not member.isfile() or not 0 <= member.size <= 16 * 1024 * 1024:
                raise ValueError('nonregular or oversized selected member')
            return archive.extractfile(member).read()
        manifest_raw = read('MANIFEST.json')
        manifest = json.loads(manifest_raw)
        if (manifest.get('schema_version') != 'research3-nonprotected-engineering-bundle/v1'
                or manifest.get('protected_data_included') is not False):
            raise ValueError('nonprotected baseline manifest required')
        source = read(member_name)
        pin = manifest['files'][member_name]
        if sha(source) != pin['sha256'] or len(source) != pin['bytes']:
            raise ValueError('archived source checksum mismatch')
        return source, manifest, sha(manifest_raw)


def method_bodies(raw):
    methods = {}
    for node in ast.walk(ast.parse(raw)):
        if isinstance(node, ast.ClassDef):
            for method in node.body:
                if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    key = node.name + '.' + method.name
                    methods[key] = ast.dump(ast.Module(body=method.body, type_ignores=[]), include_attributes=False)
    return methods


def callback_comparison(before, after):
    old, new = method_bodies(before), method_bodies(after)
    common = old.keys() & new.keys()
    return {'unchanged_nonconstructor_method_bodies': sorted(name for name in common
                if not name.endswith('.__init__') and old[name] == new[name]),
            'changed_nonconstructor_method_bodies': sorted(name for name in common
                if not name.endswith('.__init__') and old[name] != new[name]),
            'changed_constructor_bodies': sorted(name for name in common
                if name.endswith('.__init__') and old[name] != new[name]),
            'added_methods': sorted(new.keys() - old.keys()), 'removed_methods': sorted(old.keys() - new.keys())}


def supplement(archive, archive_sha256, root=ROOT):
    root = Path(root).resolve()
    comparisons, checked = [], {}
    for source in CALLBACK_SOURCES:
        old, _, _ = archived_source(archive, archive_sha256, source)
        new = (root / source).read_bytes()
        checked[source] = sha(new)
        comparisons.append({'path': source, 'baseline_sha256': sha(old), 'current_sha256': sha(new),
                            **callback_comparison(old, new)})
    old_launch, _, _ = archived_source(archive, archive_sha256, ORDINARY_LAUNCH)
    launch_sha = file_sha(root / ORDINARY_LAUNCH)
    checked[ORDINARY_LAUNCH] = launch_sha
    env_raw, _, _ = archived_source(archive, archive_sha256, BASELINE_ENV)
    env = json.loads(env_raw)
    providers = []
    for name in ('core.py', 'node.py'):
        relative = 'extensions/research3_landmark_bridge/research3_landmark_bridge/' + name
        key = 'R1:' + relative
        path = root.parent / 'risk-calibrated-nav' / relative
        current_hash = file_sha(path)
        baseline_hash = env['source_files'][key]['sha256']
        providers.append({'source': key, 'baseline_recorded_sha256': baseline_hash,
                          'current_sha256': current_hash, 'bytes_match_recorded_hash': baseline_hash == current_hash})
    if any(file_sha(root / name) != expected for name, expected in checked.items()):
        raise ValueError('sources changed during supplemental comparison')
    if file_sha(archive) != archive_sha256:
        raise ValueError('archive changed during supplemental comparison')
    return {'schema_version': 'research3-nonprotected-source-supplement/v1',
            'archive_sha256': archive_sha256, 'callback_ast_comparisons': comparisons,
            'ordinary_launch': {'path': ORDINARY_LAUNCH, 'baseline_sha256': sha(old_launch),
                'current_sha256': launch_sha, 'bytes_equal': launch_sha == sha(old_launch)},
            'baseline_provider_environment_member': BASELINE_ENV,
            'baseline_provider_environment_sha256': sha(env_raw), 'provider_source_checks': providers,
            'equivalence_approved': False, 'deployment_eligible': False, 'protected_data_used': False,
            'limits': ['AST comparison covers method bodies, ignoring positions; not decorators/signatures/imports or shared state.',
                      'Changed constructors need separate empty-authorization/default-branch tests.',
                      'Unchanged method bodies can behave differently when constructor state or dependencies change.',
                      'Provider hashes establish unchanged source bytes versus recorded metadata, not a detection replay.',
                      'No ROS callbacks, real protected input or calibration transfer executed/approved.']}


def isolated_module(name, source):
    """Execute only caller-verified own source, never untrusted archive code."""
    module = types.ModuleType(name)
    module.__file__ = '<verified-' + name + '>'
    sys.modules[name] = module  # dataclasses resolves its defining module here.
    try:
        exec(compile(source, module.__file__, 'exec'), module.__dict__)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def canonical(value):
    def encode(item):
        if is_dataclass(item):
            return asdict(item)
        if isinstance(item, Enum):
            return item.value
        raise TypeError('unexpected catalogue result type: ' + type(item).__name__)
    return json.dumps(value, default=encode, sort_keys=True, separators=(',', ':'), allow_nan=False)


def default_refusals(baseline, current):
    cases = []
    with TemporaryDirectory(prefix='r3-synthetic-refusal-') as directory:
        path = Path(directory) / 'synthetic_catalog.json'
        for partition in ('test', 'held_out', 'development'):
            payload = {'schema_version': 'research3-physical-route-catalog/v1',
                       'map_id': 'r3geo_base_r015', 'partition': partition,
                       'map_sha256': '0' * 64, 'world_sha256': '0' * 64,
                       'start': {'x': 0, 'y': 0, 'yaw': 0}, 'routes': []}
            path.write_text(json.dumps(payload))
            outcomes = []
            for module in (baseline, current):
                try:
                    module.load_physical_runtime_catalog(path)
                    outcomes.append('unexpected_acceptance')
                except Exception as exc:
                    outcomes.append(type(exc).__name__)
            cases.append({'synthetic_partition': partition, 'map_id': payload['map_id'],
                          'baseline': outcomes[0], 'current': outcomes[1],
                          'both_refuse_before_asset_access': outcomes == ['PermissionError', 'PermissionError']})
    return cases


def check(archive, archive_sha256, root=ROOT):
    root = Path(root).resolve()
    old_source, manifest, manifest_hash = archived_source(archive, archive_sha256)
    new_source = (root / SOURCE).read_bytes()
    old = isolated_module('r3_verified_baseline_catalog', old_source)
    new = isolated_module('r3_current_differential_catalog', new_source)
    rows = []
    try:
        for family in FAMILIES:
            for number in range(1, 15):
                relative = Path('data') / family / f'base-r{number:03d}'
                folder = root / relative
                assets = (*ASSETS, 'absence_intervention.json') if family == FAMILIES[2] else ASSETS
                pins = {}
                for name in assets:
                    path = folder / name
                    if path.is_symlink() or not path.resolve().is_relative_to(root):
                        raise ValueError('nonprotected input path escapes workspace')
                    key = str(relative / name)
                    pins[key] = file_sha(path)
                    if pins[key] != manifest['files'][key]['sha256']:
                        raise ValueError('world input differs from verified baseline: ' + key)
                observations = []
                for module in (old, new):
                    runtime = module.load_physical_runtime_catalog(folder / 'execution_catalog.json')
                    launch = module.validate_physical_launch_inputs(folder / 'execution_catalog.json',
                                                                    folder / 'landmark_scene.yaml')
                    observations.append(canonical({'catalogue': runtime, 'launch': launch,
                        'absent_anchor': module.validated_absent_anchor(folder, runtime)}))
                rows.append({'world': str(relative), 'input_sha256': pins,
                             'baseline_output_sha256': sha(observations[0].encode()),
                             'current_output_sha256': sha(observations[1].encode()),
                             'outputs_equal': observations[0] == observations[1]})
        refusals = default_refusals(old, new)
    finally:
        sys.modules.pop(old.__name__, None)
        sys.modules.pop(new.__name__, None)
    if file_sha(archive) != archive_sha256 or (root / SOURCE).read_bytes() != new_source:
        raise ValueError('source/archive changed during differential')
    if any(file_sha(root / name) != expected for row in rows for name, expected in row['input_sha256'].items()):
        raise ValueError('world inputs changed during differential')
    passed = all(row['outputs_equal'] for row in rows) and all(row['both_refuse_before_asset_access'] for row in refusals)
    return {'schema_version': 'research3-nonprotected-catalog-differential/v1',
            'archive_sha256': archive_sha256, 'archive_manifest_sha256': manifest_hash,
            'baseline_source_sha256': sha(old_source), 'current_source_sha256': sha(new_source),
            'world_count': len(rows), 'rows': rows, 'synthetic_default_refusals': refusals,
            'catalogue_differential_passed': passed, 'equivalence_approved': False,
            'deployment_eligible': False, 'protected_data_used': False, 'human_labels_generated': False,
            'limits': ['Only catalogue, launch-input validation and absent-anchor outputs compared.',
                      'Both isolated source modules use the current shared Python dependencies.',
                      'No ROS callbacks, Gazebo trajectories, provider detections or fresh environment checks executed.',
                      'Source equality/differential tests do not authorize calibration or heldout-world transfer.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--archive-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--supplement-only', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('create-once differential output already exists')
    result = (supplement(args.archive, args.archive_sha256) if args.supplement_only
              else check(args.archive, args.archive_sha256))
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    raise SystemExit(0 if args.supplement_only or result['catalogue_differential_passed'] else 2)


if __name__ == '__main__':
    main()
