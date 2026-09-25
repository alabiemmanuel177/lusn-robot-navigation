"""All fresh pilot emissions, render-only QA, no machine identity declarations."""
import json
from pathlib import Path
import numpy as np
from class_aware_acquisition_pilot import ROOT, OUTPUT, rows, check_pins
from finalize_class_aware_pilot import check_request, require
from run_stage1_feasibility import sha, write
from resume_stage1_two_workers import audit_capture
from expansion_rendered_checks import decode_frame
from join_physical_review_capture import join_capture
import prepare_consolidated_review as consolidated
import portable_physical_review as portable


def render_checks(run):
    joined = join_capture(run)
    tasks = [json.loads(line) for line in (run / 'landmark_review_tasks.jsonl').read_text().splitlines() if line.strip()]
    checks, attestations = [], []
    for task, row in zip(tasks, joined['observations'], strict=True):
        reasons = list(row['reasons'])
        if row['status'] != 'awaiting_individual_visual_qa':
            reasons.append('exact_frame_join_not_ready')
        if not reasons:
            rgb, _ = decode_frame(run / row['frame'])
            height, width = rgb.shape[:2]
            u, v = task['pixel']['u'], task['pixel']['v']
            if not (np.isfinite(u) and np.isfinite(v) and 0 <= u < width and 0 <= v < height):
                reasons.append('pixel_outside_frame')
            if rgb.std() <= 8:
                reasons.append('degenerate_render')
        checks.append(dict(run_id=joined['run_id'], observation_id=task['observation_id'], passed=not reasons, reasons=reasons))
        if not reasons:
            attestations.append(dict(schema_version='research3-render-integrity-qa/v1',
                run_id=joined['run_id'], observation_id=task['observation_id'],
                task_sha256=consolidated.task_digest(task), frame_sha256=row['frame_sha256'],
                request_sha256=joined['request_sha256'], provider_tasks_sha256=joined['provider_tasks_sha256'],
                attested_by='Codex automated render integrity checks; no identity verdict',
                inspection_note='Exact checksum-verified full frame; finite in-frame reported pixel; nondegenerate render. Human judges adequacy and correctness.',
                full_frame_visible=True, pixel_inside_frame=True, frame_integrity_verified=True,
                context_sufficient=None, identity_decidable=None, human_reviewability_established=False,
                correct=None, human_labels_generated=False))
    return checks, attestations


def main():
    schedule = rows()
    audit = json.loads((OUTPUT / 'final/audit.json').read_bytes())
    require(audit['integrity_passed'] and audit['automatic_feasibility_passed'], 'complete pilot confidence screen required')
    joint = json.loads((OUTPUT / 'necessary_joint_feasibility.json').read_bytes())
    require(joint['audit_sha256'] == sha(OUTPUT / 'final/audit.json') and joint['bulk_human_label_request_admitted'],
            'necessary pose screen blocks a futile bulk human labeling request')
    require(audit['plan_sha256'] == sha(OUTPUT / 'plan.json') and len(audit['rows']) == 96, 'complete exact audit')
    records = {r['candidate_id']: r for r in audit['rows']}
    require(set(records) == {r['candidate_id'] for r in schedule}, 'no omitted or duplicated assignments')
    packet = OUTPUT / 'review_packet'
    packet.mkdir(exist_ok=False)
    checks, qa, targets, accounting = [], [], [], []
    for row in schedule:
        name = row['candidate_id']
        run = ROOT / 'reports/physical_live_episodes' / name
        record = records[name]
        require(sha(run / 'request.json') == record['request_sha256'], 'unchanged request')
        require(sha(OUTPUT / (name + '.result.json')) == record['result_sha256'], 'unchanged result')
        check_request(json.loads((run / 'request.json').read_bytes()), row)
        accounting.append(dict(candidate_id=name, category=row['category'], status=record['status'], human_verdict=None))
        if record['status'] == 'infrastructure_failure':
            continue
        capture = audit_capture(run)
        require(capture['status'] == record['status'], 'retained capture agrees')
        if record['status'] != 'emitted':
            continue
        obs = capture['selected_observation']
        require(obs['entity_id'] == row['entity_id'] and obs['category'] == row['category'], 'assigned emission')
        target_checks, target_qa = render_checks(run)
        checks.extend(target_checks)
        qa.extend(target_qa)
        targets.append(dict(run_id=name, entity_id=row['entity_id'], frame='perception_capture/frame-000.json'))
    policy = dict(schema_version='research3-review-sampling-policy/v1', policy_id='class-aware-design-all-emissions-v1',
                  selection_basis='prespecified_capture_views_not_confidence_or_correctness', targets=targets)
    inventory = consolidated.consolidate([str(ROOT / 'reports/physical_live_episodes' / t['run_id']) for t in targets], qa,
        required_maps=sorted({r['map_id'] for r in schedule}), sampling_policy=policy)
    write(packet / 'inventory.json', inventory)
    write(packet / 'sampling_policy.json', policy)
    with (packet / 'combined_visual_qa.jsonl').open('x') as stream:
        for row in qa:
            stream.write(json.dumps(row, sort_keys=True) + '\n')
    write(packet / 'machine_visual_qa_report.json', dict(rows=checks, human_reviewability_established=False,
        human_labels_generated=False, correctness_judged=False))
    write(packet / 'attempt_accounting.json', dict(rows=accounting, scheduled=96, emitted_targets=len(targets),
        dataset_role='design_feasibility', calibration_eligible=False, nondetections_are_negative_labels=False))
    write(packet / 'pilot_audit.json', audit)
    # Do not hide unready emissions behind a shortened reviewer panel.
    require(not inventory['selected_missing'] and inventory['selected_ready_items'] == len(targets), 'all emissions must be present and render-ready')
    check_pins()
    kit = packet / 'research3_class_aware_design_review_kit_v1.zip'
    manifest = portable.build_kit(ROOT, kit, packet_directory=packet, partition='development', design_plan=OUTPUT / 'plan.json')
    print(json.dumps(dict(kit=str(kit), sha256=sha(kit), targets=manifest['targets'], calibration_eligible=False)))


if __name__ == '__main__':
    main()
