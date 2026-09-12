#!/usr/bin/env python3
"""Prepare or explicitly execute bounded dev10 engineering checks, never a campaign."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import signal
import subprocess
from pathlib import Path

from language_nav.benchmark import CorruptionCondition
from language_nav.live_resources import coexistence_headroom, require_research2_idle

ROOT=Path(__file__).resolve().parents[1]
RUNNER=ROOT/'scripts/run_physical_episode.py'
PROFILE=ROOT/'reports/engineering_camera_settings_v1/profiles/base-r010.yaml'
RUNS=ROOT/'reports/physical_live_episodes'
REFERENCE=RUNS/'r3-readable-inspect-dev10-20260911-v2'
LOCK=ROOT/'reports/.research3_physical_execution.lock'


def live_runner_pids(proc_root=Path('/proc')):
    from language_nav.campaign_authorization import owned_physical_process
    found=[]
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            args=(entry/'cmdline').read_bytes().decode(errors='replace').split('\0')
        except FileNotFoundError:
            continue
        except PermissionError as exc:
            raise RuntimeError('cannot establish owned runner idleness') from exc
        if owned_physical_process(args, ROOT):
            found.append(int(entry.name))
    return sorted(found)


def require_no_live_runner():
    active=live_runner_pids()
    if active:
        raise RuntimeError(f'owned Research 3 live runner still exists: {active}; no dispatch')


def run_locked(command,env,log,lock_fd):
    # pass_fds preserves the locked open-file description through nice -> Python.
    # SIGTERM/SIGKILL of this parent cannot release the child's inherited lock.
    process=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT,
        cwd=ROOT,start_new_session=True,pass_fds=(lock_fd,))
    try:
        return process.wait(timeout=300)
    except BaseException:
        for sig,grace in ((signal.SIGINT,30),(signal.SIGTERM,15),(signal.SIGKILL,5)):
            if process.poll() is not None:
                break
            os.killpg(process.pid,sig)
            try:
                process.wait(timeout=grace)
                break
            except subprocess.TimeoutExpired:
                continue
        raise


def load_script(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def expected_cases():
    return [('B6',condition.value) for condition in CorruptionCondition
            if condition.value!='attribute_corruption']+[
                (system,'truthful_original') for system in ('B1','B2','B4','B5')]


def world_for(condition):
    directory='physical_absence_worlds_v1' if condition=='missing_landmark' else 'physical_worlds_readable_v1'
    return ROOT/'data'/directory/'base-r010'


def prepare_plan(output):
    output=Path(output)
    if output.exists():
        raise FileExistsError(output)
    runner=load_script('smoke_owned_runtime',RUNNER)
    reference=json.loads((REFERENCE/'summary.json').read_text())
    if (reference.get('partition')!='development'
            or reference.get('variant_id')!='base-r010-attribute_corruption-s0'
            or reference.get('system_id')!='B6'
            or reference.get('protected_test_routes_used') is not False):
        raise ValueError('attribute reference identity/scope mismatch')
    cases=[]
    for system,condition in expected_cases():
        run_id=f'r3-eng-smoke-dev10-{system.lower()}-{condition}-sim1-v1'
        request,_,_=runner.prepare(world_for(condition),f'base-r010-{condition}-s0',
                                  run_id,89,90.,1)
        cases.append({'system_id':system,'condition':condition,'run_id':run_id,
                      'request_preflight':request,'status':'planned_not_executed'})
    plan={'schema_version':'research3-physical-engineering-smoke/v1',
        'scope':'engineering_contract_verification_not_performance_or_confirmatory_campaign',
        'protected_data_used':False,'navigation_outcomes_inferred':False,
        'simulation_seed':1,'instruction_seed':0,'horizontal_fov':2.,'timeout_s':90,
        'ros_domain_id':89,'case_count':11,'cases':cases,
        'profile_path':str(PROFILE),'profile_sha256':digest(PROFILE),
        'runner_sha256':digest(RUNNER),
        'retained_attribute_reference':{'directory':str(REFERENCE),
            'condition':'attribute_corruption','system_id':'B6',
            'scope':'completed_inspection_and_safe_budget_abstention_not_task_success',
            'sha256':{name:digest(REFERENCE/name) for name in ('request.json','summary.json','measurements.json')}},
        'execution_policy':'serial_create_once_retain_failures_halt_infrastructure_or_unknown_measurements',
        'coexistence_override_default':False,
        'power_or_seed_adequacy_claimed':False,'full_campaign_completed':False}
    with output.open('x') as stream:
        json.dump(plan,stream,indent=2,sort_keys=True,allow_nan=False)
        stream.write('\n')
    return plan


def checked_command(plan,case,allow_coexistence,retry_id=None):
    if (plan.get('schema_version')!='research3-physical-engineering-smoke/v1'
            or plan.get('protected_data_used') is not False
            or plan.get('simulation_seed')!=1 or plan.get('horizontal_fov')!=2.
            or plan.get('timeout_s')!=90 or plan.get('ros_domain_id')!=89):
        raise ValueError('engineering scope/settings mismatch')
    if (case.get('system_id'),case.get('condition')) not in expected_cases():
        raise ValueError('case is outside the eleven predeclared development checks')
    system,condition=case['system_id'],case['condition']
    run_id=f'r3-eng-smoke-dev10-{system.lower()}-{condition}-sim1-v1'
    if case.get('run_id')!=run_id:
        raise ValueError('run identity mismatch')
    if retry_id is not None:
        if (not re.fullmatch(re.escape(run_id)+r'-retry-[A-Za-z0-9][A-Za-z0-9_-]*',retry_id)
                or len(retry_id)>96):
            raise ValueError('explicit retry ID must extend original ID with -retry- and a safe suffix')
        original=RUNS/run_id
        if not original.is_dir() or (original/'summary.json').exists():
            raise ValueError('retry requires an existing incomplete original; completed outcomes cannot be replaced')
        if (original/'failure.json').exists():
            failure=json.loads((original/'failure.json').read_text())
            if failure.get('error_type') not in {'KeyboardInterrupt','SystemExit','InterruptedError','TimeoutExpired'}:
                raise ValueError('retry not authorized for a non-interruption failure')
        run_id=retry_id
    if plan.get('profile_path')!=str(PROFILE) or digest(PROFILE)!=plan.get('profile_sha256'):
        raise ValueError('fixed engineering profile changed')
    if digest(RUNNER)!=plan.get('runner_sha256'):
        raise ValueError('runtime changed since engineering plan preparation')
    runner=load_script('smoke_runtime_preflight',RUNNER)
    request,_,_=runner.prepare(world_for(condition),f'base-r010-{condition}-s0',run_id,89,90.,1)
    previous=case['request_preflight']
    for key in ('partition','map_id','variant_id','asset_sha256','source_sha256','simulation_launch_argv'):
        if request.get(key)!=previous.get(key):
            raise ValueError('preflight identity/source/asset changed: '+key)
    if request['partition']!='development' or request['map_id']!='r3geo_base_r010':
        raise ValueError('only development dev10 is authorized')
    argv=['nice','-n','15','python3',str(RUNNER),'--world',str(world_for(condition)),
        '--variant-id',request['variant_id'],'--run-id',run_id,'--system-id',system,
        '--ros-domain-id','89','--timeout','90','--simulation-seed','1',
        '--camera-profile',str(PROFILE),'--camera-horizontal-fov','2.0',
        '--capture-perception']
    if allow_coexistence:
        argv.append('--allow-coexistence-trial')
    return argv


def execute_plan(path,output,allow_coexistence=False,case_ids=None,retries=None,max_cases=1):
    if type(max_cases) is not int or not 1<=max_cases<=11:
        raise ValueError('max_cases must be1..11; defaultone bounds external parent lifetime')
    fd=os.open(LOCK,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('Research 3 execution lock is held by a parent or surviving child') from exc
        require_no_live_runner()
        return _execute_locked(path,output,allow_coexistence,case_ids,retries or {},max_cases,fd)
    finally:
        # Do not LOCK_UN: closing only our descriptor preserves any child's lock.
        os.close(fd)


def _execute_locked(path,output,allow_coexistence,case_ids,retries,max_cases,lock_fd):
    path,output=Path(path),Path(output)
    if output.exists():
        raise FileExistsError(output)
    plan=json.loads(path.read_text())
    cases=plan.get('cases',[])
    if [(c.get('system_id'),c.get('condition')) for c in cases]!=expected_cases():
        raise ValueError('complete ordered eleven-case engineering matrix required')
    original_cases=cases
    original_ids={case['run_id'] for case in cases}
    if (case_ids and (len(case_ids)!=len(set(case_ids)) or not set(case_ids)<=original_ids)
            or not set(retries)<=original_ids):
        raise ValueError('case and retry references must belong to original eleven-case matrix')
    cases=[case for case in cases if not case_ids or case['run_id'] in case_ids]
    if any(key not in {case['run_id'] for case in cases} for key in retries):
        raise ValueError('retry must also belong to selected cases')
    if len(set(retries.values()))!=len(retries):
        raise ValueError('retry IDs must be unique')
    # Validate every command offline before creating any attempt or simulator.
    for case in cases:
        checked_command(plan,case,allow_coexistence,retries.get(case['run_id']))
    output.mkdir(parents=True,exist_ok=False)
    report={'schema_version':'research3-physical-engineering-smoke-execution/v1',
        'plan_sha256':digest(path),'scope':plan['scope'],'attempts':[],
        'halted':False,'protected_data_used':False,'full_campaign_completed':False,
        'allow_coexistence_trial':allow_coexistence}
    report.update(original_matrix_run_ids=[case['run_id'] for case in original_cases],
                  max_new_dispatches=max_cases,child_lifetime_lock=True,
                  historical_zero_overlap_claimed=False)
    dispatched=0
    env=dict(os.environ)
    env.update({name:'2' for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')})
    with (output/'attempts.jsonl').open('x') as journal:
        for case in cases:
            if dispatched>=max_cases:
                break
            actual_id=retries.get(case['run_id'],case['run_id'])
            directory=RUNS/actual_id
            row={key:case[key] for key in ('run_id','condition','system_id')}
            row.update(original_run_id=case['run_id'],run_id=actual_id,supplemental_retry=actual_id!=case['run_id'])
            try:
                if directory.exists():
                    row['status']='skipped_existing_not_relaunched_or_claimed_success'
                    if not (directory/'summary.json').exists():
                        raise RuntimeError('existing incomplete attempt retained; explicit distinct retry ID required')
                else:
                    require_no_live_runner()
                    command=checked_command(plan,case,allow_coexistence,retries.get(case['run_id']))
                    row['resource_preflight']=coexistence_headroom()
                    if not allow_coexistence:
                        require_research2_idle()
                    row['argv']=command
                    dispatched+=1
                    with (output/(actual_id+'.log')).open('x') as log:
                        code=run_locked(command,env,log,lock_fd)
                    row['returncode']=code
                    summary_path=directory/'summary.json'
                    if code!=0 or (directory/'failure.json').exists() or not summary_path.exists():
                        raise RuntimeError('runner failure, nonzero exit or missing summary; retained run requires audit')
                    summary=json.loads(summary_path.read_text())
                    row['summary']=summary
                    row['summary_sha256']=digest(summary_path)
                    if (summary.get('schema_version')!='research3-live-summary/v3'
                            or summary.get('run_id')!=actual_id
                            or summary.get('partition')!='development'
                            or summary.get('infrastructure_failure') is not False
                            or any(type(summary.get(key)) is not bool for key in ('collision','timeout','instruction_completion'))
                            or summary.get('trajectory_quality',{}).get('valid') is not True
                            or digest(directory/'measurements.json')!=summary.get('measurements_sha256')):
                        raise RuntimeError('infrastructure or unknown/unverifiable independent outcome')
                    row['status']='measured_engineering_outcome_retained_not_performance_claim'
            except BaseException as exc:
                row.update(status='halted_resource_infrastructure_or_unknown',error=str(exc),error_type=type(exc).__name__)
                report['halted']=True
            report['attempts'].append(row)
            journal.write(json.dumps(row,sort_keys=True)+'\n')
            journal.flush()
            if report['halted']:
                break
    report['not_attempted_count']=len(cases)-len(report['attempts'])
    with (output/'report.json').open('x') as stream:
        json.dump(report,stream,indent=2,sort_keys=True)
        stream.write('\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='mode',required=True)
    prepare=sub.add_parser('prepare')
    prepare.add_argument('--output',type=Path,required=True)
    run=sub.add_parser('run')
    run.add_argument('--plan',type=Path,required=True)
    run.add_argument('--output',type=Path,required=True)
    run.add_argument('--allow-coexistence-trial',action='store_true')
    run.add_argument('--case',dest='case_ids',action='append',help='original matrix run ID')
    run.add_argument('--retry',action='append',default=[],metavar='ORIGINAL_ID=NEW_RETRY_ID')
    run.add_argument('--max-cases',type=int,default=1,help='maximum new dispatches; bounded defaultone')
    args=parser.parse_args()
    if args.mode=='prepare':
        result=prepare_plan(args.output)
        print(f"Prepared {result['case_count']} engineering checks; no simulations launched")
    else:
        retries={}
        for value in args.retry:
            if '=' not in value:
                parser.error('--retry requires ORIGINAL_ID=NEW_RETRY_ID')
            original,new=value.split('=',1)
            if original in retries:
                parser.error('duplicate retry mapping')
            retries[original]=new
        result=execute_plan(args.plan,args.output,args.allow_coexistence_trial,args.case_ids,retries,args.max_cases)
        print(json.dumps({'halted':result['halted'],'recorded':len(result['attempts'])}))
        raise SystemExit(int(result['halted']))


if __name__=='__main__':
    main()
