"""Bounded four-worker development engineering trial; prepare-only by default.

Separate from the 80-view scientific feasibility schedule. No retries, labels,
calibration, validation access or campaign-concurrency authorization.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time

import run_stage1_feasibility as serial

ROOT = serial.ROOT
OUTPUT = ROOT / 'reports/four_worker_capture_trial_20260922_v1'


def commands():
    # Fixed before observing outcomes: map 1, all four classes, view 0.
    rows = serial.assignments()
    selected = [next(r for r in rows if r['candidate_id'] == identifier) for identifier in
                ('r3-recovery-feas-r001-chair-v0', 'r3-recovery-feas-r001-doorway-v0',
                 'r3-recovery-feas-r001-laboratory_entrance-v0', 'r3-recovery-feas-r001-office_entrance-v0')]
    result = []
    for index, row in enumerate(selected):
        command = serial.argv(row)
        identifier = f'r3-parallel-engineering-20260922-w{index + 1}'
        command[command.index('--run-id') + 1] = identifier
        command[command.index('--ros-domain-id') + 1] = str(92 + index)
        result.append(dict(run_id=identifier, argv=command))
    return result


def validate_pair(requests):
    if len(requests) != 4:
        raise ValueError('exactly four workers required')
    for key in ('run_id', 'ros_domain_id', 'worker_id'):
        if len({r[key] for r in requests}) != 4:
            raise ValueError('workers share ' + key)
    for request in requests:
        if request['partition'] != 'development' or request['protected_test_routes_used']:
            raise ValueError('development only')


def prepare():
    from snapshot_expansion_instrumentation import validate
    snapshot = validate(serial.SNAPSHOT)
    rows = commands()
    for row in rows:
        response = subprocess.run(row['argv'] + ['--prepare-only'], cwd=ROOT,
                                  capture_output=True, text=True, timeout=30, check=True)
        row['request'] = json.loads(response.stdout)
    validate_pair([r['request'] for r in rows])
    paths = [Path(__file__), Path(serial.__file__), serial.MANIFEST, serial.SNAPSHOT]
    paths += [Path(r['argv'][r['argv'].index('--camera-profile') + 1]) for r in rows]
    OUTPUT.mkdir(exist_ok=False)
    plan = dict(rows=rows, snapshot_sha256=snapshot,
                input_sha256={str(p): serial.sha(p) for p in paths},
                authorization=dict(user_response='Okay so you have the full System at you disposal, use as much resources as you need please',
                                   scope='four concurrent development engineering captures only'),
                calibration_eligible=False, retries=0, changes_eighty_view_schedule=False,
                transport_mapping='unique worker_id sets both GZ_PARTITION and IGN_PARTITION',
                acceptance='All four captures complete with exact-frame evidence; inspect retained evidence before approving wider concurrency. No speedup claim from this four-worker trial alone.')
    serial.write(OUTPUT / 'plan.json', plan)
    print(json.dumps(dict(prepared=4, executed=False, output=str(OUTPUT))), flush=True)


def execute():
    from physical_engineering_smoke import require_no_live_runner
    from snapshot_expansion_instrumentation import validate
    from run_expansion_collection import classify
    plan = json.loads((OUTPUT / 'plan.json').read_bytes())
    if [(r['run_id'], r['argv']) for r in plan['rows']] != [(r['run_id'], r['argv']) for r in commands()]:
        raise ValueError('trial commands changed')
    for path, digest in plan['input_sha256'].items():
        if serial.sha(path) != digest:
            raise ValueError('trial input changed')
    validate_pair([r['request'] for r in plan['rows']])
    if validate(serial.SNAPSHOT) != plan['snapshot_sha256']:
        raise ValueError('snapshot changed')
    fd = os.open(ROOT / 'reports/.research3_physical_execution.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require_no_live_runner()
        for row in plan['rows']:
            if (ROOT / 'reports/physical_live_episodes' / row['run_id']).exists():
                raise RuntimeError('existing evidence: no automatic retry')
        for _ in range(3):
            headroom = serial.resource_gate()
            time.sleep(2)
        serial.write(OUTPUT / 'started.json', dict(resource_preflight=headroom, time=time.time()))

        def worker(row):
            start = time.monotonic()
            error = None
            code = None
            try:
                with (OUTPUT / (row['run_id'] + '.log')).open('x') as log:
                    code = serial.run_owned(row['argv'], log, fd)
            except Exception as exc:
                error = str(exc)
            result = classify(ROOT / 'reports/physical_live_episodes' / row['run_id'])
            result.update(run_id=row['run_id'], elapsed_s=time.monotonic() - start,
                          exit_code=code, executor_error=error, calibration_eligible=False)
            if code != 0 or error:
                result['status'] = 'infrastructure_failure'
            serial.write(OUTPUT / (row['run_id'] + '.result.json'), result)
            return result

        start = time.monotonic()
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(worker, plan['rows']))
        serial.write(OUTPUT / 'result.json', dict(results=results, elapsed_s=time.monotonic() - start,
                     wider_concurrency_approved=False, evidence_inspection_required=True))
        print(json.dumps(results), flush=True)
    finally:
        os.close(fd)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    if parser.parse_args().execute:
        execute()
    else:
        prepare()
