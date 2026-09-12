#!/usr/bin/env python3
"""Fit a create-once candidate only from revalidated joint human observations.

This does not approve calibration deployment or fit on protected labels.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

from language_nav.calibration import build_calibration_artifact

SPEC = importlib.util.spec_from_file_location('joint_fit_export', Path(__file__).with_name('export_physical_human_review.py'))
EXPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORT)


def fit(*, inventory, qa, progress, evidence, policy, requirements, export_directory,
        partition, minimum_samples):
    if type(minimum_samples) is not int or minimum_samples < 1:
        raise ValueError('explicit positive minimum sample count required')
    requirements_hash = EXPORT._UI.digest(requirements)
    coverage = EXPORT._UI.load_json(requirements)
    reviewed, samples, readiness = EXPORT.export_payload(inventory, qa, progress, coverage,
                                                        evidence=evidence, policy=policy)
    if readiness['blockers'] or readiness.get('joint_review_contract') is None:
        raise ValueError('joint export remains blocked; no calibration candidate fitted')
    expected = {'reviewed_tasks.jsonl': reviewed, 'calibration_samples.jsonl': samples, 'readiness.json': readiness}
    snapshots = {}
    for name, content in expected.items():
        path = Path(export_directory) / name
        actual = ([json.loads(line) for line in path.read_text().splitlines() if line.strip()]
                  if name.endswith('.jsonl') else EXPORT._UI.load_json(path))
        if actual != content:
            raise ValueError('stale joint export: ' + name)
        snapshots[path] = EXPORT._UI.digest(path)
    raw = (Path(export_directory) / 'calibration_samples.jsonl').read_bytes()
    if [json.loads(line) for line in raw.decode().splitlines() if line.strip()] != samples:
        raise ValueError('joint calibration samples changed during fitting admission')
    artifact = build_calibration_artifact(samples, input_sha256=hashlib.sha256(raw).hexdigest(),
        partition=partition, minimum_samples=minimum_samples)
    artifact.update(joint_review_contract=readiness['joint_review_contract'],
                    deployment_approval_granted_by_this_tool=False,
                    fit_metrics_scope='in_sample_only')
    for path, digest in snapshots.items():
        if EXPORT._UI.digest(path) != digest:
            raise ValueError('joint export changed during candidate fitting')
    if EXPORT._UI.digest(requirements) != requirements_hash:
        raise ValueError('coverage requirements changed during candidate fitting')
    for path, digest in ((inventory, readiness['inventory_sha256']), (qa, readiness['qa_sha256']),
                         (progress, readiness['progress_sha256']),
                         (evidence, readiness['joint_review_contract']['evidence_sha256']),
                         (policy, readiness['joint_review_contract']['policy_sha256'])):
        if EXPORT._UI.digest(path) != digest:
            raise ValueError('joint review input changed during candidate fitting')
    return artifact


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('inventory', 'qa', 'progress', 'evidence', 'policy', 'requirements', 'export-directory', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--partition', choices=('development', 'validation'), required=True)
    parser.add_argument('--minimum-samples', type=int, required=True)
    args = vars(parser.parse_args())
    output = args.pop('output')
    if output.exists():
        raise FileExistsError(output)
    artifact = fit(**args)
    with output.open('x') as stream:
        json.dump(artifact, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
