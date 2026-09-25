"""Fixed Stage A executor: isolated first capture, then guarded two-worker batches."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time
import run_stage1_feasibility as base
import run_redesign_stage_a as adapter
from inspect_simulator_workloads import inspect
from resume_stage1_two_workers import audit_capture
from snapshot_expansion_instrumentation import validate

ROOT, OUTPUT = base.ROOT, adapter.OUTPUT


def command(row,index):
    return ['nice','-n','19','ionice','-c','3','python3',str(ROOT/'scripts/run_redesign_stage_a.py'),
            '--candidate-id',row['candidate_id'],'--domain',str(100+index%2)]


def prepare():
    approval = dict(stage='A',authorized=True,attempts=144,plan_sha256=adapter.EXPECTED,
        user_statement='Approved',authority='User approval immediately following request for Stage A only',
        recorded_at=time.time(),primary_collection_authorized=False,protected_access_authorized=False,
        model_or_labels_approved=False,input_sha256={name:base.sha(ROOT/name) for name in
        ('configs/calibration_redesign_v2.yaml','docs/CALIBRATION_REDESIGN_AMENDMENT_20260923.md')})
    if not adapter.APPROVAL.exists():base.write(adapter.APPROVAL,approval)
    rows=adapter.assignments();validate(adapter.SNAPSHOT)
    OUTPUT.mkdir(exist_ok=False)
    sources=[adapter.PLAN,adapter.APPROVAL,adapter.SNAPSHOT,*[ROOT/'scripts'/name for name in
        ('execute_redesign_stage_a.py','run_redesign_stage_a.py','run_stage1_feasibility.py',
         'prepare_calibration_redesign.py','prepare_calibration_expansion.py','resume_stage1_two_workers.py',
         'inspect_simulator_workloads.py','snapshot_expansion_instrumentation.py')]]
    for row in rows:
        adapter.validate_row(row)
        sources.extend([ROOT/row['camera_profile'],ROOT/row['derivative_world_path']])
    base.write(OUTPUT/'source_binding.json',dict(input_sha256={str(p.relative_to(ROOT)):base.sha(p) for p in sources},
        core_snapshot_unchanged=True,scope='Stage A lighting adapter plus orchestration'))
    prepared=[]
    for i,row in enumerate(rows):
        result=subprocess.run(command(row,i)+['--prepare-only'],cwd=ROOT,capture_output=True,text=True,check=True)
        request=json.loads(result.stdout)
        if request['lighting_redesign']['world_sha256']!=base.sha(ROOT/row['derivative_world_path']):
            raise ValueError('prepared lighting binding')
        prepared.append(dict(candidate_id=row['candidate_id'],argv=command(row,i),request=request))
    base.write(OUTPUT/'execution_plan.json',dict(rows=prepared,retries=0,calibration_eligible=False))
    print('Prepared all 144 assignments',flush=True)


def summary():
    rows=adapter.assignments();counts={};bins={c:[0,0,0] for c in ('chair','doorway','laboratory_entrance','office_entrance')}
    results=[]
    for row in rows:
        path=OUTPUT/(row['candidate_id']+'.result.json')
        if not path.exists():continue
        result=json.loads(path.read_bytes());results.append(result)
        status=result['status'];counts[status]=counts.get(status,0)+1
        obs=result.get('selected_observation')
        if obs:
            p=obs['confidence'];bins[row['category']][0 if p<.5 else 1 if p<.8 else 2]+=1
    return dict(completed=len(results),scheduled=144,status_counts=counts,raw_confidence_bins=bins,
        automatic_feasibility_passed=len(results)==144 and all(n>=2 for b in bins.values() for n in b),
        calibration_eligible=False,human_labels_generated=False,results=results)


def execute():
    from physical_engineering_smoke import require_no_live_runner
    plan=json.loads((OUTPUT/'execution_plan.json').read_bytes());rows=adapter.assignments()
    if [(r['candidate_id'],r['argv']) for r in plan['rows']] != [(r['candidate_id'],command(r,i)) for i,r in enumerate(rows)]:
        raise ValueError('execution schedule changed')
    def monitored_external():
        adapter.validate_pins()
        return [r['pid'] for r in inspect()]
    base.other_simulators=monitored_external
    fd=os.open(ROOT/'reports/.research3_physical_execution.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);require_no_live_runner()
        batches=[plan['rows'][:1]]+[plan['rows'][i:i+2] for i in range(1,144,2)]
        for batch in batches:
            pending=[]
            for row in batch:
                name=row['candidate_id']
                if (OUTPUT/(name+'.result.json')).exists():continue
                if (OUTPUT/(name+'.start.json')).exists() or (ROOT/'reports/physical_live_episodes'/name).exists():
                    raise RuntimeError('interrupted attempt; retain and investigate, never replay')
                pending.append(row)
            if not pending:continue
            adapter.validate_pins();validate(adapter.SNAPSHOT)
            for _ in range(3):headroom=base.resource_gate();time.sleep(2)
            def worker(row):
                name=row['candidate_id'];started=time.time()
                base.write(OUTPUT/(name+'.start.json'),dict(started_at=started,resources=headroom,argv=row['argv']))
                try:
                    with (OUTPUT/(name+'.log')).open('x') as log:code=base.run_owned(row['argv'],log,fd)
                    if code:raise RuntimeError(f'runner exit {code}')
                    folder=ROOT/'reports/physical_live_episodes'/name
                    result=audit_capture(folder)
                    request=json.loads((folder/'request.json').read_bytes())
                    if request['lighting_redesign'] != row['request']['lighting_redesign']:
                        raise ValueError('actual lighting provenance mismatch')
                    if request['simulation_launch_argv'] != row['request']['simulation_launch_argv']:
                        raise ValueError('actual world/pose command mismatch')
                    adapter.validate_pins()
                except Exception as exc:result=dict(run_id=name,status='infrastructure_failure',error=str(exc))
                result.update(elapsed_s=time.time()-started,calibration_eligible=False)
                base.write(OUTPUT/(name+'.result.json'),result)
                return result
            with ThreadPoolExecutor(max_workers=2) as pool:outcomes=list(pool.map(worker,pending))
            print(json.dumps({k:v for k,v in summary().items() if k!='results'}),flush=True)
            if any(r['status']=='infrastructure_failure' for r in outcomes):
                raise RuntimeError('retained infrastructure failure; investigate before unstarted assignments')
        base.write(OUTPUT/'summary.json',summary())
    finally:os.close(fd)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--summary',action='store_true')
    args=p.parse_args()
    if args.summary:print(json.dumps(summary(),indent=2))
    elif args.execute:execute()
    else:prepare()
