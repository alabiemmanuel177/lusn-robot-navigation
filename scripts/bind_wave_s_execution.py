"""Bind explicit prospective user authority only after source-bound preflight.

This receipt records delegation already given in the conversation. It is not a
signature or a claim that the human inspected subsequently generated evidence.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from prepare_joint_score_protocol import ROOT, sha
from joint_score_collection import write_once
from joint_score_components import digest
from joint_score_wave_s_driver import verify_inputs
from fit_joint_score_wave_s import validate_execution, protocol_acceptance


def read(path):
    return json.loads(Path(path).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inspect_transport(root, config_path):
    audit = read(root/'capture_audit.json')
    require(audit['transport_passed'] is True and audit['primary_eligible'] is False,
            'four-view engineering transport must pass')
    require(audit['config_sha256'] == sha(config_path), 'preflight config binding')
    require(len(audit['rows']) == 4, 'exactly four fixed preflight views')
    checked = []
    for i, category in enumerate(('chair', 'doorway', 'laboratory_entrance', 'office_entrance')):
        folder = root/f'view-{i:02}'
        summary, execution, frame, plan = [read(folder/n) for n in
            ('summary.json', 'execution.json', 'frame-000.json', 'plan.json')]
        require(summary == audit['rows'][i] and summary['status'] == 'captured' and
                summary['attempt_id'] == 'preflight-'+category, 'closed capture identity')
        require(execution['failure'] is None and execution['owned_launches_exited'] is True and
                len(execution['owned_launch_pids']) == 2 and execution['motion_dispatched'] is False and
                execution['source_checked_after_capture'] is True and
                execution['cleanup']['forced_kill_count'] == 0, 'clean stationary lifecycle required')
        require(plan['preflight_only'] is True and plan['primary_eligible'] is False and
                plan['seed'] == 29 and plan['partition'] == 'development', 'engineering scope only')
        for path, expected in plan['input_sha256'].items():
            require(sha(path) == expected, 'changed captured source: '+path)
        events = [read(p) for p in sorted(folder.glob('event-*.json'))]
        def event(kind):
            matches = [e for e in events if e['kind'] == kind]
            require(len(matches) == 1, 'unique event: '+kind)
            return matches[0]
        arm, selected, closed = event('arm'), event('select'), event('close')
        ready = event('localization_ready')
        stamp = frame['rgb_stamp_ns']
        require(ready['no_spawn_contact'] is True and ready['amcl_converged'] is True,
                'localization/contact readiness')
        require(stamp == frame['depth_stamp_ns'] == selected['stamp_ns'] and stamp > arm['arm_stamp_ns'],
                'exact synchronized post-arm pair required')
        require(closed['monotonic']-selected['monotonic'] >= 2. and
                closed['monotonic'] < summary['deadline_monotonic'], 'fixed TF delay and deadline')
        tf = frame['camera_to_map']
        require(tf['header']['stamp']['sec']*10**9+tf['header']['stamp']['nanosec'] == stamp and
                tf['header']['frame_id'] == 'map' and tf['child_frame_id'] == frame['rgb']['frame_id'],
                'exact-time measured TF required')
        for channel in ('rgb', 'depth'):
            require(sha(folder/frame[channel]['file']) == frame[channel]['sha256'], 'image integrity')
        checked.append(dict(category=category, stamp_ns=stamp,
                            capture_wall_seconds=closed['monotonic']-summary['launch_monotonic']))
    return checked


def bind(config_path, capture_root, inference_root, output):
    config = read(config_path); verify_inputs(config)
    auth_path = ROOT/'reports/joint_score_wave_s_authorization_20260924.json'
    auth = read(auth_path)
    require(auth['agent_may_bind_exact_manifest_after_preflight'] is True and
            auth['failed_preflight_may_be_bypassed'] is False and
            auth['authorizes_validation_release_or_protected_access'] is False,
            'explicit bounded prospective authority required')
    protocol = ROOT/'docs/SCORE_LEARNING_COLLECTION_PROTOCOL_20260924.md'
    schedule = ROOT/'reports/joint_score_protocol_20260924_v1/schedule.json'
    review = ROOT/'reports/joint_score_protocol_20260924_v1/review_decision_CONVERSATION_FINAL.json'
    ps, ss = sha(protocol), sha(schedule)
    require(auth['protocol_sha256'] == ps and auth['schedule_sha256'] == ss, 'authority binding')
    protocol_acceptance(read(review), ps, ss)
    clearance = read(config['static_clearance_audit'])
    rows = [r for r in read(schedule)['rows'] if r['wave'] == 'S']
    require(clearance['passed'] is True and len(clearance['rows']) == len(rows) == 400 and
            [r['attempt_id'] for r in clearance['rows']] == [r['attempt_id'] for r in rows] and
            all(r['clearance_passed'] is True for r in clearance['rows']), 'all scheduled static poses')
    for path, expected in clearance['source_sha256'].items():
        require(sha(path) == expected, 'static audit source changed')
    checked = inspect_transport(capture_root, config_path)
    evidence = read(inference_root/'evidence.json')
    require(evidence['integration_completed'] is True and evidence['primary_eligible'] is False and
            evidence['human_labels_generated'] is False and len(evidence['rows']) == 4,
            'completed nonprimary inference integration required')
    batch = read(inference_root/'batch.json')
    require(batch['driver_config_sha256'] == sha(config_path) and batch['preflight_only'] is True,
            'inference source binding')
    pins = dict(config['input_sha256']); groups = dict(config['asset_groups'])
    groups['static_clearance_audit'] = [config['static_clearance_audit']]
    groups['transport_preflight_audit'] = [str((capture_root/'capture_audit.json').resolve()),
                                         str((inference_root/'evidence.json').resolve())]
    paths = [config_path, Path(config['static_clearance_audit']), auth_path, protocol, schedule, review,
             Path(__file__), inference_root/'batch.json', inference_root/'evidence.json']
    paths += list(capture_root.rglob('*.json'))
    for folder in (inference_root/'detector', inference_root/'ocr'):
        plan, report = read(folder/'plan.json'), read(folder/'report.json')
        require(report['plan_sha256'] == sha(folder/'plan.json') and
                report['journal_sha256'] == sha(folder/'results.jsonl'), 'inference audit binding')
        for path, expected in plan['input_sha256'].items():
            require(sha(path) == expected, 'inference dependency changed')
            pins[path] = expected
        paths += [folder/n for n in ('plan.json', 'report.json', 'results.jsonl')]
    da = read(inference_root/'detector/audit.json')
    require(da['reconstruction_passed'] is True and
            da['report_sha256'] == sha(inference_root/'detector/report.json'), 'raw detector audit')
    paths += [inference_root/'detector/audit.json']
    for completion in sorted((inference_root/'integration').glob('completion-*.json')):
        paths.append(completion)
        value = read(completion)
        for engine in ('detector', 'ocr'):
            require(value[engine]['status'] == 'completed' and value[engine]['audit_passed'] is True,
                    'completed engine acknowledgment')
            for path, expected in value[engine]['input_sha256'].items():
                require(sha(path) == expected, 'completion dependency changed')
                pins[path] = expected
    for path in paths:
        pins[str(path.resolve())] = sha(path)
    manifest = dict(schema_version='research3-jsc-execution/v1', wave='S', protocol_sha256=ps,
        schedule_sha256=ss, preflight_status='passed', serial=True, input_sha256=pins,
        asset_groups=groups, checked_views=checked, primary_attempt_budget=400,
        preflight_is_accuracy_evidence=False, authorizes_wave_c_or_v=False)
    receipt = dict(schema_version='research3-jsc-execution-approval/v1', reviewer_type='human',
        reviewer_name=auth['reviewer_name'], reviewed_at=auth['recorded_at'],
        decision='authorize_wave_s_collection', execution_manifest_sha256=digest(manifest),
        authorizes_validation_or_protected_access=False,
        authority_source=str(auth_path), authority_source_sha256=sha(auth_path),
        user_statement=auth['user_statement'], agent_bound_at=datetime.now(timezone.utc).isoformat(),
        provenance='Agent-bound receipt of prospective conversational authorization, not a human signature or later evidence review.',
        approves_unseen_labels_or_models=False)
    validate_execution(manifest, receipt, protocol_sha=ps, schedule_sha=ss)
    output.mkdir(exist_ok=False)
    write_once(output/'execution_manifest.json', manifest)
    write_once(output/'execution_approval.json', receipt)
    print(json.dumps(dict(status='authorized', wave='S', primary_attempts=400,
                         execution_manifest_sha256=digest(manifest)), indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('config', 'capture-root', 'inference-root', 'output'):
        p.add_argument('--'+name, required=True, type=Path)
    a = p.parse_args()
    bind(a.config, a.capture_root, a.inference_root, a.output)
