#!/usr/bin/env python3
"""Build one partition's primary expansion review kit from a completed collection report.

Steps, all hash-bound and create-once: verify the collection report and every
attempt's evidence; run automated per-observation image checks; write the
prespecified sampling policy that selects exactly the assigned entity's
emission for each attempt that emitted one; consolidate the inventory; and
package the portable reviewer kit. Non-selected emissions stay retained but are
not review targets. Nondetections, ambiguous emissions and infrastructure
failures are listed in the accounting file, never turned into labels.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from run_expansion_collection import load_plan, REPORT_SCHEMA, RUNS, sha_file, write_once  # noqa: E402
from expansion_machine_visual_qa import check_run  # noqa: E402
import prepare_consolidated_review as consolidated  # noqa: E402
import portable_physical_review as portable  # noqa: E402


def evidence_integrity(run, attempt):
    """Reasons the retained evidence of an attempt no longer verifies; empty when intact."""
    problems = []
    request = run / 'request.json'
    if not request.exists() or sha_file(request) != attempt['request_sha256']:
        problems.append('request_missing_or_changed')
    if attempt['status'] == 'emitted':
        for name in ('perception_capture/summary.json', 'perception_capture/frame-000.json',
                     'perception_capture/observation_index.json', 'landmark_review_tasks.jsonl', 'expansion_attempt.json'):
            path = run / name
            if not path.exists() or path.stat().st_size == 0:
                problems.append('empty_or_missing:' + name)
        try:
            frame = json.loads((run / 'perception_capture/frame-000.json').read_bytes())
            for kind in ('rgb', 'depth'):
                raw = (run / 'perception_capture' / frame[kind]['file']).read_bytes()
                if sha_file(run / 'perception_capture' / frame[kind]['file']) != frame[kind]['sha256'] or len(raw) != frame[kind]['bytes']:
                    problems.append('image_checksum_mismatch:' + kind)
        except (OSError, ValueError, KeyError):
            problems.append('frame_record_unreadable')
        if attempt.get('attempt_sha256') and (run / 'expansion_attempt.json').exists() \
                and sha_file(run / 'expansion_attempt.json') != attempt['attempt_sha256']:
            problems.append('attempt_record_changed')
    return sorted(set(problems))


def build(report_path, output, *, partition):
    report = json.loads(Path(report_path).read_bytes())
    plan, plan_sha, _ = load_plan()
    if (report.get('schema_version') != REPORT_SCHEMA or report.get('partition') != partition
            or report.get('plan_sha256') != plan_sha or report.get('complete') is not True):
        raise PermissionError('complete accepted-plan collection report required for this partition')
    rows = {row['candidate_id']: row for row in plan['rows'] if row['partition'] == partition}
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    qa_rows, checks, targets, accounting = [], [], [], []
    for attempt in report['attempts']:
        run = RUNS / attempt['run_id']
        row = rows[attempt['candidate_id']]
        integrity = evidence_integrity(run, attempt)
        accounting.append(dict(candidate_id=attempt['candidate_id'], run_id=attempt['run_id'], status=attempt['status'],
                               map_id=row['map_id'], category=row['category'], entity_id=row['entity_id'],
                               view_group=row['view_group'], seed=row['seed'], selected_entity=attempt['selected_entity'],
                               evidence_integrity=integrity,
                               review_target=attempt['status'] == 'emitted' and not integrity))
        if integrity:
            # The attempt happened and its ledger record stands, but its retained
            # bytes no longer verify; it cannot be reviewed and is not re-run.
            continue
        if attempt['status'] != 'emitted':
            continue
        if attempt['selected_entity'] != row['entity_id']:
            raise ValueError('selected emission is not the prespecified entity: ' + attempt['run_id'])
        results, attested = check_run(run)
        checks.extend(results)
        qa_rows.extend(attested)
        targets.append(dict(run_id=attempt['run_id'], entity_id=row['entity_id'], frame='perception_capture/frame-000.json'))
    if not targets:
        raise ValueError('no emitted attempts to review')
    policy = dict(schema_version='research3-review-sampling-policy/v1',
                  policy_id=f'expansion-{partition}-assigned-entity-emissions-v1',
                  selection_basis='prespecified_capture_views_not_confidence_or_correctness', targets=targets)
    maps = sorted({row['map_id'] for row in rows.values()})
    inventory = consolidated.consolidate([str(RUNS / t['run_id']) for t in targets], qa_rows, required_maps=maps,
                                         required_classes=list(consolidated.DEFAULT_CLASSES), sampling_policy=policy)
    with (output / 'combined_visual_qa.jsonl').open('x') as stream:
        for row in qa_rows:
            stream.write(json.dumps(row, sort_keys=True) + '\n')
    inventory['qa_input_sha256'] = sha_file(output / 'combined_visual_qa.jsonl')
    write_once(output / 'inventory.json', inventory)
    write_once(output / 'sampling_policy.json', policy)
    write_once(output / 'machine_visual_qa_report.json', dict(
        schema_version='research3-expansion-machine-visual-qa-report/v1', observations=len(checks),
        passed=sum(r['passed'] for r in checks), failed=[r for r in checks if not r['passed']], rows=checks,
        human_labels_generated=False, correctness_judged=False))
    write_once(output / 'attempt_accounting.json', dict(
        schema_version='research3-expansion-attempt-accounting/v1', partition=partition, plan_sha256=plan_sha,
        collection_report_sha256=sha_file(report_path), scheduled=report['scheduled'], accounted=report['accounted'],
        status_counts=report['status_counts'], review_targets=len(targets),
        evidence_unrecoverable=[dict(candidate_id=a['candidate_id'], run_id=a['run_id'], ledger_status=a['status'],
                                     reasons=a['evidence_integrity']) for a in accounting if a['evidence_integrity']],
        selected_ready=inventory.get('selected_ready_items'), selected_missing=inventory.get('selected_missing'),
        rows=accounting, human_labels_generated=False,
        note='nondetections, ambiguous emissions and infrastructure failures are retained here and are not calibration rows'))
    kit = output / f'research3_expansion_{partition}_review_kit.zip'
    manifest = portable.build_kit(ROOT, kit, packet_directory=output, partition=partition)
    return dict(packet=str(output), kit=str(kit), kit_sha256=sha_file(kit), review_targets=len(targets),
                ready_items=inventory['ready_items'], selected_missing=inventory.get('selected_missing_items'),
                inventory_status=inventory['status'], kit_manifest=manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--partition', choices=('development', 'validation'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.report, args.output, partition=args.partition)
    print(json.dumps({k: v for k, v in result.items() if k != 'kit_manifest'}))


if __name__ == '__main__':
    main()
