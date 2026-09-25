"""New fixed class-aware design pilot; explicitly reuse frozen capture mechanics."""
from contextlib import contextmanager
import argparse
import copy
import datetime as dt
import json
from pathlib import Path
import random
import subprocess
import distance_lighting_pilot as engine
from run_stage1_feasibility import ROOT,sha,write
from language_nav.capture_view import validate_capture_pose
from snapshot_expansion_instrumentation import validate

OUTPUT=ROOT/'reports/class_aware_acquisition_pilot_20260923_v1'
PROTOCOL=ROOT/'docs/CLASS_AWARE_ACQUISITION_PILOT_20260923.md'
DISTANCE_PLAN=ROOT/'reports/distance_lighting_pilot_20260923_v1/plan.json'
NEAR_PLAN=ROOT/'reports/calibration_redesign_20260923_v1/plan.json'
ORIGINAL_ARGUMENTS=engine.arguments


def build_rows():
    distance=json.loads(DISTANCE_PLAN.read_bytes())['rows']
    near=json.loads(NEAR_PLAN.read_bytes())['panels']['design_feasibility'];result=[]
    for source in distance:
        if source['category']=='doorway':continue
        row=copy.deepcopy(source);row['acquisition_family']='midpoint_far'
        row['candidate_id']=source['candidate_id'].replace('r3-dl-v1-','r3-ca-v1-').replace('-s9','-s17')
        row['simulator_seed']=17;result.append(row)
    for source in near:
        if source['category']!='doorway' or source['yaw_offset_rad']==0:continue
        row=copy.deepcopy(source);row['acquisition_family']='near_oblique';row['simulator_seed']=17
        number=int(source['map_id'][-3:]);yaw_index=0 if source['yaw_offset_rad']<0 else 1
        row['candidate_id']=f'r3-ca-v1-r{number:03}-doorway-v{source["source_view_index"]}-y{yaw_index}-light{round(source["lighting_scale"]*100):03}-s17'
        row['world_sha256']=sha(ROOT/row['derivative_world_path']);row['human_verdict']=None
        result.append(row)
    if len(result)!=96 or len({r['candidate_id'] for r in result})!=96:raise ValueError('fixed 96 unique assignments')
    for row in result:
        if row['map_id'] not in ('r3geo_base_r001','r3geo_base_r006') or row['partition']!='development' or row['calibration_eligible']:
            raise ValueError('design-only development scope')
        validate_capture_pose(ROOT/row['world_directory'],**row['capture_pose'])
        if sha(ROOT/row['camera_profile'])!=row['camera_profile_sha256']:raise ValueError('camera drift')
    random.Random(20260925).shuffle(result);return result


def check_pins():
    binding=json.loads((OUTPUT/'source_binding.json').read_bytes())
    for name,digest in binding['input_sha256'].items():
        if sha(ROOT/name)!=digest:raise ValueError('class-aware source/input changed: '+name)
    return binding


def rows():
    check_pins();plan=json.loads((OUTPUT/'plan.json').read_bytes());authority=json.loads((OUTPUT/'authority.json').read_bytes())
    if (authority['scope']!='development_design_only_class_aware_96'
            or authority['plan_sha256']!=sha(OUTPUT/'plan.json') or authority['primary_collection_authorized'] is not False):
        raise PermissionError('exact class-aware design scope required')
    if plan['rows']!=build_rows():raise ValueError('class-aware schedule changed')
    return plan['rows']


def arguments(row,domain):
    args=ORIGINAL_ARGUMENTS(row,domain)
    args[args.index('--simulation-seed')+1]='17'
    return args


def command(row,index):
    return ['nice','-n','19','ionice','-c','3','python3',str(Path(__file__).resolve()),'episode',
            '--candidate-id',row['candidate_id'],'--domain',str(100+index%2)]


@contextmanager
def bound_engine():
    bindings=dict(OUTPUT=OUTPUT,rows=rows,check_pins=check_pins,arguments=arguments,command=command)
    previous={key:getattr(engine,key) for key in bindings}
    try:
        for key,value in bindings.items():setattr(engine,key,value)
        yield engine
    finally:
        for key,value in previous.items():setattr(engine,key,value)


def prepare():
    validate(engine.SNAPSHOT);schedule=build_rows();OUTPUT.mkdir(exist_ok=False)
    write(OUTPUT/'plan.json',dict(rows=schedule,scheduled=96,exploratory=True,
        protocol_sha256=sha(PROTOCOL),retries=0,calibration_eligible=False,protected_access=False))
    write(OUTPUT/'authority.json',dict(scope='development_design_only_class_aware_96',
        recorded_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        user_statement='Proceed and keep going, why do you keep stopping you know what next is there to do so keep fucking going',
        interpretation='Continued exploratory acquisition design; no primary/model/validation authority',
        plan_sha256=sha(OUTPUT/'plan.json'),primary_collection_authorized=False,
        protected_access_authorized=False,validation_release_authorized=False,human_labels_generated=False))
    # Include all frozen mechanics and inputs from the preceding implementation,
    # then add the new source, protocol, plan and authority. No old binding edits.
    prior=json.loads((DISTANCE_PLAN.parent/'source_binding.json').read_bytes())['input_sha256']
    paths={ROOT/name for name in prior};paths.update([Path(__file__).resolve(),PROTOCOL,NEAR_PLAN,DISTANCE_PLAN,
        OUTPUT/'plan.json',OUTPUT/'authority.json'])
    write(OUTPUT/'source_binding.json',dict(input_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths}))
    prepared=[]
    for i,row in enumerate(schedule):
        response=subprocess.run(command(row,i)+['--prepare-only'],cwd=ROOT,capture_output=True,text=True,check=True,timeout=30)
        prepared.append(dict(candidate_id=row['candidate_id'],argv=command(row,i),request=json.loads(response.stdout)))
    write(OUTPUT/'execution_plan.json',dict(rows=prepared))
    print('96 class-aware assignments prepared; no captures yet',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','episode','execute','summary'))
    p.add_argument('--candidate-id');p.add_argument('--domain',type=int,choices=(100,101));p.add_argument('--prepare-only',action='store_true')
    args=p.parse_args()
    if args.action=='prepare':prepare()
    else:
        with bound_engine() as driver:
            if args.action=='episode':driver.episode(args)
            elif args.action=='execute':driver.execute()
            else:print(json.dumps({k:v for k,v in driver.summarize().items() if k!='results'}))
