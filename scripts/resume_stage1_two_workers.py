"""Execute the unchanged remaining 36 views of the unchanged 80-view feasibility panel in guarded two-worker batches.

Concurrency authorized by the September 22 resource-scaling/continue instructions.
No retries, primary calibration credit, human labels or protected access.
"""
from concurrent.futures import ThreadPoolExecutor
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time
import run_stage1_feasibility as base
from inspect_simulator_workloads import inspect as inspect_external_workloads


def external_workload_pids():
    return [row['pid'] for row in inspect_external_workloads()]


ROOT = base.ROOT
OUTPUT = ROOT / 'reports/stage1_two_workers_20260922_v4'
SNAPSHOT = ROOT / 'reports/expansion_instrumentation_snapshot_20260922_v8/snapshot.json'
PRIOR = ROOT / 'reports/stage1_four_workers_20260922_v1'
REPAIR = ROOT / 'reports/stage1_resume36_approval_20260922.json'


def audit_capture(folder):
    folder = Path(folder)
    read = lambda name: json.loads((folder / name).read_bytes())
    request = read('request.json')
    summary = read('capture_summary.json')
    frame_path = folder / 'perception_capture/frame-000.json'
    frame = json.loads(frame_path.read_bytes())
    completion = read('provider_frame_completion.json')
    attempt = read('expansion_attempt.json')
    assert request['partition'] == 'development' and not request['protected_test_routes_used']
    assert summary['complete'] and not summary['human_labels_generated'] and not summary['motion_commands_sent']
    assert completion['status'] == 'completed' and completion['frame_sha256'] == base.sha(frame_path)
    assert completion['frame_stamp_ns'] == frame['rgb_stamp_ns']
    assert frame['rgb_stamp_ns'] == frame['depth_stamp_ns'] and not frame['observation_triggered']
    for kind in ('rgb', 'depth'):
        source = frame_path.parent / frame[kind]['file']
        assert source.stat().st_size == frame[kind]['bytes'] and base.sha(source) == frame[kind]['sha256']
    expected = [dict(r, frame_stamp_ns=r['observed_at_ns']) for r in completion['observations']]
    assert sorted(expected, key=lambda r:r['observation_id']) == sorted(attempt['retained_observations'], key=lambda r:r['observation_id'])
    assert attempt['human_verdict'] is None and not attempt['confidence_used_for_selection']
    return dict(run_id=request['run_id'], status=attempt['status'], frame_sha256=base.sha(frame_path),
                selected_observation=attempt['selected_observation'], human_correctness_verified=False)


def commands():
    result = []
    for index, row in enumerate(base.assignments()[44:]):
        command = base.argv(row)
        command[command.index('--expansion-instrumentation-snapshot') + 1] = str(SNAPSHOT)
        command[command.index('--ros-domain-id') + 1] = str(100 + index % 2)
        result.append(dict(candidate_id=row['candidate_id'], argv=command))
    return result


def prepare():
    from snapshot_expansion_instrumentation import validate
    validate(SNAPSHOT)
    audits = [audit_capture(ROOT / f'reports/physical_live_episodes/r3-parallel-engineering-20260922-w{i}') for i in range(1,5)]
    approval=json.loads(REPAIR.read_bytes())
    if (approval.get('authorized') is not True or approval.get('resume_unstarted_count')!=36
            or approval.get('workers')!=2 or approval.get('require_external_campaign_idle') is not True):
        raise ValueError('exact resume approval required')
    retained=[PRIOR/(r['candidate_id']+'.result.json') for r in base.assignments()[:24]]
    prior_resume=ROOT/'reports/stage1_four_workers_20260922_v2'
    retained += [prior_resume/(r['candidate_id']+'.result.json') for r in base.assignments()[24:44]]
    if sum(json.loads(p.read_bytes())['status']=='infrastructure_failure' for p in retained)!=5:
        raise ValueError('retained failure accounting changed')
    for path in retained:
        if not path.exists():raise ValueError('original attempted evidence missing')
    rows = commands()
    pins = {str(p):base.sha(p) for p in (Path(__file__), Path(base.__file__), base.MANIFEST, base.APPROVAL, SNAPSHOT, REPAIR, ROOT/'scripts/snapshot_expansion_instrumentation.py', ROOT/'scripts/inspect_simulator_workloads.py', *retained)}
    for row in rows:
        response = subprocess.run(row['argv'] + ['--prepare-only'], cwd=ROOT, capture_output=True, text=True, check=True, timeout=30)
        row['request'] = json.loads(response.stdout)
        profile = Path(row['argv'][row['argv'].index('--camera-profile') + 1])
        pins[str(profile)] = base.sha(profile)
    OUTPUT.mkdir(exist_ok=False)
    base.write(OUTPUT / 'plan.json', dict(rows=rows, input_sha256=pins, trial_integrity_audits=audits,
        concurrency=2, calibration_eligible=False, retries=0, protected_access=False,
        authority='Explicit September 22 two-worker resume approval; all 44 prior attempts and five failures retained',
        scientific_manifest_sha256=base.EXPECTED))
    print('Prepared 36 unstarted assignments, two workers, trial integrity checks passed', flush=True)


def execute():
    # Only this dedicated executor process uses the strengthened scanner.
    # Importing this module for offline tests does not change historical helpers.
    base.other_simulators = external_workload_pids
    from snapshot_expansion_instrumentation import validate
    from physical_engineering_smoke import require_no_live_runner
    plan = json.loads((OUTPUT / 'plan.json').read_bytes())
    if [(r['candidate_id'],r['argv']) for r in plan['rows']] != [(r['candidate_id'],r['argv']) for r in commands()]:
        raise ValueError('plan commands changed')
    fd = os.open(ROOT / 'reports/.research3_physical_execution.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require_no_live_runner()
        for offset in range(0,36,2):
            batch = []
            for row in plan['rows'][offset:offset+2]:
                name = row['candidate_id']
                end = OUTPUT / (name + '.result.json')
                if end.exists():
                    if json.loads(end.read_bytes())['status'] == 'infrastructure_failure':
                        raise RuntimeError('retained failure requires disposition; no retry')
                    continue
                if (OUTPUT / (name + '.start.json')).exists() or (ROOT / 'reports/physical_live_episodes' / name).exists():
                    raise RuntimeError('interrupted evidence; no automatic replay')
                batch.append(row)
            if not batch:
                continue
            for path,digest in plan['input_sha256'].items():
                if base.sha(path) != digest:raise ValueError('pinned input changed')
            base.assignments(); validate(SNAPSHOT)
            for _ in range(3):
                headroom = base.resource_gate(); time.sleep(2)
            def worker(row):
                name = row['candidate_id']; started = time.time()
                base.write(OUTPUT / (name + '.start.json'), dict(time=started, argv=row['argv'], resources=headroom))
                try:
                    with (OUTPUT / (name + '.log')).open('x') as log:
                        code = base.run_owned(row['argv'], log, fd)
                    if code != 0:raise RuntimeError(f'runner exit {code}')
                    outcome = audit_capture(ROOT / 'reports/physical_live_episodes' / name)
                except Exception as exc:
                    outcome = dict(status='infrastructure_failure', error=str(exc), run_id=name)
                outcome.update(elapsed_s=time.time()-started, calibration_eligible=False)
                base.write(OUTPUT / (name + '.result.json'), outcome)
                return outcome
            with ThreadPoolExecutor(max_workers=2) as pool:
                outcomes = list(pool.map(worker,batch))
            print(json.dumps(dict(batch=offset//2+1, outcomes=[dict(run_id=r['run_id'],status=r['status']) for r in outcomes])),flush=True)
            if any(r['status']=='infrastructure_failure' for r in outcomes):
                raise RuntimeError('batch stopped on infrastructure failure; no replacements')
    finally:
        os.close(fd)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    if parser.parse_args().execute:execute()
    else:prepare()
