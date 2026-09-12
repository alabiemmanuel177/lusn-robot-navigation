#!/usr/bin/env python3
"""Assemble an unlabelled, create-once packet from explicit nonprotected inputs.

Ordinary sampling is fixed: frame-000 intended chair, laboratory entrance and
its doorway, and office entrance on each of the 14 nonprotected maps. No score,
confidence or correctness field participates in selection. This is engineering
review preparation, not scientific approval of a calibration sampling design.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'packet_consolidation', Path(__file__).with_name('prepare_consolidated_review.py'))
CONSOLIDATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONSOLIDATE)
CATEGORIES = ('chair', 'laboratory_entrance', 'office_entrance')
FRAME = 'perception_capture/frame-000.json'


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def safe_run(run_id):
    if not isinstance(run_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,95}', run_id):
        raise ValueError('invalid run_id')
    return run_id


def gate_directory(directory, run_id, expected_map=None):
    """Only request metadata may be read until nonprotected scope is proven."""
    request_path = directory / 'request.json'
    if not request_path.is_file():
        return {'run_id': run_id, 'status': 'missing_request_no_capture_read'}
    request = json.loads(request_path.read_bytes())
    map_id = request.get('map_id')
    if map_id not in CONSOLIDATE.DEFAULT_MAPS:
        raise ValueError('protected or unknown map rejected before capture access')
    partition = 'development' if int(map_id[-3:]) <= 10 else 'validation'
    if (request.get('partition') != partition
            or request.get('protected_test_routes_used') is not False
            or request.get('run_id') != run_id
            or (expected_map is not None and map_id != expected_map)):
        raise ValueError('request identity or nonprotected partition mismatch')
    return {'run_id': run_id, 'map_id': map_id, 'status': 'nonprotected_request_verified'}


def selection(plan, runs_root, extra=None):
    if (plan.get('schema_version') != 'research3-stationary-capture-plan/v1'
            or plan.get('protected_content_read') is not False
            or plan.get('view_count') != 42 or len(plan.get('views', [])) != 42):
        raise ValueError('requires complete nonprotected 42-view plan')
    expected = {(f'base-r{i:03d}', category) for i in range(1, 15) for category in CATEGORIES}
    seen, run_ids, targets, directories, gates = set(), set(), [], [], []
    runs_root = Path(runs_root).resolve()
    ordinary = []
    for view in plan['views']:
        key = (view.get('base_instruction_id'), view.get('category'))
        if key not in expected or key in seen:
            raise ValueError('duplicate, protected, or unknown plan map/category')
        seen.add(key)
        base, category = key
        number = int(base[-3:])
        if view.get('partition') != ('development' if number <= 10 else 'validation'):
            raise ValueError('plan partition mismatch')
        run_id = safe_run(view.get('run_id'))
        if run_id in run_ids:
            raise ValueError('duplicate run_id')
        run_ids.add(run_id)
        entity = view.get('intended_entity_id')
        if not isinstance(entity, str) or not entity.strip():
            raise ValueError('missing intended entity')
        map_id = f'r3geo_{base.replace("-", "_")}'
        if category != 'chair' and not re.fullmatch(re.escape(map_id) + r'_(left|right)_[12]_entrance', entity):
            raise ValueError('entrance entity/map mismatch')
        entities = [entity]
        if category == 'laboratory_entrance':
            entities.append(entity.removesuffix('_entrance') + '_doorway')
        targets.extend({'run_id': run_id, 'entity_id': item, 'frame': FRAME} for item in entities)
        ordinary.append((run_id, map_id))
    # Entire plan scope is checked before opening even one run request.
    for run_id, map_id in ordinary:
        directory = (runs_root / run_id).resolve()
        if directory.parent != runs_root:
            raise ValueError('run directory escapes runs root')
        directories.append(directory)
        gates.append(gate_directory(directory, run_id, map_id))
    if extra is not None:
        if (set(extra) != {'schema_version', 'selection_basis', 'targets'}
                or extra['schema_version'] != 'research3-review-extra-selection/v1'
                or extra['selection_basis'] != 'explicit_stress_capture_not_confidence_or_correctness'
                or not isinstance(extra['targets'], list)):
            raise ValueError('invalid explicit stress selection')
        for target in extra['targets']:
            if set(target) != {'run_id', 'entity_id', 'frame'}:
                raise ValueError('stress targets must contain only run/entity/frame')
            run_id = safe_run(target['run_id'])
            if run_id not in run_ids:
                directory = (runs_root / run_id).resolve()
                if directory.parent != runs_root:
                    raise ValueError('stress directory escapes runs root')
                gates.append(gate_directory(directory, run_id))
                directories.append(directory)
                run_ids.add(run_id)
            targets.append(dict(target))
    policy = {'schema_version': 'research3-review-sampling-policy/v1',
              'policy_id': 'fixed-ordinary-frame000-four-classes-plus-explicit-stress-v1',
              'selection_basis': 'prespecified_capture_views_not_confidence_or_correctness',
              'targets': targets}
    CONSOLIDATE.validate_sampling_policy(policy)
    return directories, policy, gates


def prepare(plan_path, qa_paths, output, *, runs_root=ROOT / 'reports/physical_live_episodes', extra_path=None):
    output = Path(output)
    if output.exists():
        raise FileExistsError('packet output already exists')
    plan_raw = Path(plan_path).read_bytes()
    extra_raw = Path(extra_path).read_bytes() if extra_path else None
    directories, policy, gates = selection(json.loads(plan_raw), runs_root,
                                           json.loads(extra_raw) if extra_raw else None)
    qa_rows, qa_inputs, seen = [], [], set()
    for path in qa_paths:
        path = Path(path).resolve()
        if path in seen:
            raise ValueError('duplicate QA input path')
        seen.add(path)
        raw = path.read_bytes()
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
        if any(not isinstance(row, dict) for row in rows):
            raise ValueError('QA rows must be objects')
        qa_rows.extend(rows)
        qa_inputs.append({'path': str(path), 'sha256': sha(raw), 'rows': len(rows)})
    combined = b''.join((json.dumps(row, sort_keys=True, allow_nan=False) + '\n').encode() for row in qa_rows)
    inventory = CONSOLIDATE.consolidate(directories, qa_rows, sampling_policy=policy)
    inventory['qa_input_sha256'] = sha(combined)
    payloads = {'sampling_policy.json': encoded(policy), 'combined_visual_qa.jsonl': combined,
                'inventory.json': encoded(inventory)}
    manifest = {'schema_version': 'research3-physical-review-packet/v1',
                'status': inventory['status'], 'plan_sha256': sha(plan_raw),
                'extra_selection_sha256': sha(extra_raw) if extra_raw is not None else None,
                'qa_inputs': qa_inputs, 'run_directories': [str(path) for path in directories],
                'directory_gates': gates, 'ordinary_views': 42, 'ordinary_targets': 56,
                'total_targets': len(policy['targets']),
                'files': {name: sha(raw) for name, raw in payloads.items()},
                'human_labels_generated': False, 'visual_qa_generated': False,
                'calibration_frozen': False, 'scientific_sampling_design_approved': False,
                'protected_data_used': False, 'study_complete': False}
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in {**payloads, 'packet_manifest.json': encoded(manifest)}.items():
        with (output / name).open('xb') as stream:
            stream.write(raw)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--qa', type=Path, action='append', default=[])
    parser.add_argument('--extra-selection', type=Path,
                        help='v1 explicit stress targets run_id/entity_id/frame under runs-root')
    parser.add_argument('--runs-root', type=Path, default=ROOT / 'reports/physical_live_episodes')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.plan, args.qa, args.output, runs_root=args.runs_root,
                     extra_path=args.extra_selection)
    print(json.dumps({'status': result['status'], 'targets': result['total_targets']}))


if __name__ == '__main__':
    main()
