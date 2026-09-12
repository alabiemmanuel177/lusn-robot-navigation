#!/usr/bin/env python3
"""Serial development or explicitly frozen validation stationary capture executor."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess

import yaml

from language_nav.capture_view import validate_capture_pose
from language_nav.camera_configuration import validate_camera_freeze, validate_frozen_capture_view, capture_source_snapshot
from language_nav.benchmark.physical_catalog import validate_physical_launch_inputs
from language_nav.live_resources import coexistence_headroom, require_research2_idle

ROOT=Path(__file__).resolve().parents[1]
RUNNER=ROOT/'scripts/run_physical_episode.py'
WORLDS=ROOT/'data/physical_worlds_readable_v1'
RUNS=ROOT/'reports/physical_live_episodes'
CATEGORIES={'chair','laboratory_entrance','office_entrance'}


def run_owned(command,env,log):
    """On interruption stop only this newly-created process group, never R2."""
    process=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT,
                             cwd=ROOT,start_new_session=True)
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


def checked_command(view,plan,plan_path,domain,timeout,allow_coexistence,validation=False):
    base=view.get('base_instruction_id','')
    partition='validation' if validation else 'development'
    pattern=r'base-r01[1-4]' if validation else r'base-r00[1-9]|base-r010'
    if not re.fullmatch(pattern,base) or view.get('partition')!=partition:
        raise ValueError('executor map/partition differs from explicit execution scope')
    category=view.get('category')
    if category not in CATEGORIES:
        raise ValueError('unexpected capture category')
    argv=view.get('command_argv')
    if not isinstance(argv,list) or len(argv)<2 or argv[0]!='python3' or Path(argv[1]).resolve()!=RUNNER.resolve():
        raise ValueError('plan executable/runner is not the owned capture runner')
    parser=argparse.ArgumentParser(add_help=False,exit_on_error=False)
    for flag in ('world','variant-id','run-id','ros-domain-id','simulation-seed','timeout',
                 'capture-frame-budget','camera-horizontal-fov','camera-profile','capture-target-category'):
        parser.add_argument('--'+flag,required=True)
    parser.add_argument('--capture-only',action='store_true')
    parser.add_argument('--camera-settings-freeze',required=validation)
    parser.add_argument('--capture-pose',nargs=3,type=float,required=True)
    if len([a for a in argv[2:] if a.startswith('--')]) != len(set(a for a in argv[2:] if a.startswith('--'))):
        raise ValueError('duplicate plan options rejected')
    try:
        args,extra=parser.parse_known_args(argv[2:])
    except (argparse.ArgumentError,SystemExit) as exc:
        raise ValueError('malformed capture command') from exc
    if extra:
        raise ValueError('unrecognized command options')
    world=WORLDS/base
    profile=plan_path.parent/'profiles'/f'{base}.yaml'
    run_id=view.get('run_id','')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,95}',run_id):
        raise ValueError('unsafe run ID')
    if (Path(args.world).resolve()!=world.resolve()
            or Path(args.camera_profile).resolve()!=profile.resolve()
            or not profile.resolve().is_relative_to(plan_path.parent.resolve())
            or args.run_id!=run_id or args.variant_id!=base+'-truthful_original-s0'
            or args.capture_target_category!=category or not args.capture_only
            or args.capture_frame_budget!='1' or args.simulation_seed!='1'
            or float(args.camera_horizontal_fov)!=2.):
        raise ValueError('plan scope or capture parameters mismatch')
    if validation:
        freeze=plan_path.parent/'camera_settings_freeze.json'
        if (Path(args.camera_settings_freeze).resolve()!=freeze.resolve()
                or not freeze.resolve().is_relative_to(plan_path.parent.resolve())):
            raise ValueError('validation requires the owned matching camera settings freeze')
        validate_camera_freeze(freeze,map_id='r3geo_'+base.replace('-','_'),
                               profile=profile,horizontal_fov=2.0)
        validate_physical_launch_inputs(world/'execution_catalog.json',world/'landmark_scene.yaml',world/'map.yaml')
    else:
        if args.camera_settings_freeze is not None:
            raise ValueError('freeze override requires explicit validation execution scope')
        for name in ('world.sdf','execution_catalog.json','landmark_scene.yaml','map.pgm'):
            if hashlib.sha256((world/name).read_bytes()).hexdigest()!=plan['source_sha256'][base][name]:
                raise ValueError('planned asset changed: '+name)
    pose=validate_capture_pose(world,*args.capture_pose)
    if validation:
        validate_frozen_capture_view(freeze,map_id='r3geo_'+base.replace('-','_'),
                                     category=category,pose=pose,world=world)
    if not validation and pose!=view.get('capture_pose'):
        raise ValueError('capture pose does not match plan')
    settings=yaml.safe_load(profile.read_text())
    if (settings.get('partition_scope')!=[partition]
            or settings.get('map_scope')!=['r3geo_'+base.replace('-','_')]
            or settings.get('confidence_calibration_validated') is not False):
        raise ValueError('profile is not map-scoped engineering input for requested partition')
    command=['nice','-n','15','python3',str(RUNNER),'--world',str(world),
        '--variant-id',args.variant_id,'--run-id',run_id,'--ros-domain-id',str(domain),
        '--simulation-seed','1','--timeout',str(timeout),'--capture-only',
        '--capture-frame-budget','1','--capture-pose',*[str(v) for v in args.capture_pose],
        '--camera-horizontal-fov','2.0','--camera-profile',str(profile),
        '--capture-target-category',category]
    if validation:
        command.extend(['--camera-settings-freeze',str(freeze)])
    if allow_coexistence:
        command.append('--allow-coexistence-trial')
    return command


def execute_plan(plan_path,output,maps=None,categories=None,domain=89,timeout=25,
                 allow_coexistence=False,validation=False):
    plan_path,output=Path(plan_path).resolve(),Path(output)
    if output.exists():
        raise FileExistsError(output)
    if type(domain) is not int or not 1<=domain<=101 or type(timeout) is not int or not 1<=timeout<=120:
        raise ValueError('domain must be 1..101; capture timeout must be 1..120 seconds')
    pattern=r'base-r01[1-4]' if validation else r'base-r00[1-9]|base-r010'
    if maps and any(not re.fullmatch(pattern,base) for base in maps):
        raise ValueError('map filters must match explicit nonprotected execution scope')
    if categories and not set(categories)<=CATEGORIES:
        raise ValueError('invalid category filter')
    raw=plan_path.read_bytes()
    plan=json.loads(raw)
    schema=('research3-frozen-camera-validation-commands/v1' if validation
            else 'research3-stationary-capture-plan/v1')
    protected_key='protected_content_used' if validation else 'protected_content_read'
    if plan.get('schema_version')!=schema or plan.get(protected_key) is not False:
        raise ValueError('unexpected capture plan schema/scope')
    views=([{**view,'partition':'validation'} for view in plan['commands']] if validation else plan['views'])
    partition='validation' if validation else 'development'
    selected=[v for v in views if v.get('partition')==partition
              and (not maps or v['base_instruction_id'] in maps)
              and (not categories or v['category'] in categories)]
    if not selected or len({v['run_id'] for v in selected})!=len(selected):
        raise ValueError('empty selection or duplicate run IDs')
    commands=[checked_command(v,plan,plan_path,domain,timeout,allow_coexistence,validation) for v in selected]
    freeze_path=plan_path.parent/'camera_settings_freeze.json'
    freeze_sha256=hashlib.sha256(freeze_path.read_bytes()).hexdigest() if validation else None
    output.mkdir(parents=True,exist_ok=False)
    report={'schema_version':'research3-stationary-serial-execution/v1',
        'plan_sha256':hashlib.sha256(raw).hexdigest(),
        'runner_sha256':hashlib.sha256(RUNNER.read_bytes()).hexdigest(),
        'allow_coexistence_trial':allow_coexistence,'selected_count':len(selected),
        'partition':partition,'camera_settings_freeze_sha256':freeze_sha256,
        'domain_id':domain,'capture_timeout_s':timeout,'attempts':[],
        'halted':False,'human_labels_generated':False,'navigation_success_claimed':False}
    report['source_sha256']=capture_source_snapshot()
    env=dict(os.environ)
    env.update({name:'2' for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS',
                                    'MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')})
    with (output/'attempts.jsonl').open('x') as journal:
        for view,command in zip(selected,commands):
            run_id=view['run_id']
            row={'run_id':run_id,'category':view['category'],'base_instruction_id':view['base_instruction_id']}
            directory=RUNS/run_id
            try:
                if directory.exists():
                    row['status']='skipped_existing_not_relaunched_or_claimed_success'
                else:
                    if capture_source_snapshot()!=report['source_sha256']:
                        raise ValueError('capture source snapshot changed during serial execution')
                    if validation:
                        if hashlib.sha256(freeze_path.read_bytes()).hexdigest()!=freeze_sha256:
                            raise ValueError('engineering camera freeze changed during serial execution')
                        checked_command(view,plan,plan_path,domain,timeout,allow_coexistence,True)
                    row['resource_preflight']=coexistence_headroom()
                    if not allow_coexistence:
                        require_research2_idle()
                    row['argv']=command
                    with (output/f'{run_id}.log').open('x') as log:
                        returncode=run_owned(command,env,log)
                    row['returncode']=returncode
                    failure=directory/'failure.json'
                    summary=directory/'capture_summary.json'
                    if failure.exists():
                        row['failure']=json.loads(failure.read_text())
                        row['status']='halted_resource_or_infrastructure_failure'
                        report['halted']=True
                    elif returncode!=0 or not summary.exists():
                        row['status']='halted_nonzero_exit_or_missing_evidence'
                        report['halted']=True
                    else:
                        measured=json.loads(summary.read_text())
                        row['capture_summary']=measured
                        if (measured.get('run_id')!=run_id
                                or measured.get('schema_version')!='research3-stationary-capture/v1'
                                or measured.get('collision_count')!=0):
                            row['status']='halted_invalid_or_unsafe_capture_evidence'
                            report['halted']=True
                        else:
                            row['status']=('capture_complete_not_human_reviewed' if measured.get('complete') is True
                                           else 'capture_incomplete_retained_no_automatic_replacement')
            except BaseException as exc:
                row.update(status='halted_preflight_or_infrastructure_exception',
                           error_type=type(exc).__name__,error=str(exc))
                report['halted']=True
            report['attempts'].append(row)
            journal.write(json.dumps(row,sort_keys=True)+'\n')
            journal.flush()
            if report['halted']:
                break
    report['not_attempted_count']=len(selected)-len(report['attempts'])
    with (output/'report.json').open('x') as stream:
        json.dump(report,stream,indent=2,sort_keys=True)
        stream.write('\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--map',action='append',dest='maps')
    parser.add_argument('--category',action='append',choices=sorted(CATEGORIES),dest='categories')
    parser.add_argument('--ros-domain-id',type=int,default=89)
    parser.add_argument('--timeout',type=int,default=25)
    parser.add_argument('--allow-coexistence-trial',action='store_true')
    parser.add_argument('--validation',action='store_true',
                        help='explicit stationary validation scope; matching engineering freeze mandatory')
    args=parser.parse_args()
    result=execute_plan(args.plan,args.output,args.maps,args.categories,args.ros_domain_id,
                        args.timeout,args.allow_coexistence_trial,args.validation)
    print(json.dumps({'halted':result['halted'],'recorded':len(result['attempts']),
                      'not_attempted':result['not_attempted_count']}))
    raise SystemExit(1 if result['halted'] else 0)


if __name__=='__main__':
    main()
