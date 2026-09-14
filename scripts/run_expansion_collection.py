#!/usr/bin/env python3
"""Serial, resource-guarded executor for the accepted 560-attempt expansion schedule.

Plan-only unless --execute. Runs one partition of the hash-bound plan through
the owned runner with the pinned exact-frame instrumentation, retains every
attempt under its own immutable run ID, and writes a completion report. The
report for the development partition is the evidence the runner requires
before any validation attempt. Nothing here labels observations, fits
calibration or authorizes protected execution.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
RUNNER = ROOT / 'scripts/run_physical_episode.py'
RUNS = ROOT / 'reports/physical_live_episodes'
WORLDS = ROOT / 'data/physical_worlds_readable_v1'
PLAN = ROOT / 'reports/calibration_expansion_handoff_20260912_v1/plan.json'
DECISION = ROOT / 'reports/calibration_expansion_handoff_20260912_v1/amendment_review_decision.json'
FREEZE_TEMPLATE = ROOT / 'reports/engineering_camera_settings_v3/camera_settings_freeze.json'
PROFILE_DIRS = (ROOT / 'reports/fresh_current_capture_20260911_v1/profiles',
                ROOT / 'reports/engineering_camera_settings_v3/profiles')
CANDIDATE = re.compile(r'expansion-v1-r(00[1-9]|01[0-4])-(chair|doorway|laboratory_entrance|office_entrance)-s[12]-view[0-4]')
REPORT_SCHEMA = 'research3-expansion-collection-report/v1'
TERMINAL = ('emitted', 'nondetection', 'ambiguous_emissions', 'infrastructure_failure')
MAX_CONSECUTIVE_INFRASTRUCTURE_FAILURES = 3
# Infrastructure causes verified from retained records that precede any provider
# outcome: nothing armed, or the collector's own exact-stamp transform lookup
# raced the transform data. These qualify for the single new-ID retry the
# amendment permits; provider outcomes (emitted, nondetection, ambiguous) never do.
RETRYABLE_REASONS = frozenset({'transform_invalid'})


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha_file(path) -> str:
    return sha(Path(path).read_bytes())


def write_once(path, payload):
    with Path(path).open('x') as stream:
        json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def load_plan(plan_path=PLAN, decision_path=DECISION):
    raw = Path(plan_path).read_bytes()
    decision = json.loads(Path(decision_path).read_bytes())
    if (decision.get('schema_version') != 'research3-calibration-expansion-review/v1'
            or decision.get('overall_decision') != 'accept' or decision.get('plan_sha256') != sha(raw)
            or not decision.get('reviewer_name', '').strip()):
        raise PermissionError('plan is not the human-accepted expansion schedule')
    plan = json.loads(raw)
    if plan.get('schema_version') != 'research3-calibration-expansion-plan/v1' or len(plan['rows']) != 560:
        raise ValueError('complete 560-row expansion plan required')
    ids = [row['candidate_id'] for row in plan['rows']]
    if len(set(ids)) != 560 or any(not CANDIDATE.fullmatch(i) for i in ids):
        raise ValueError('plan row identities are not the prespecified candidates')
    return plan, sha(raw), decision


def profile_for(row):
    for folder in PROFILE_DIRS:
        path = folder / (row['map_id'].removeprefix('r3geo_').replace('_', '-') + '.yaml')
        if path.exists() and sha_file(path) == row['camera_profile_sha256']:
            return path
    raise ValueError('pinned camera profile not found: ' + row['candidate_id'])


def world_for(row):
    return WORLDS / row['map_id'].removeprefix('r3geo_').replace('_', '-')


def per_view_freeze(row, template_path, destination):
    """One v2 camera freeze binding exactly this validation view, derived from the pinned template."""
    from language_nav.camera_configuration import capture_source_snapshot
    template = json.loads(Path(template_path).read_bytes())
    if template.get('schema_version') != 'research3-engineering-camera-freeze/v2':
        raise ValueError('v2 freeze template required')
    world = world_for(row)
    view = dict(map_id=row['map_id'], category=row['category'], capture_pose=row['capture_pose'],
                world_sha256={name: sha_file(world / name) for name in
                              ('world.sdf', 'execution_catalog.json', 'landmark_scene.yaml', 'map.pgm', 'map.yaml')})
    for name, digest in row['world_sha256'].items():
        if view['world_sha256'].get(name, digest) != digest:
            raise ValueError('validation world differs from the accepted plan')
    payload = dict(template, validation_views=[view], source_sha256=capture_source_snapshot(),
                   derived_from_freeze_sha256=sha_file(template_path), expansion_candidate_id=row['candidate_id'],
                   per_view_binding='one validation view per freeze, as the accepted amendment permits')
    write_once(destination, payload)
    return destination


def command(row, *, snapshot, domain, timeout, freeze=None, development_report=None):
    world = world_for(row)
    base = world.name
    argv = ['nice', '-n', '15', 'python3', str(RUNNER), '--world', str(world),
            '--variant-id', f'{base}-truthful_original-s0', '--run-id', row['run_id'],
            '--ros-domain-id', str(domain), '--simulation-seed', str(row['seed']), '--timeout', str(timeout),
            '--capture-only', '--capture-frame-budget', '1',
            '--capture-pose', repr(float(row['capture_pose']['x'])), repr(float(row['capture_pose']['y'])),
            repr(float(row['capture_pose']['yaw'])),
            '--capture-target-category', row['category'], '--capture-entity-id', row['entity_id'],
            '--camera-profile', str(profile_for(row)), '--camera-horizontal-fov', '2.0',
            '--expansion-instrumentation-snapshot', str(snapshot)]
    if row['partition'] == 'validation':
        argv += ['--camera-settings-freeze', str(freeze), '--development-complete-report', str(development_report)]
    return argv


def run_owned(argv, log):
    process = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT, start_new_session=True)
    try:
        return process.wait(timeout=600)
    except BaseException:
        for sig, grace in ((signal.SIGINT, 30), (signal.SIGTERM, 15), (signal.SIGKILL, 5)):
            if process.poll() is not None:
                break
            os.killpg(process.pid, sig)
            try:
                process.wait(timeout=grace)
                break
            except subprocess.TimeoutExpired:
                continue
        raise


def classify(run_dir):
    run_dir = Path(run_dir)
    attempt = run_dir / 'expansion_attempt.json'
    failure = run_dir / 'failure.json'
    armed = (run_dir / 'perception_capture/armed.json').exists()
    provider_started = (run_dir / 'provider_frame_started.json').exists()
    if attempt.exists():
        record = json.loads(attempt.read_bytes())
        reasons = record.get('reasons', [])
        # Retryable only when no provider outcome exists for the frame: the
        # provider never began processing it, or only the collector's own
        # transform record was missing while the provider did process it.
        return dict(status=record['status'], reasons=reasons, armed=armed,
                    selected_entity=(record.get('selected_observation') or {}).get('entity_id'),
                    attempt_sha256=sha_file(attempt), provider_started=provider_started,
                    predispatch=(record['status'] == 'infrastructure_failure'
                                 and (not provider_started or (bool(reasons) and set(reasons) <= RETRYABLE_REASONS))))
    if failure.exists():
        record = json.loads(failure.read_bytes())
        return dict(status='infrastructure_failure', reasons=[record.get('error', 'failure')], armed=armed,
                    selected_entity=None, attempt_sha256=None, predispatch=not armed)
    return dict(status='infrastructure_failure', reasons=['no attempt or failure record'], armed=armed,
                selected_entity=None, attempt_sha256=None, predispatch=not armed)


def existing_attempts(directory):
    path = Path(directory) / 'attempts.jsonl'
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def started_attempts(directory):
    """Ledger records whose run directory exists; a launch the runner rejected before
    creating anything retained no evidence and is not a consumed attempt."""
    return [record for record in existing_attempts(directory) if Path(record['run_directory']).exists()]


def launch_rejections(directory):
    return [record for record in existing_attempts(directory) if not Path(record['run_directory']).exists()]


def execute(args):
    from language_nav.live_resources import require_research2_idle, coexistence_headroom
    from language_nav.campaign_authorization import exclusive_campaign_runtime
    from snapshot_expansion_instrumentation import validate as validate_snapshot
    plan, plan_sha, decision = load_plan(args.plan, args.decision)
    rows = [dict(row, run_id=row['candidate_id']) for row in plan['rows'] if row['partition'] == args.partition]
    if len(rows) != {'development': 400, 'validation': 160}[args.partition]:
        raise ValueError('unexpected partition size')
    snapshot = Path(args.snapshot).resolve()
    snapshot_sha = validate_snapshot(snapshot)
    directory = Path(args.lifecycle_directory).resolve()
    development_report = None
    if args.partition == 'validation':
        if not args.development_complete_report:
            raise PermissionError('validation collection requires the complete development report')
        development_report = Path(args.development_complete_report).resolve()
        validate_development_complete_report(development_report)
    if args.resume:
        planned = json.loads((directory / 'planned.json').read_bytes())
        if planned['plan_sha256'] != plan_sha or planned['partition'] != args.partition:
            raise ValueError('resume must continue the identical planned schedule')
        if planned['snapshot_sha256'] != snapshot_sha:
            if not args.accept_snapshot_change:
                raise ValueError('resume with a different instrumentation snapshot requires --accept-snapshot-change and a reason')
            with (directory / 'snapshot_changes.jsonl').open('a') as stream:
                stream.write(json.dumps(dict(previous_sha256=planned['snapshot_sha256'], new_sha256=snapshot_sha,
                                             new_path=str(snapshot), reason=args.accept_snapshot_change,
                                             at_utc=dt.datetime.now(dt.timezone.utc).isoformat()), sort_keys=True) + '\n')
        started = started_attempts(directory)
        done = set()
        for record in started:
            if record['status'] in TERMINAL and record.get('final'):
                done.add(record['candidate_id'])
        # A retained retryable infrastructure failure on the first attempt may
        # still use its single retry when the run resumes.
        for record in started:
            if (record['status'] == 'infrastructure_failure' and record.get('predispatch') and record['attempt_index'] == 0
                    and not any(r['candidate_id'] == record['candidate_id'] and r['attempt_index'] == 1 for r in started)):
                done.discard(record['candidate_id'])
    else:
        directory.mkdir(parents=True, exist_ok=False)
        (directory / 'freezes').mkdir()
        done = set()
    freezes = {}
    if args.partition == 'validation':
        for row in rows:
            destination = directory / 'freezes' / (row['candidate_id'] + '.json')
            if not destination.exists():
                per_view_freeze(row, args.freeze_template, destination)
            freezes[row['candidate_id']] = destination
    argvs = {row['candidate_id']: command(row, snapshot=snapshot, domain=args.ros_domain_id, timeout=args.timeout,
                                          freeze=freezes.get(row['candidate_id']), development_report=development_report)
             for row in rows}
    if not args.resume:
        write_once(directory / 'planned.json', dict(
            schema_version='research3-expansion-collection-plan/v1', partition=args.partition, plan_path=str(args.plan),
            plan_sha256=plan_sha, decision_sha256=sha_file(args.decision), snapshot_path=str(snapshot),
            snapshot_sha256=snapshot_sha, ros_domain_id=args.ros_domain_id, timeout_s=args.timeout,
            development_complete_report=str(development_report) if development_report else None,
            development_complete_report_sha256=sha_file(development_report) if development_report else None,
            rows=[dict(candidate_id=row['candidate_id'], run_id=row['run_id'], argv=argvs[row['candidate_id']])
                  for row in rows],
            retry_policy='one new-ID retry only for infrastructure failure before arming; the original stays retained',
            stopping_rule=f'halt after {MAX_CONSECUTIVE_INFRASTRUCTURE_FAILURES} consecutive infrastructure failures; never on outcome',
            execute=bool(args.execute), human_labels_generated=False, execution_scope='fixed prespecified schedule, no outcome chasing'))
    if not args.execute:
        print(json.dumps(dict(partition=args.partition, planned=len(rows), executed=False, plan_sha256=plan_sha)))
        return
    consecutive = 0
    with exclusive_campaign_runtime(), (directory / 'attempts.jsonl').open('a') as ledger:
        for row in rows:
            if row['candidate_id'] in done:
                continue
            if args.limit is not None and len([1 for r in started_attempts(directory) if r.get('final')]) >= args.limit:
                break
            for attempt_index, run_id in enumerate((row['candidate_id'], row['candidate_id'] + '-retry1')):
                if attempt_index == 0 and (RUNS / run_id).exists():
                    # Resumed retry of a retained first attempt: keep the original directory.
                    continue
                if (RUNS / run_id).exists():
                    raise FileExistsError(f'run directory already exists: {run_id}; no overwrite')
                require_research2_idle()
                headroom = coexistence_headroom()
                argv = list(argvs[row['candidate_id']])
                argv[argv.index('--run-id') + 1] = run_id
                started = dt.datetime.now(dt.timezone.utc).isoformat()
                with (directory / f'{run_id}.log').open('x') as log:
                    code = run_owned(argv, log)
                outcome = classify(RUNS / run_id)
                retry = (outcome['status'] == 'infrastructure_failure' and outcome.get('predispatch') and attempt_index == 0)
                record = dict(candidate_id=row['candidate_id'], run_id=run_id, attempt_index=attempt_index,
                              partition=args.partition, map_id=row['map_id'], category=row['category'],
                              entity_id=row['entity_id'], seed=row['seed'], view_group=row['view_group'],
                              exit_code=code, started_at_utc=started,
                              finished_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                              headroom_before=headroom, run_directory=str(RUNS / run_id),
                              request_sha256=sha_file(RUNS / run_id / 'request.json') if (RUNS / run_id / 'request.json').exists() else None,
                              final=not retry, **outcome)
                ledger.write(json.dumps(record, sort_keys=True) + '\n')
                ledger.flush()
                os.fsync(ledger.fileno())
                print(json.dumps({k: record[k] for k in ('run_id', 'status', 'exit_code', 'final')}), flush=True)
                if not retry:
                    break
            consecutive = consecutive + 1 if record['status'] == 'infrastructure_failure' else 0
            if consecutive >= MAX_CONSECUTIVE_INFRASTRUCTURE_FAILURES:
                print(json.dumps(dict(halted='consecutive infrastructure failures', count=consecutive)), flush=True)
                break
    write_report(directory, rows, plan_sha, snapshot_sha, args.partition)


def write_report(directory, rows, plan_sha, snapshot_sha, partition):
    directory = Path(directory)
    attempts = started_attempts(directory)
    final = {}
    for record in attempts:
        # The last record per candidate is authoritative: a resumed retry
        # supersedes its retained first attempt for accounting only.
        if record.get('final') or record['attempt_index'] == 0:
            final[record['candidate_id']] = record
    for record in attempts:
        if record['attempt_index'] == 1:
            final[record['candidate_id']] = record
    counts = {status: sum(1 for r in final.values() if r['status'] == status) for status in TERMINAL}
    report = dict(schema_version=REPORT_SCHEMA, partition=partition, plan_sha256=plan_sha,
                  snapshot_sha256=snapshot_sha, scheduled=len(rows), accounted=len(final),
                  attempts_including_retries=len(attempts), status_counts=counts,
                  retryable_reasons=sorted(RETRYABLE_REASONS),
                  complete=len(final) == len(rows) and all(r['status'] in TERMINAL for r in final.values()),
                  attempts=[dict(candidate_id=r['candidate_id'], run_id=r['run_id'], status=r['status'],
                                 request_sha256=r['request_sha256'], attempt_sha256=r['attempt_sha256'],
                                 selected_entity=r['selected_entity']) for r in final.values()],
                  retries=[dict(candidate_id=r['candidate_id'], run_id=r['run_id'], reasons=r['reasons'])
                           for r in attempts if r['attempt_index'] == 0 and r['candidate_id'] in final
                           and final[r['candidate_id']]['attempt_index'] == 1],
                  snapshot_changes=[json.loads(line) for line in (directory / 'snapshot_changes.jsonl').read_text().splitlines()]
                  if (directory / 'snapshot_changes.jsonl').exists() else [],
                  launch_rejections=[dict(run_id=r['run_id'], reasons=r['reasons'], started_at_utc=r['started_at_utc'])
                                     for r in launch_rejections(directory)],
                  human_labels_generated=False, calibration_fitted=False, execution_scope='nonprotected_expansion_collection',
                  written_at_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    path = directory / 'report.json'
    if path.exists():
        path.rename(directory / f'report.superseded.{int(dt.datetime.now().timestamp())}.json')
    write_once(path, report)
    print(json.dumps({k: report[k] for k in ('partition', 'scheduled', 'accounted', 'status_counts', 'complete')}))
    return report


def validate_development_complete_report(path):
    path = Path(path)
    raw = path.read_bytes()
    report = json.loads(raw)
    _, plan_sha, _ = load_plan()
    if (report.get('schema_version') != REPORT_SCHEMA or report.get('partition') != 'development'
            or report.get('plan_sha256') != plan_sha or report.get('complete') is not True
            or report.get('scheduled') != 400 or report.get('accounted') != 400
            or report.get('human_labels_generated') is not False):
        raise PermissionError('complete development expansion collection report required')
    attempts = report['attempts']
    if len(attempts) != 400 or len({a['candidate_id'] for a in attempts}) != 400:
        raise ValueError('development report must account for every scheduled attempt exactly once')
    for attempt in attempts:
        run_dir = RUNS / attempt['run_id']
        if not run_dir.resolve().is_relative_to(RUNS.resolve()) or sha_file(run_dir / 'request.json') != attempt['request_sha256']:
            raise ValueError('development attempt evidence changed: ' + attempt['run_id'])
    return sha(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=PLAN)
    parser.add_argument('--decision', type=Path, default=DECISION)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--partition', choices=('development', 'validation'), required=True)
    parser.add_argument('--lifecycle-directory', type=Path, required=True)
    parser.add_argument('--ros-domain-id', type=int, default=89)
    parser.add_argument('--timeout', type=int, default=90)
    parser.add_argument('--development-complete-report', type=Path)
    parser.add_argument('--freeze-template', type=Path, default=FREEZE_TEMPLATE)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--accept-snapshot-change', help='reason for continuing a resumed schedule under a newer instrumentation pin')
    parser.add_argument('--limit', type=int, help='stop after this many final attempts in this session (preflight use)')
    args = parser.parse_args()
    execute(args)


if __name__ == '__main__':
    main()
