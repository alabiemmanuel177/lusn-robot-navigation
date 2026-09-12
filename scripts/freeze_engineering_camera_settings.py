#!/usr/bin/env python3
"""Freeze engineering camera settings from explicit development visual checks.

This does not label detections, calibrate confidence or freeze a study protocol.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import yaml

from language_nav.camera_configuration import validate_camera_freeze, capture_source_snapshot
from language_nav.capture_view import validate_capture_pose

ROOT=Path(__file__).resolve().parents[1]
RUNS=ROOT/'reports/physical_live_episodes'
RUNNER=ROOT/'scripts/run_physical_episode.py'
WORLDS=ROOT/'data/physical_worlds_readable_v1'
REQUIRED_FILES=('request.json','perception_capture/frame-000.json',
                'perception_capture/frame-000-rgb.bin')
PALETTES={'red':[107,45,45],'blue':[45,60,107],'green':[45,95,60],'yellow':[110,101,45]}
SHARED={'doorway':[78,44,87],'laboratory_entrance':[92,42,76],'office_entrance':[39,90,79]}


def freeze(plan_path,output,evidence_runs,*,development_visual_check_complete=False):
    plan_path,output=Path(plan_path).resolve(),Path(output).resolve()
    if not development_visual_check_complete:
        raise ValueError('explicit caller development visual-check attestation required')
    if output.exists():
        raise FileExistsError(output)
    directories=[Path(path).resolve() for path in evidence_runs]
    if len(directories)!=6 or len(set(directories))!=6:
        raise ValueError('exactly six distinct explicit development runs required')
    evidence=[]
    counts=Counter()
    for directory in directories:
        if directory.parent!=RUNS.resolve():
            raise ValueError('evidence run must belong to owned physical-live reports')
        request=json.loads((directory/'request.json').read_text())
        if (request.get('partition')!='development' or request.get('protected_test_routes_used') is not False
                or request.get('map_id') not in {f'r3geo_base_r{i:03}' for i in range(1,11)}
                or request.get('capture_only') is not True or request.get('camera_horizontal_fov')!=2.0):
            raise ValueError('evidence must be development stationary FOV2 capture')
        counts[request['map_id']]+=1
        hashes={}
        for name in REQUIRED_FILES:
            path=(directory/name).resolve()
            if not path.is_relative_to(directory) or not path.is_file():
                raise ValueError('missing/escaping development evidence file')
            raw=path.read_bytes()
            if not raw:
                raise ValueError('empty development evidence file')
            hashes[name]=hashlib.sha256(raw).hexdigest()
        evidence.append({'run_directory':str(directory),'map_id':request['map_id'],'sha256':hashes})
    if counts!=Counter({'r3geo_base_r001':1,'r3geo_base_r002':1,'r3geo_base_r003':1,
                        'r3geo_base_r004':1,'r3geo_base_r010':2}):
        raise ValueError('evidence must cover four chair-color worlds and two dev10 sign views')
    raw_plan=plan_path.read_bytes()
    plan=json.loads(raw_plan)
    if plan.get('schema_version')!='research3-stationary-capture-plan/v1' or plan.get('protected_content_read') is not False:
        raise ValueError('unsupported/nonprotected capture plan required')
    profiles={}
    for i in range(1,15):
        base=f'base-r{i:03}'
        profile=yaml.safe_load((plan_path.parent/'profiles'/f'{base}.yaml').read_text())
        palette=profile.get('camera_palette',{})
        chairs={key:value for key,value in palette.items() if key.startswith('chair:color=')}
        if (len(chairs)!=1 or any(value!=PALETTES.get(key.split('=')[-1]) for key,value in chairs.items())
                or {key:value for key,value in palette.items() if key not in chairs}!=SHARED
                or profile.get('color_tolerance')!=10.0
                or profile.get('map_scope')!=['r3geo_'+base.replace('-','_')]):
            raise ValueError('profile differs from explicitly reviewed engineering palette')
        profile['partition_scope']=['development' if i<=10 else 'validation']
        profile['purpose']='frozen_engineering_camera_settings_not_confidence_calibration'
        profile['engineering_configuration_frozen']=True
        profile['chair_prototype_status']='development_visual_settings_checked_not_per_map_detector_validation'
        profile['validation_capture_gate']='requires_matching_engineering_camera_freeze'
        profiles[base]=yaml.safe_dump(profile,sort_keys=False).encode()
    freeze_payload={'schema_version':'research3-engineering-camera-freeze/v2',
        'protected_data_used':False,'confidence_calibration_frozen':False,'human_labels_generated':False,
        'purpose':'engineering_camera_settings_only_not_confidence_calibration_or_experiment_protocol',
        'horizontal_fov':2.0,'color_tolerance':10.0,
        'visual_check_attestation':{'development_visual_check_complete':True,
            'source':'explicit_caller_attestation_not_automatic_QA_or_human_detection_verdict'},
        'development_evidence':evidence,
        'source_capture_plan_sha256':hashlib.sha256(raw_plan).hexdigest(),
        'source_sha256':capture_source_snapshot(), 'validation_views':[],
        'profiles':{'r3geo_'+base.replace('-','_'):hashlib.sha256(raw).hexdigest()
                    for base,raw in profiles.items()},
        'limitations':['no_per_map_detector_accuracy_claim','no_confidence_calibration',
                      'no_human_correct_incorrect_labels','no_heldout_or_confirmatory_protocol_freeze']}
    freeze_path=output/'camera_settings_freeze.json'
    commands=[]
    for view in plan['views']:
        if view.get('partition')!='validation':
            continue
        base=view['base_instruction_id']
        if base not in {f'base-r{i:03}' for i in range(11,15)}:
            raise ValueError('validation view must be one of four nonprotected maps')
        category=view['category']
        if category not in {'chair','laboratory_entrance','office_entrance'}:
            raise ValueError('unsupported validation target category')
        pose=view['capture_pose']
        world=WORLDS/base
        validate_capture_pose(world,pose['x'],pose['y'],pose['yaw'])
        freeze_payload['validation_views'].append({'map_id':'r3geo_'+base.replace('-','_'),
            'category':category,'capture_pose':pose,
            'world_sha256':{name:hashlib.sha256((world/name).read_bytes()).hexdigest()
                for name in ('world.sdf','execution_catalog.json','landmark_scene.yaml','map.pgm','map.yaml')}})
        argv=['python3',str(RUNNER),'--world',str(world),
            '--variant-id',base+'-truthful_original-s0','--run-id',view['run_id'],
            '--ros-domain-id','89','--timeout','25','--simulation-seed','1',
            '--capture-only','--capture-frame-budget','1','--capture-target-category',category,
            '--capture-pose',str(pose['x']),str(pose['y']),str(pose['yaw']),
            '--camera-horizontal-fov','2.0','--camera-profile',str(output/'profiles'/f'{base}.yaml'),
            '--camera-settings-freeze',str(freeze_path)]
        commands.append({'base_instruction_id':base,'category':category,'run_id':view['run_id'],
                         'command_argv':argv,'confidence_calibration_claimed':False})
    if len(commands)!=12 or len({(row['base_instruction_id'],row['category']) for row in commands})!=12:
        raise ValueError('exactly twelve distinct validation views required')
    output.mkdir(parents=True,exist_ok=False)
    (output/'profiles').mkdir()
    for base,raw in profiles.items():
        with (output/'profiles'/f'{base}.yaml').open('xb') as stream:
            stream.write(raw)
    with freeze_path.open('x') as stream:
        json.dump(freeze_payload,stream,indent=2,sort_keys=True)
        stream.write('\n')
    for base in profiles:
        validate_camera_freeze(freeze_path,map_id='r3geo_'+base.replace('-','_'),
            profile=output/'profiles'/f'{base}.yaml',horizontal_fov=2.0)
    with (output/'validation_commands.json').open('x') as stream:
        json.dump({'schema_version':'research3-frozen-camera-validation-commands/v1',
                   'protected_content_used':False,'simulation_launched':False,
                   'coexistence_override_included':False,'commands':commands},stream,indent=2,sort_keys=True)
        stream.write('\n')
    return freeze_payload,commands


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--evidence-run',type=Path,action='append',required=True)
    parser.add_argument('--development-visual-check-complete',action='store_true')
    args=parser.parse_args()
    _,commands=freeze(args.plan,args.output,args.evidence_run,
        development_visual_check_complete=args.development_visual_check_complete)
    print(f'Engineering settings only:14 profiles,6 development evidence runs,{len(commands)} validation commands; no labels/live runs')


if __name__=='__main__':
    main()
