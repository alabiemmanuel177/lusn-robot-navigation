"""Fixed, exploratory R3 distance × lighting interaction pilot; never calibration."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import fcntl
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import yaml
import run_stage1_feasibility as base
from language_nav.capture_view import validate_capture_pose
from prepare_calibration_redesign import lighting_variant
from resume_stage1_two_workers import audit_capture
from inspect_simulator_workloads import inspect
from snapshot_expansion_instrumentation import validate

ROOT=base.ROOT
OUTPUT=ROOT/'reports/distance_lighting_pilot_20260923_v1'
NEAR=ROOT/'reports/calibration_redesign_20260923_v1/plan.json'
FAR=ROOT/'reports/stage1_view_feasibility_20260921_v3.json'
SNAPSHOT=ROOT/'reports/expansion_instrumentation_snapshot_20260922_v8/snapshot.json'
PROTOCOL=ROOT/'docs/DISTANCE_LIGHTING_PILOT_20260923.md'
CLASSES=('chair','doorway','laboratory_entrance','office_entrance')


def build_rows():
    near=json.loads(NEAR.read_bytes());far=json.loads(FAR.read_bytes());rows=[]
    for world in far['maps']:
        number=world['map_number']
        if number not in (1,6):continue
        for target in world['targets']:
            reference=next(r for r in near['panels']['design_feasibility'] if r['map_id']==f'r3geo_base_r{number:03}'
                           and r['category']==target['category'] and r['source_view_index']==0)
            folder=ROOT/reference['world_directory']
            for name,digest in world['source_sha256'].items():
                if base.sha(folder/name)!=digest:raise ValueError('static source changed')
            scene=yaml.safe_load((folder/'landmark_scene.yaml').read_bytes())
            entity=next(e for e in scene['entities'] if e['entity_id']==target['entity_id'])
            if scene['partition']!='development':raise ValueError('development only')
            for fraction in (.5,1.):
                for index,far_view in enumerate(target['candidates']):
                    x,y=[reference['capture_pose'][k]+fraction*(far_view['pose'][k]-reference['capture_pose'][k]) for k in ('x','y')]
                    yaw=math.atan2(entity['pose']['y']-y,entity['pose']['x']-x)+far_view['yaw_offset_rad']
                    pose=validate_capture_pose(folder,x,y,yaw)
                    for scale in (1.,.9,.8):
                        light=f'light{round(scale*100):03}'
                        derivative=NEAR.parent/'worlds'/folder.name/light/'world.sdf'
                        if derivative.read_bytes()!=lighting_variant((folder/'world.sdf').read_bytes(),scale):
                            raise ValueError('nonlighting derivative change')
                        rows.append(dict(candidate_id=f'r3-dl-v1-r{number:03}-{target["category"]}-d{round(fraction*100)}-y{index}-{light}-s9',
                            partition='development',panel='design_feasibility',map_id=reference['map_id'],
                            category=target['category'],entity_id=entity['entity_id'],capture_pose=pose,
                            distance_fraction=fraction,yaw_offset_rad=far_view['yaw_offset_rad'],lighting_scale=scale,
                            simulator_seed=9,world_directory=reference['world_directory'],
                            camera_profile=reference['camera_profile'],camera_profile_sha256=reference['camera_profile_sha256'],
                            derivative_world_path=str(derivative.relative_to(ROOT)),world_sha256=base.sha(derivative),
                            calibration_eligible=False,human_verdict=None))
    random.Random(20260924).shuffle(rows)
    if len(rows)!=96 or len({r['candidate_id'] for r in rows})!=96:raise ValueError('fixed 96 assignments')
    return rows


def check_pins():
    binding=json.loads((OUTPUT/'source_binding.json').read_bytes())
    for name,digest in binding['input_sha256'].items():
        if base.sha(ROOT/name)!=digest:raise ValueError('pinned input changed: '+name)
    return binding


def rows():
    check_pins()
    plan=json.loads((OUTPUT/'plan.json').read_bytes())
    authority=json.loads((OUTPUT/'authority.json').read_bytes())
    if (authority.get('scope')!='development_design_only_distance_lighting_96'
            or authority.get('plan_sha256')!=base.sha(OUTPUT/'plan.json')
            or authority.get('primary_collection_authorized') is not False):raise PermissionError('scope authority')
    if plan['rows']!=build_rows():raise ValueError('exact schedule changed')
    return plan['rows']


def arguments(row,domain):
    if domain not in (100,101):raise ValueError('isolated domain')
    folder=ROOT/row['world_directory']
    return ['--world',str(folder),'--variant-id',folder.name+'-truthful_original-s0',
        '--run-id',row['candidate_id'],'--ros-domain-id',str(domain),'--simulation-seed','9',
        '--timeout','90','--capture-only','--capture-frame-budget','1',
        '--capture-pose',*[repr(row['capture_pose'][k]) for k in ('x','y','yaw')],
        '--capture-target-category',row['category'],'--capture-entity-id',row['entity_id'],
        '--camera-profile',str(ROOT/row['camera_profile']),'--camera-horizontal-fov','2.0',
        '--expansion-instrumentation-snapshot',str(SNAPSHOT)]


def command(row,index):
    return ['nice','-n','19','ionice','-c','3','python3',str(Path(__file__).resolve()),'episode',
            '--candidate-id',row['candidate_id'],'--domain',str(100+index%2)]


def prepare():
    validate(SNAPSHOT);schedule=build_rows();OUTPUT.mkdir(exist_ok=False)
    base.write(OUTPUT/'plan.json',dict(rows=schedule,scheduled=96,exploratory=True,
        protocol_sha256=base.sha(PROTOCOL),retries=0,calibration_eligible=False,protected_access=False))
    base.write(OUTPUT/'authority.json',dict(scope='development_design_only_distance_lighting_96',
        recorded_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        user_statement='Proceed and keep going, why do you keep stopping you know what next is there to do so keep fucking going',
        interpretation='Continue R3 design experimentation; not unseen scientific/model/primary approval',
        plan_sha256=base.sha(OUTPUT/'plan.json'),primary_collection_authorized=False,
        validation_release_authorized=False,protected_access_authorized=False,human_labels_generated=False))
    paths={Path(__file__).resolve(),PROTOCOL,NEAR,FAR,SNAPSHOT,OUTPUT/'plan.json',OUTPUT/'authority.json'}
    paths.update(ROOT/'scripts'/n for n in ('run_stage1_feasibility.py','prepare_calibration_redesign.py',
        'prepare_calibration_expansion.py','resume_stage1_two_workers.py','inspect_simulator_workloads.py',
        'snapshot_expansion_instrumentation.py','physical_engineering_smoke.py'))
    for row in schedule:
        paths.update((ROOT/row['world_directory']/n) for n in ('world.sdf','landmark_scene.yaml','manifest.json','map.yaml','map.pgm','execution_catalog.json'))
        paths.update([ROOT/row['camera_profile'],ROOT/row['derivative_world_path']])
    base.write(OUTPUT/'source_binding.json',dict(input_sha256={str(p.relative_to(ROOT)):base.sha(p) for p in paths}))
    prepared=[]
    for i,row in enumerate(schedule):
        result=subprocess.run(command(row,i)+['--prepare-only'],cwd=ROOT,capture_output=True,text=True,check=True,timeout=30)
        prepared.append(dict(candidate_id=row['candidate_id'],argv=command(row,i),request=json.loads(result.stdout)))
    base.write(OUTPUT/'execution_plan.json',dict(rows=prepared));print('96 requests prepared; no captures yet',flush=True)


def episode(args):
    row=next(r for r in rows() if r['candidate_id']==args.candidate_id)
    import run_physical_episode as runner
    original,old_argv=runner.physical_simulation_command,sys.argv
    def simulation(request,start):
        check_pins()
        request['diagnostic_world_sdf']=str(ROOT/row['derivative_world_path'])
        request['distance_lighting_pilot']=dict(plan_sha256=base.sha(OUTPUT/'plan.json'),
            source_binding_sha256=base.sha(OUTPUT/'source_binding.json'),world_sha256=row['world_sha256'],
            calibration_eligible=False,exploratory=True)
        return original(request,start)
    try:
        runner.physical_simulation_command=simulation
        sys.argv=[str(runner.__file__)]+arguments(row,args.domain)+(['--prepare-only'] if args.prepare_only else [])
        runner.main()
    finally:runner.physical_simulation_command,sys.argv=original,old_argv


def summarize():
    schedule=rows();results=[];counts={};bins={c:[0,0,0] for c in CLASSES}
    for row in schedule:
        path=OUTPUT/(row['candidate_id']+'.result.json')
        if not path.exists():continue
        result=json.loads(path.read_bytes());results.append(result)
        counts[result['status']]=counts.get(result['status'],0)+1
        obs=result.get('selected_observation')
        if obs:
            p=obs['confidence'];bins[row['category']][0 if p<.5 else 1 if p<.8 else 2]+=1
    return dict(completed=len(results),scheduled=96,status_counts=counts,raw_confidence_bins=bins,
        automatic_feasibility_passed=len(results)==96 and all(n>=2 for b in bins.values() for n in b),
        calibration_eligible=False,human_labels_generated=False,results=results)


def execute():
    from physical_engineering_smoke import require_no_live_runner
    schedule=rows();plan=json.loads((OUTPUT/'execution_plan.json').read_bytes())
    if [(r['candidate_id'],r['argv']) for r in plan['rows']]!=[(r['candidate_id'],command(r,i)) for i,r in enumerate(schedule)]:
        raise ValueError('commands changed')
    def external():check_pins();return [r['pid'] for r in inspect()]
    base.other_simulators=external
    fd=os.open(ROOT/'reports/.research3_physical_execution.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);require_no_live_runner()
        for batch in [plan['rows'][:1]]+[plan['rows'][i:i+2] for i in range(1,96,2)]:
            pending=[]
            for row in batch:
                name=row['candidate_id']
                if (OUTPUT/(name+'.result.json')).exists():continue
                if (OUTPUT/(name+'.start.json')).exists() or (ROOT/'reports/physical_live_episodes'/name).exists():
                    raise RuntimeError('interrupted attempt; retain, never replay')
                pending.append(row)
            if not pending:continue
            check_pins();validate(SNAPSHOT)
            for _ in range(3):headroom=base.resource_gate();time.sleep(2)
            def worker(row):
                name=row['candidate_id'];started=time.time()
                base.write(OUTPUT/(name+'.start.json'),dict(started_at=started,resources=headroom,argv=row['argv']))
                try:
                    with (OUTPUT/(name+'.log')).open('x') as log:code=base.run_owned(row['argv'],log,fd)
                    if code:raise RuntimeError(f'runner exit {code}')
                    folder=ROOT/'reports/physical_live_episodes'/name
                    result=audit_capture(folder);request=json.loads((folder/'request.json').read_bytes())
                    if request['distance_lighting_pilot']!=row['request']['distance_lighting_pilot'] or request['simulation_launch_argv']!=row['request']['simulation_launch_argv']:
                        raise ValueError('actual simulation binding differs')
                    obs=result.get('selected_observation');target=next(r for r in schedule if r['candidate_id']==name)
                    if obs and (obs['entity_id']!=target['entity_id'] or obs['category']!=target['category']):raise ValueError('wrong selected target')
                    check_pins()
                except Exception as exc:result=dict(run_id=name,status='infrastructure_failure',error=str(exc))
                result.update(elapsed_s=time.time()-started,calibration_eligible=False)
                base.write(OUTPUT/(name+'.result.json'),result);return result
            with ThreadPoolExecutor(max_workers=2) as pool:outcomes=list(pool.map(worker,pending))
            print(json.dumps({k:v for k,v in summarize().items() if k!='results'}),flush=True)
            if any(r['status']=='infrastructure_failure' for r in outcomes):raise RuntimeError('retain failure; investigate before unstarted work')
        base.write(OUTPUT/'summary.json',summarize())
    finally:os.close(fd)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('prepare','episode','execute','summary'))
    parser.add_argument('--candidate-id');parser.add_argument('--domain',type=int,choices=(100,101));parser.add_argument('--prepare-only',action='store_true')
    args=parser.parse_args()
    if args.action=='prepare':prepare()
    elif args.action=='episode':episode(args)
    elif args.action=='execute':execute()
    else:print(json.dumps({k:v for k,v in summarize().items() if k!='results'}))
