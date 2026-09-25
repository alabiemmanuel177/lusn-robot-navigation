"""Prepare/run exactly the approved development-only design-feasibility panel.

No background scheduling, outcome-dependent retries, provider edits or protected
access. Resume never reruns an assignment with a retained start event.
"""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'reports/stage1_view_feasibility_20260921_v3.json'
APPROVAL=ROOT/'reports/stage1_feasibility_authorization_20260921_v1.json'
SNAPSHOT=ROOT/'reports/expansion_instrumentation_snapshot_20260914_v7/snapshot.json'
EXPECTED='124d634d6656a86fa4a830b19e3a27a494cf28cef77ec183f78a4d33fe79c37f'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path,value):
    with Path(path).open('x') as stream:
        json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n');stream.flush();os.fsync(stream.fileno())


def assignments():
    if sha(MANIFEST)!=EXPECTED:raise ValueError('approved manifest changed')
    approval=json.loads(APPROVAL.read_bytes())
    if approval.get('authorized') is not True or approval.get('manifest_sha256')!=EXPECTED:raise PermissionError('bound scope approval required')
    data=json.loads(MANIFEST.read_bytes());rows=[]
    for world in data['maps']:
        number=world['map_number']
        if number not in range(1,11):raise ValueError('development maps only')
        folder=ROOT/f'data/physical_worlds_readable_v1/base-r{number:03}'
        for name,digest in world['source_sha256'].items():
            if sha(folder/name)!=digest:raise ValueError('world source drift')
        for target in world['targets']:
            for row in target['candidates']:
                if (row['partition']!='development' or not row['footprint_checked'] or not row['ray_proxy_clear']
                        or row['world_directory']!=str(folder.relative_to(ROOT))):raise ValueError('candidate scope')
                rows.append(row)
    if len(rows)!=80 or len({r['candidate_id'] for r in rows})!=80:raise ValueError('exact 80 unique assignments required')
    return rows


def argv(row):
    world=ROOT/row['world_directory'];pose=row['pose']
    return ['nice','-n','19','ionice','-c','3','python3',str(ROOT/'scripts/run_physical_episode.py'),
        '--world',str(world),'--variant-id',world.name+'-truthful_original-s0',
        '--run-id',row['candidate_id'],'--ros-domain-id','89','--simulation-seed','1','--timeout','90',
        '--capture-only','--capture-frame-budget','1','--capture-pose',*[repr(pose[k]) for k in ('x','y','yaw')],
        '--capture-target-category',row['category'],'--capture-entity-id',row['entity_id'],
        '--camera-profile',str(ROOT/row['camera_profile']),'--camera-horizontal-fov','2.0',
        '--expansion-instrumentation-snapshot',str(SNAPSHOT)]


def other_simulators(proc=Path('/proc')):
    pids=[]
    for entry in proc.iterdir():
        if not entry.name.isdigit():continue
        try:args=(entry/'cmdline').read_bytes().decode(errors='replace').split('\0')
        except FileNotFoundError:continue
        sim=any(Path(arg).name in ('gz','ign') and i+1<len(args) and args[i+1]=='sim' for i,arg in enumerate(args))
        if sim and not any(str(ROOT) in arg for arg in args):pids.append(int(entry.name))
    return sorted(pids)


def resource_gate():
    from language_nav.live_resources import coexistence_headroom,require_research2_idle
    require_research2_idle();headroom=coexistence_headroom()
    pids=other_simulators()
    gpu=int(Path('/sys/class/drm/card0/device/gpu_busy_percent').read_text())
    if pids or gpu>30:raise RuntimeError(f'wait for other simulations/GPU headroom: simulator PIDs={pids}, GPU={gpu}%')
    free=os.statvfs(ROOT);free_bytes=free.f_bavail*free.f_frsize
    if free_bytes<20*2**30:raise RuntimeError('less than 20 GiB disk headroom')
    return dict(headroom,gpu_busy_percent=gpu,other_simulators=pids,disk_free_bytes=free_bytes)


def prepare(output):
    from snapshot_expansion_instrumentation import validate
    rows=assignments();snapshot_sha=validate(SNAPSHOT)
    output.mkdir(parents=True,exist_ok=False)
    inputs={str(p.relative_to(ROOT)):sha(p) for p in (MANIFEST,APPROVAL,SNAPSHOT,Path(__file__))}
    prepared=[]
    for row in rows:
        profile=ROOT/row['camera_profile'];inputs[str(profile.relative_to(ROOT))]=sha(profile)
        result=subprocess.run(argv(row)+['--prepare-only'],capture_output=True,text=True,timeout=30,cwd=ROOT)
        if result.returncode:raise RuntimeError(result.stderr)
        request=json.loads(result.stdout)
        if request['partition']!='development' or request['protected_test_routes_used'] is not False:raise ValueError('prepared scope')
        prepared.append(dict(candidate_id=row['candidate_id'],argv=argv(row),request=request))
    plan=dict(schema_version='research3-stage1-feasibility-execution-plan/v1',rows=prepared,
        input_sha256=inputs,snapshot_sha256=snapshot_sha,approved_manifest_sha256=EXPECTED,
        retries=0,serial=True,calibration_eligible=False,validation_access=False,protected_access=False)
    write(output/'execution_plan.json',plan)
    print(json.dumps(dict(prepared=len(prepared),executed=False,output=str(output))),flush=True)


def run_owned(command,log,lock_fd):
    from language_nav.live_resources import coexistence_headroom,require_research2_idle
    process=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
                             start_new_session=True,pass_fds=(lock_fd,))
    deadline=time.monotonic()+600
    try:
        while process.poll() is None:
            if time.monotonic()>deadline:raise TimeoutError('600-second owned process limit')
            coexistence_headroom();require_research2_idle()
            if other_simulators():raise RuntimeError('another simulation started; stop only owned R3 run')
            time.sleep(1)
        return process.returncode
    finally:
        for sig,grace in ((signal.SIGINT,30),(signal.SIGTERM,15),(signal.SIGKILL,5)):
            if process.poll() is not None:break
            os.killpg(process.pid,sig)
            try:process.wait(timeout=grace)
            except subprocess.TimeoutExpired:pass


def execute(output):
    from snapshot_expansion_instrumentation import validate
    from physical_engineering_smoke import require_no_live_runner
    from run_expansion_collection import classify
    plan=json.loads((output/'execution_plan.json').read_bytes())
    approved=assignments()
    if len(plan['rows'])!=len(approved):raise ValueError('execution plan shape changed')
    for row,target in zip(plan['rows'],approved,strict=True):
        if row['candidate_id']!=target['candidate_id'] or row['argv']!=argv(target):raise ValueError('execution plan argv changed')
    for name,digest in plan['input_sha256'].items():
        if sha(ROOT/name)!=digest:raise ValueError('prepared input changed')
    fd=os.open(ROOT/'reports/.research3_physical_execution.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);require_no_live_runner()
        for row in plan['rows']:
            identifier=row['candidate_id'];end=output/(identifier+'.result.json');start=output/(identifier+'.start.json')
            if end.exists():
                if json.loads(end.read_bytes())['status']=='infrastructure_failure':raise RuntimeError('retained infrastructure failure requires explicit disposition')
                continue
            run_dir=ROOT/'reports/physical_live_episodes'/identifier
            if start.exists() or run_dir.exists():raise RuntimeError('interrupted assignment retained; no automatic replay')
            for _ in range(3):headroom=resource_gate();time.sleep(2)
            if validate(SNAPSHOT)!=plan['snapshot_sha256']:raise ValueError('snapshot changed')
            assignments()
            for name,digest in plan['input_sha256'].items():
                if sha(ROOT/name)!=digest:raise ValueError('input changed before launch')
            write(start,dict(started_at=dt.datetime.now(dt.timezone.utc).isoformat(),resource_preflight=headroom,argv=row['argv']))
            error=None;code=None
            try:
                with (output/(identifier+'.log')).open('x') as log:code=run_owned(row['argv'],log,fd)
            except Exception as exc:error=str(exc)
            outcome=classify(run_dir)
            if code!=0 or error:outcome.update(status='infrastructure_failure',executor_error=error,exit_code=code)
            write(end,dict(outcome,finished_at=dt.datetime.now(dt.timezone.utc).isoformat(),calibration_eligible=False))
            print(json.dumps(dict(candidate_id=identifier,status=outcome['status'])),flush=True)
            if outcome['status']=='infrastructure_failure':raise RuntimeError('retained infrastructure failure; no automatic replacement')
    finally:os.close(fd)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--execute',action='store_true')
    args=p.parse_args()
    if args.execute:execute(args.output.resolve())
    else:prepare(args.output.resolve())
