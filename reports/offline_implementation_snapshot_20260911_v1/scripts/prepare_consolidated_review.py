#!/usr/bin/env python3
"""Create-once non-protected review inventory; QA is never a correctness label."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re

_SPEC = importlib.util.spec_from_file_location(
    'physical_review_join', Path(__file__).with_name('join_physical_review_capture.py'))
_JOIN = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_JOIN)
DEFAULT_MAPS = tuple(f'r3geo_base_r{i:03d}' for i in range(1, 15))
DEFAULT_CLASSES = ('chair', 'doorway', 'office_entrance', 'laboratory_entrance')
QA_CHECKS = ('full_frame_visible', 'context_sufficient',
             'pixel_marker_verified', 'identity_decidable')


def task_digest(task):
    """Canonical per-task binding, separate from the exact source file digest."""
    return hashlib.sha256(json.dumps(task, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def nonprotected_map(map_id):
    match = re.fullmatch(r'r3geo_base_r(\d{3})', map_id or '')
    return bool(match and 1 <= int(match[1]) <= 14)


def consolidate(directories, qa_rows=(), *, required_maps=DEFAULT_MAPS,
                required_classes=DEFAULT_CLASSES):
    required_maps, required_classes = sorted(set(required_maps)), sorted(set(required_classes))
    if not required_maps or not all(nonprotected_map(m) for m in required_maps):
        raise ValueError('required scope must contain only non-protected physical maps')
    if not required_classes or any(not isinstance(c, str) or not c for c in required_classes):
        raise ValueError('nonempty required classes needed')
    qa_rows = list(qa_rows)
    qa_counts = Counter((q.get('run_id'), q.get('observation_id')) for q in qa_rows)
    qa_by_key = {(q.get('run_id'), q.get('observation_id')): q for q in qa_rows}
    used_qa, run_ids, runs, items = set(), set(), [], []
    paths = [Path(path).resolve() for path in directories]
    if len(paths) != len(set(paths)):
        raise ValueError('duplicate run directory')
    for directory in paths:
        request_path = directory / 'request.json'
        if not request_path.is_file():
            runs.append({'directory': str(directory), 'status': 'blocked',
                         'reasons': ['missing_request'], 'items': 0})
            continue
        request = _JOIN.read_json(request_path)
        map_id = request.get('map_id')
        expected_partition = ('development' if nonprotected_map(map_id)
                              and int(map_id[-3:]) <= 10 else 'validation')
        if (not nonprotected_map(map_id) or request.get('partition') != expected_partition
                or request.get('protected_test_routes_used') is not False):
            raise ValueError('protected or unproven non-protected run rejected before capture read')
        run_id = request.get('run_id')
        if not isinstance(run_id, str) or not run_id or run_id in run_ids:
            raise ValueError('missing or duplicate run ID')
        run_ids.add(run_id)
        provenance = {'directory': str(directory), 'run_id': run_id, 'map_id': map_id,
                      'partition': expected_partition, 'request_sha256': _JOIN.digest(request_path),
                      'map_sha256': request.get('asset_sha256', {}).get('map.pgm'),
                      'source_revision': request.get('source_revision'),
                      'source_sha256': request.get('source_sha256'),
                      'runtime_scene_sha256': request.get('runtime_scene_sha256'),
                      'camera_profile_sha256': request.get('camera_profile_sha256')}
        try:
            joined = _JOIN.join_capture(directory)
        except (FileNotFoundError, KeyError, TypeError, json.JSONDecodeError, ValueError) as exc:
            # The independent map gate above has already rejected protected inputs.
            runs.append({**provenance, 'status': 'blocked', 'items': 0,
                         'reasons': ['unusable_capture_input'], 'detail': str(exc)})
            continue
        tasks = [json.loads(line) for line in
                 (directory / 'landmark_review_tasks.jsonl').read_text().splitlines()
                 if line.strip()]
        provenance.update(provider_tasks_sha256=joined['provider_tasks_sha256'],
                          capture_summary_sha256=joined['capture_summary_sha256'])
        source_complete = bool(provenance['map_sha256'] and provenance['source_revision']
                               and provenance['source_sha256'])
        run_items = []
        for task, join_row in zip(tasks, joined['observations'], strict=True):
            identifier = task.get('observation_id')
            key = (run_id, identifier)
            binding = {'run_id': run_id, 'observation_id': identifier,
                       'task_sha256': task_digest(task),
                       'frame_sha256': join_row.get('frame_sha256'),
                       'request_sha256': joined['request_sha256'],
                       'provider_tasks_sha256': joined['provider_tasks_sha256']}
            reasons = list(join_row['reasons'])
            if not source_complete:
                reasons.append('missing_map_or_source_provenance')
            qa = qa_by_key.get(key)
            qa_valid = False
            if qa is None:
                reasons.append('individual_machine_visual_qa_missing')
            else:
                used_qa.add(key)
                if qa_counts[key] != 1:
                    reasons.append('duplicate_visual_qa')
                elif any(qa.get(name) != value for name, value in binding.items()):
                    reasons.append('stale_or_mismatched_visual_qa')
                elif (qa.get('schema_version') != 'research3-machine-visual-qa/v1'
                      or not isinstance(qa.get('attested_by'), str) or not qa['attested_by'].strip()
                      or qa.get('correct') is not None
                      or any(qa.get(name) is not True for name in QA_CHECKS)):
                    reasons.append('invalid_or_failed_visual_qa')
                else:
                    qa_valid = True
            status = ('ready_for_human_review' if not reasons else
                      'awaiting_visual_qa' if reasons == ['individual_machine_visual_qa_missing']
                      else 'rejected')
            row = {**binding, 'map_id': map_id, 'partition': expected_partition,
                   'category': task.get('category'), 'entity_id': task.get('entity_id'),
                   'frame': join_row.get('frame'), 'pixel': task.get('pixel'),
                   'status': status, 'reasons': reasons,
                   'machine_visual_qa_passed': qa_valid,
                   'machine_visual_qa_sha256': task_digest(qa) if qa is not None else None,
                   'correct': None, 'human_reviewer_id': '',
                   'human_review_status': 'pending_human_review'}
            run_items.append(row)
        items.extend(run_items)
        runs.append({**provenance, 'status': 'inventoried', 'items': len(run_items)})
    ready = [item for item in items if item['status'] == 'ready_for_human_review']
    coverage = []
    for map_id in required_maps:
        for category in required_classes:
            selected = [item for item in items
                        if item['map_id'] == map_id and item['category'] == category]
            count = sum(item['status'] == 'ready_for_human_review' for item in selected)
            coverage.append({'map_id': map_id, 'category': category,
                             'retained_items': len(selected), 'ready_items': count,
                             'status': 'represented_unlabelled' if count else 'missing_ready_items',
                             'human_correct': None, 'human_incorrect': None,
                             'recall_coverage': None})
    missing_coverage = any(row['ready_items'] == 0 for row in coverage)
    return {'schema_version': 'research3-consolidated-review-inventory/v1',
            'status': 'blocked' if not ready else 'partial_human_review_handoff'
            if missing_coverage or len(ready) != len(items)
            or any(run['status'] == 'blocked' for run in runs)
            or any(key not in used_qa for key in qa_by_key) else 'ready_for_human_review',
            'runs': runs, 'items': items, 'ready_items': len(ready),
            'rejected_items': sum(item['status'] == 'rejected' for item in items),
            'unmatched_qa': [dict(qa, rejection_reason='no_inventory_item') for qa in qa_rows
                             if (qa.get('run_id'), qa.get('observation_id')) not in used_qa],
            'required_maps': required_maps, 'required_classes': required_classes,
            'coverage': coverage, 'coverage_complete': not missing_coverage,
            'human_labels_generated': False, 'calibration_frozen': False,
            'detector_performance_validated': False, 'protected_data_used': False,
            'study_complete': False,
            'scope': 'QA-attested unlabelled inventory; not accuracy or recall evidence'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, action='append', default=[])
    parser.add_argument('--qa', type=Path)
    parser.add_argument('--required-map', action='append')
    parser.add_argument('--required-class', action='append')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    qa = [json.loads(line) for line in args.qa.read_text().splitlines() if line.strip()] if args.qa else []
    result = consolidate(args.run, qa, required_maps=args.required_map or DEFAULT_MAPS,
                         required_classes=args.required_class or DEFAULT_CLASSES)
    if args.qa:
        result['qa_input_sha256'] = _JOIN.digest(args.qa)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'status': result['status'], 'ready_items': result['ready_items']}))


if __name__ == '__main__':
    main()
