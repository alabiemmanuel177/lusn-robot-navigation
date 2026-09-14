#!/usr/bin/env python3
"""Export existing human decisions; never infer labels or fit calibration."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import importlib.util
import json
import math
from pathlib import Path
import re

_SPEC = importlib.util.spec_from_file_location('physical_review_ui',
    Path(__file__).with_name('serve_physical_review.py'))
_UI = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_UI)
EVENT_KEYS = {'item_index', 'run_id', 'observation_id', 'task_sha256', 'frame_sha256',
              'reviewer_id', 'verdict', 'notes', 'correct', 'review_status', 'recorded_at'}
JOINT_EVENT_KEYS = EVENT_KEYS | {'dimension_verdicts', 'evidence_sha256', 'policy_sha256', 'item_evidence_sha256'}
JOINT_TARGET = 'category_and_stable_entity_association_and_pose_under_approved_rubric'
NONHUMAN = re.compile(r'(^|[^a-z])(synthetic|test|fixture|agent|bot|automated|automatic|codex|gpt|machine|ai)([^a-z]|$)', re.I)


def validate_requirements(requirements):
    if requirements is None:
        return
    version = requirements.get('schema_version')
    if version not in ('research3-physical-calibration-coverage/v1',
                       'research3-physical-calibration-coverage/v2'):
        raise ValueError('unsupported coverage requirements schema')
    keys = ('minimum_per_map_class_outcome', 'minimum_per_class_confidence_bin')
    if version.endswith('/v2'):
        if requirements.get('outcome_coverage_scope') not in ('global_class', 'map_class'):
            raise ValueError('explicit global_class or map_class outcome scope required')
        if requirements.get('unreviewable_exclusion_policy') not in ('allow_with_counts', 'block'):
            raise ValueError('explicit unreviewable exclusion policy required')
        keys = ('minimum_per_map_class_total', 'minimum_per_class_outcome',
                'minimum_per_class_confidence_bin')
    for key in keys:
        if type(requirements.get(key)) is not int or requirements[key] < 1:
            raise ValueError('coverage minima must be positive integers')
    edges = requirements.get('confidence_bin_edges', [])
    if (len(edges) < 2 or edges[0] != 0 or edges[-1] != 1
            or any(type(x) not in (float, int) or not math.isfinite(x) for x in edges)
            or any(a >= b for a, b in zip(edges, edges[1:]))):
        raise ValueError('confidence bins must strictly partition [0,1]')


def coverage_blockers(coverage, exclusions, requirements):
    """Apply a prespecified policy to counts; never choose or relax its values."""
    if requirements is None:
        return (['pending_or_unreviewable_items_retained'] if exclusions else []) + [
            'prespecified_coverage_and_confidence_requirements_missing']
    validate_requirements(requirements)
    if requirements['schema_version'].endswith('/v1'):
        blockers = ['pending_or_unreviewable_items_retained'] if exclusions else []
        minimum = requirements['minimum_per_map_class_outcome']
        if any(row['correct'] < minimum or row['incorrect'] < minimum for row in coverage):
            blockers.append('map_class_binary_outcome_coverage_incomplete')
        return blockers
    blockers = []
    if any(row['reason'] == 'pending_human_review' for row in exclusions):
        blockers.append('pending_human_review')
    if (requirements['unreviewable_exclusion_policy'] == 'block'
            and any(row['reason'] == 'human_unreviewable' for row in exclusions)):
        blockers.append('unreviewable_exclusions_blocked_by_protocol')
    if any(row['correct'] + row['incorrect'] < requirements['minimum_per_map_class_total']
           for row in coverage):
        blockers.append('map_class_total_coverage_incomplete')
    outcome_rows = coverage
    if requirements['outcome_coverage_scope'] == 'global_class':
        grouped = {}
        for row in coverage:
            group = grouped.setdefault(row['category'], {'correct': 0, 'incorrect': 0})
            for key in ('correct', 'incorrect'):
                group[key] += row[key]
        outcome_rows = list(grouped.values())
    minimum = requirements['minimum_per_class_outcome']
    if any(row['correct'] < minimum or row['incorrect'] < minimum for row in outcome_rows):
        blockers.append(requirements['outcome_coverage_scope'] + '_binary_outcome_coverage_incomplete')
    return blockers


def export_payload(inventory, qa, progress, requirements=None, *, evidence=None, policy=None):
    # resume is explicitly read-only and checks the immutable header; no new
    # progress file is created, even if no human has started reviewing.
    store = _UI.ReviewStore(inventory, qa, progress, resume=True, evidence=evidence, policy=policy)
    progress_hash = _UI.digest(progress)
    joint_rows, joint_policy, policy_approved = store.validate_joint() if evidence else ([], {}, False)
    joint = evidence is not None
    validate_requirements(requirements)
    events = store.events()[1:]
    latest, seen, event_times = {}, set(), set()
    previous_time = None
    for event in events:
        if not isinstance(event, dict) or set(event) != (JOINT_EVENT_KEYS if joint else EVENT_KEYS):
            raise ValueError('unexpected audit fields: no inferred or machine labels accepted')
        index = event['item_index']
        if type(index) is not int or not 0 <= index < len(store.items):
            raise ValueError('audit references unknown item')
        item = store.items[index]
        if any(event[key] != item[key] for key in
               ('run_id', 'observation_id', 'task_sha256', 'frame_sha256')):
            raise ValueError('stale or conflicting audit binding')
        reviewer, verdict = event['reviewer_id'], event['verdict']
        if (not isinstance(reviewer, str) or not reviewer.strip() or len(reviewer) > 100
                or NONHUMAN.search(reviewer)):
            raise ValueError('missing or explicitly non-human reviewer provenance')
        if verdict not in ('correct', 'incorrect', 'unreviewable'):
            raise ValueError('invalid human verdict')
        expected_correct = {'correct': True, 'incorrect': False, 'unreviewable': None}[verdict]
        if event['correct'] is not expected_correct:
            raise ValueError('verdict and correctness conflict')
        expected_status = 'human_unreviewable' if verdict == 'unreviewable' else 'human_verified'
        if event['review_status'] != expected_status:
            raise ValueError('human review status conflicts with verdict')
        if not isinstance(event['notes'], str) or len(event['notes']) > 2000:
            raise ValueError('invalid human review notes')
        timestamp = datetime.fromisoformat(event['recorded_at'])
        if timestamp.tzinfo is None or (previous_time is not None and timestamp < previous_time):
            raise ValueError('audit timestamps must be timezone-aware and ordered')
        previous_time = timestamp
        if joint:
            reference = joint_rows[index]
            if (event['evidence_sha256'] != store.evidence_hash or event['policy_sha256'] != store.policy_hash
                    or event['item_evidence_sha256'] != _UI._JOINT.object_hash(reference)
                    or any(reference[key] != item[key] for key in ('run_id', 'observation_id', 'task_sha256', 'frame_sha256'))):
                raise ValueError('stale joint dimension evidence/rubric binding')
            if _UI.joint_verdict(event['dimension_verdicts']) != verdict:
                raise ValueError('aggregate verdict conflicts with explicit dimension verdicts')
            if verdict != 'unreviewable':
                if not policy_approved or not reference['evidence_complete']:
                    raise ValueError('joint binary label requires approved rubric and complete evidence')
                approved_at = datetime.fromisoformat(joint_policy['approved_at'])
                if approved_at.tzinfo is None or approved_at > timestamp:
                    raise ValueError('joint rubric must be approved before each human verdict')
        fingerprint = _UI._INVENTORY.task_digest(event)
        if fingerprint in seen or (index, timestamp) in event_times:
            raise ValueError('duplicate or conflicting audit event')
        seen.add(fingerprint)
        event_times.add((index, timestamp))
        latest[index] = event
    reviewed, samples, exclusions, provenance = [], [], [], []
    ids = set()
    for index, item in enumerate(store.items):
        event = latest.get(index)
        if event is None or event['verdict'] == 'unreviewable':
            exclusions.append({'run_id': item['run_id'], 'observation_id': item['observation_id'],
                               'reason': 'pending_human_review' if event is None else 'human_unreviewable',
                               'correct': None})
            continue
        if not joint:
            exclusions.append({'run_id': item['run_id'], 'observation_id': item['observation_id'],
                               'reason': 'legacy_category_only_not_joint_review', 'correct': None})
            continue
        run = store.runs[item['run_id']]
        rows = [json.loads(line) for line in
                (run / 'landmark_review_tasks.jsonl').read_text().splitlines() if line.strip()]
        original = next(row for row in rows if row['observation_id'] == item['observation_id'])
        # Provider normalization scopes review targets by run and observation ID.
        # Run-scoped IDs distinguish multi-view/seed captures without inventing IDs.
        target_key = (item['run_id'], original['observation_id'])
        if target_key in ids:
            raise ValueError('provider export requires globally unique observation IDs')
        ids.add(target_key)
        row = {**original, 'review_status': 'human_verified',
               'reviewer_id': event['reviewer_id'], 'correct': int(event['correct'])}
        reviewed.append(row)
        provenance.append({key: event[key] for key in ('run_id', 'observation_id', 'dimension_verdicts',
            'evidence_sha256', 'policy_sha256', 'item_evidence_sha256', 'recorded_at', 'reviewer_id')})
        samples.append({'schema_version': 'landmark-calibration-sample/v1',
                        'observation_id': row['observation_id'], 'partition': row['partition'],
                        'category': row['category'], 'probability': float(row['probability']),
                        'correct': row['correct']})
    inventory_data = _UI.load_json(inventory)
    coverage, confidence = [], []
    for map_id in inventory_data['required_maps']:
        for category in inventory_data['required_classes']:
            counts = Counter(int(latest[i]['correct']) for i, item in enumerate(store.items)
                             if item['map_id'] == map_id and item['category'] == category
                             and joint and i in latest and latest[i]['correct'] is not None)
            coverage.append({'map_id': map_id, 'category': category,
                             'correct': counts[1], 'incorrect': counts[0]})
    blockers = []
    if not joint:
        blockers.append('joint_observation_review_required')
    elif not policy_approved:
        blockers.append('joint_review_rubric_not_approved')
    if not reviewed:
        blockers.append('no_accepted_human_binary_labels')
    blockers.extend(coverage_blockers(coverage, exclusions, requirements))
    if requirements is not None:
        edges = requirements['confidence_bin_edges']
        for category in inventory_data['required_classes']:
            for low, high in zip(edges, edges[1:]):
                count = sum(row['category'] == category and low <= row['probability']
                            and (row['probability'] < high or high == 1)
                            for row in reviewed)
                confidence.append({'category': category, 'low': low, 'high': high, 'count': count})
        if any(row['count'] < requirements['minimum_per_class_confidence_bin'] for row in confidence):
            blockers.append('class_confidence_coverage_incomplete')
    if _UI.digest(progress) != progress_hash:
        raise ValueError('progress changed during export; retry after review saves finish')
    if joint:
        store.validate_joint()
    store.validate()
    report = {'schema_version': 'research3-physical-human-export/v2',
              'status': 'blocked' if blockers else 'ready_for_calibration_protocol_review',
              'blockers': blockers, 'provider_review_rows': len(reviewed),
              'excluded': exclusions, 'excluded_counts': dict(Counter(row['reason'] for row in exclusions)),
              'audit_events_retained': len(events), 'superseded_events': len(events) - len(latest),
              'map_class_outcomes': coverage, 'class_confidence_coverage': confidence,
              'requirements': requirements,
              'requirements_sha256': _UI._INVENTORY.task_digest(requirements) if requirements else None,
              'inventory_sha256': _UI.digest(inventory), 'qa_sha256': _UI.digest(qa),
              'progress_sha256': progress_hash, 'labels_generated': False,
              'calibration_fitted': False, 'calibration_frozen': False, 'protected_data_used': False,
              'human_identity_authenticated': False,
              'limit': 'Rejects explicit synthetic provenance; a typed name does not independently prove human identity.'}
    report['joint_review_contract'] = ({'schema_version': 'research3-joint-calibration-label-contract/v1',
        'target': JOINT_TARGET, 'dimensions': list(_UI.DIMENSIONS),
        'evidence_sha256': store.evidence_hash, 'policy_sha256': store.policy_hash,
        'audit_schema_version': 'research3-physical-human-review-audit/v2',
        'accepted_label_bindings': provenance} if joint else None)
    return reviewed, samples, report


def write_export(directory, reviewed, samples, report):
    directory = Path(directory)
    payloads = {'reviewed_tasks.jsonl': ''.join(json.dumps(row, sort_keys=True, allow_nan=False) + '\n'
                                              for row in reviewed),
                'calibration_samples.jsonl': ''.join(json.dumps(row, sort_keys=True, allow_nan=False) + '\n'
                                                   for row in samples),
                'readiness.json': json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + '\n'}
    directory.mkdir(exist_ok=False)
    for filename, payload in payloads.items():
        with (directory / filename).open('x') as stream:
            stream.write(payload)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('inventory', 'qa', 'progress', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--requirements', type=Path)
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--policy', type=Path)
    args = parser.parse_args()
    requirements = _UI.load_json(args.requirements) if args.requirements else None
    rows, samples, report = export_payload(args.inventory, args.qa, args.progress, requirements,
                                          evidence=args.evidence, policy=args.policy)
    write_export(args.output, rows, samples, report)
    print(json.dumps({'status': report['status'], 'exported': len(rows)}))


if __name__ == '__main__':
    main()
