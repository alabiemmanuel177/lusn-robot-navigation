#!/usr/bin/env python3
"""Retain exact pre-capture source bytes locally; no environment/model closure."""
import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R1 = Path('/home/eao/risk-calibrated-nav')
SPEC = importlib.util.spec_from_file_location('capture_snapshot_package', Path(__file__).with_name('package_physical_engineering.py'))
PACKAGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKAGE)
BRIDGE_FILES = ('__init__.py', 'core.py', 'node.py')
TRANSFORM_FILES = ('live_risk_node.py', 'projection.py')


def capture(snapshot, *, root=ROOT, provider_root=R1):
    from language_nav.camera_configuration import capture_source_snapshot, PROVIDER_SOURCE_FILES
    root, provider_root = Path(root).resolve(), Path(provider_root).resolve()
    if snapshot.get('schema_version') != 'research3-capture-source-snapshot/v1':
        raise ValueError('explicit current capture source snapshot required')
    sources = snapshot.get('source_sha256', {})
    provider = snapshot.get('provider_source_snapshot', {})
    external = provider.get('files', {})
    if (sources != capture_source_snapshot(root) or set(external) != set(PROVIDER_SOURCE_FILES)
            or provider.get('complete') is not True
            or set(provider.get('source_build_match', {})) != set(BRIDGE_FILES)
            or any(value is not True for value in provider['source_build_match'].values())
            or set(provider.get('transform_source_build_match', {})) != set(TRANSFORM_FILES)
            or any(value is not True for value in provider['transform_source_build_match'].values())):
        raise ValueError('complete fixed source/provider allowlist and matching active bridge required')
    files, origins, reads = {}, {}, []
    def retain(member, path, expected):
        raw = path.read_bytes()
        if PACKAGE.digest(raw) != expected:
            raise ValueError('source changed since capture plan pin: ' + member)
        files[member] = raw
        origins[member] = {'path': str(path), 'resolved_path': str(path.resolve())}
        reads.append((path, expected))
    for name, expected in sorted(sources.items()):
        path = PACKAGE.safe_path(root, name)
        retain('research3/' + name, path, expected)
    for name, expected in sorted(external.items()):
        # Fixed list, never a provider-tree traversal or arbitrary manifest path.
        path = PACKAGE.safe_path(provider_root, name)
        retain('external_provider/' + name, path, expected)
    bridge = root/'ros_ws/build/research3_landmark_bridge/research3_landmark_bridge'
    active = provider.get('active_build_files', {})
    if set(active) != set(BRIDGE_FILES):
        raise ValueError('all three explicitly pinned active bridge files required')
    for name in BRIDGE_FILES:
        path = bridge/name
        record = active[name]
        if Path(record.get('path', '')) != path or record.get('resolved_path') != str(path.resolve()):
            raise ValueError('active bridge source location differs from capture pin')
        expected_source = provider_root/'extensions/research3_landmark_bridge/research3_landmark_bridge'/name
        if path.resolve() not in (path, expected_source.resolve()):
            raise ValueError('active bridge resolves outside its explicit source/build locations')
        if record['sha256'] != external[str(expected_source.relative_to(provider_root))]:
            raise ValueError('active bridge bytes differ from pinned source')
        retain('external_provider/active_build/' + name, path, record['sha256'])
    transforms = provider.get('active_transform_files', {})
    if set(transforms) != set(TRANSFORM_FILES):
        raise ValueError('both explicitly pinned active transform files required')
    for name in TRANSFORM_FILES:
        path = provider_root/'build/semantic_perception/semantic_perception'/name
        expected_source = provider_root/'src/semantic_perception/semantic_perception'/name
        record = transforms[name]
        if (Path(record.get('path', '')) != path or record.get('resolved_path') != str(path.resolve())
                or path.resolve() not in (path, expected_source.resolve())
                or record['sha256'] != external[str(expected_source.relative_to(provider_root))]):
            raise ValueError('active transform location/bytes differ from explicit source/build pins')
        retain('external_provider/active_transforms/' + name, path, record['sha256'])
    if any(PACKAGE.digest(path.read_bytes()) != expected for path, expected in reads):
        raise ValueError('source changed while retaining snapshot')
    manifest = {'schema_version': 'research3-capture-source-archive/v1',
        'capture_source_snapshot': snapshot, 'origins': origins,
        'protected_data_included': False, 'human_labels_included': False,
        'external_environment_closure_complete': False, 'study_complete': False,
        'distribution_authorized': False, 'scope': 'local pre-capture source/config bytes only',
        'limitations': ['No model weights, secrets, process environment, ROS/Gazebo binary closure or Research 2 source is collected.',
                       'External provider files are an explicit named local subset, not permission to distribute them.',
                       'Only runs whose recorded source pins match this snapshot can claim this source-byte reconstruction.'],
        'files': {name: {'sha256': PACKAGE.digest(raw), 'bytes': len(raw)} for name, raw in sorted(files.items())}}
    return files, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot-json', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or Path(str(args.output)+'.sha256').exists():
        raise FileExistsError('capture source archive and checksum are create-once')
    raw = args.snapshot_json.read_bytes()
    files, manifest = capture(json.loads(raw))
    manifest['source_snapshot_input_sha256'] = PACKAGE.digest(raw)
    checksum = PACKAGE.write_bundle(args.output, files, manifest)
    print(json.dumps({'sha256': checksum, 'members': len(files),
                      'uncompressed_bytes': sum(map(len, files.values())), 'study_complete': False}))


if __name__ == '__main__':
    main()
