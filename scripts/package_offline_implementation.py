#!/usr/bin/env python3
"""Snapshot R3 code and non-protected worlds, with exact local integrity verification."""
import argparse
import hashlib
import json
from pathlib import Path

from verify_physical_release import verify

ROOT = Path(__file__).resolve().parents[1]


def package(destination, root=ROOT):
    root, destination = Path(root).resolve(), Path(destination).resolve()
    roots = [root / p for p in ('src', 'scripts', 'tests', 'ros_ws/src')]
    for family in ('physical_worlds_v1', 'physical_absence_worlds_v1'):
        roots.extend(root / 'data' / family / f'base-r{i:03}' for i in range(1, 15))
    if any(destination.is_relative_to(path) for path in roots):
        raise ValueError('snapshot must not be inside an input tree')
    files = []
    for directory in roots:
        if not directory.is_dir():
            raise ValueError('missing snapshot input: ' + str(directory))
        for path in sorted(directory.rglob('*')):
            if '__pycache__' in path.parts or any(part.startswith('.') for part in path.relative_to(directory).parts):
                continue
            if path.is_symlink():
                raise ValueError('snapshot refuses symlink inputs')
            if path.is_file() and path.suffix not in {'.pyc', '.pyo'}:
                files.append(path)
    files.extend(root / name for name in (
        'pyproject.toml', 'configs/research_dependencies.yaml',
        'configs/physical_campaign_draft_v1.yaml', 'configs/physical_experiment_design_draft_v2.yaml',
        'docs/CONSOLIDATED_REVIEW_HANDOFF.md', 'docs/OFFLINE_EXPERIMENT_DESIGN.md',
        'docs/OFFLINE_ANALYSIS_RELEASE.md', 'docs/PHYSICAL_PROTOCOL_DRAFT.md',
        'docs/PHYSICAL_DETECTOR_VALIDATION.md', 'docs/OFFLINE_COMPLETION_20260911.md'))
    destination.mkdir(parents=True, exist_ok=False)
    records = []
    for source in sorted(set(files)):
        if source.is_symlink() or not source.resolve().is_relative_to(root):
            raise ValueError('invalid snapshot input')
        raw = source.read_bytes()
        name = str(source.relative_to(root))
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(raw)
        records.append({'path': name, 'sha256': hashlib.sha256(raw).hexdigest()})
    manifest = {'schema_version': 'research3-local-file-manifest/v1', 'files': records,
                'scope': 'offline implementation and 28 non-protected world assets only',
                'scientific_release_complete': False,
                'limitations': ['No final protocol, calibration labels, live comparative evidence or external dependencies bundled.',
                    'Public benchmark input and runtime environment must be supplied separately; not a standalone study release.']}
    manifest_path = destination / 'MANIFEST.json'
    with manifest_path.open('x') as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write('\n')
    result = verify(destination, manifest, manifest_path)
    if not result['integrity_passed']:
        raise ValueError('snapshot integrity verification failed')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(package(args.output), sort_keys=True))


if __name__ == '__main__':
    main()
