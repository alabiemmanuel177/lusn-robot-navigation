#!/usr/bin/env python3
"""Create-once engineering stationary capture plan; no ROS/Gazebo execution."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re

import yaml

from language_nav.benchmark.physical_catalog import validate_physical_launch_inputs
from language_nav.capture_view import validate_capture_pose

ROOT = Path(__file__).resolve().parents[1]
CHAIRS = {'blue':[45,60,107], 'red':[107,45,45],
          'green':[45,95,60], 'yellow':[110,101,45]}
SHARED = {'doorway':[78,44,87], 'laboratory_entrance':[92,42,76],
          'office_entrance':[39,90,79]}
PROVIDER = '3821eee3392dbfb6f99452e11233835f03c63c0a'


def prepare_plan(worlds: Path, output: Path, domain: int = 91,
                 run_prefix: str = 'r3-stationary-draft-v1',
                 runner: Path = ROOT/'scripts/run_physical_episode.py') -> dict:
    if output.exists():
        raise FileExistsError(output)
    if type(domain) is not int or not 1 <= domain <= 101:
        raise ValueError('isolated ROS domain must be an integer between 1 and 101')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,50}', run_prefix):
        raise ValueError('run prefix must be a short safe ID')
    runner_source = runner.read_text()
    target_supported = bool(re.search(
        r"add_argument\(['\"]--capture-target-category['\"]", runner_source))
    profiles, views, hashes = {}, [], {}
    for index in range(1,15):
        base = f'base-r{index:03}'
        world = worlds/base
        runtime = validate_physical_launch_inputs(world/'execution_catalog.json',
            world/'landmark_scene.yaml',world/'map.yaml')
        scene = yaml.safe_load((world/'landmark_scene.yaml').read_text())
        partition = 'development' if index <= 10 else 'validation'
        if runtime.semantic.partition != partition:
            raise ValueError('non-protected split mismatch')
        chairs = [e for e in scene['entities'] if e['category']=='chair']
        if len(chairs) != 1:
            raise ValueError('expected exactly one existing chair')
        chair = chairs[0]
        color = chair['attributes']['color']
        profile = {
            'schema_version':'landmark-capture-profile/v1',
            'profile_id':f'{base}-stationary-predicted-palette-draft-v1',
            'provider_revision':PROVIDER,
            'partition_scope':['development'] if partition=='development' else [],
            'map_scope':[runtime.semantic.map_id],
            'purpose':'engineering_predicted_palette_not_confidence_calibration',
            'human_labels_generated':False, 'color_tolerance':10.0,
            'camera_palette':{f'chair:color={color}':CHAIRS[color], **SHARED},
            'chair_prototype_status':'predicted_unvalidated_in_this_world',
            'confidence_calibration_validated':False,
            'validation_capture_gate':'development_capture_validation_required_before_validation_use',
        }
        profiles[base] = profile
        hashes[base] = {name:hashlib.sha256((world/name).read_bytes()).hexdigest()
                       for name in ('world.sdf','execution_catalog.json','landmark_scene.yaml','map.pgm')}
        chair_pose = (1.15,-.30,math.atan2(chair['pose']['y']+.30,chair['pose']['x']-1.15))
        selected = [('chair',chair,chair_pose)]
        # Category-based view selection only, not expected-route/evaluator access.
        for category in ('laboratory_entrance','office_entrance'):
            candidates = [e for e in scene['entities'] if e['category']==category]
            entity = max(candidates,key=lambda e:e['pose']['x'])
            side = 1 if entity['pose']['y']>0 else -1
            doorway_x = next(route.goal.x for route in runtime.execution
                             if route.route_id in entity['route_ids'])
            selected.append((category,entity,(doorway_x,
                            -side*.6,side*math.pi/2)))
        for category,entity,coordinates in selected:
            pose = validate_capture_pose(world,*coordinates)
            run_id = f'{run_prefix}-r{index:03}-{category}'
            command = None
            if partition == 'development':
                command = ['python3',str(runner.resolve()),'--world',str(world.resolve()),
                    '--variant-id',f'{base}-truthful_original-s0','--run-id',run_id,
                    '--ros-domain-id',str(domain),'--simulation-seed','1',
                    '--timeout','90','--capture-only','--capture-frame-budget','1',
                    '--capture-pose',str(pose['x']),str(pose['y']),str(pose['yaw']),
                    '--camera-horizontal-fov','2.0',
                    '--camera-profile',str((output/'profiles'/f'{base}.yaml').resolve())]
                if target_supported:
                    command += ['--capture-target-category',category]
            views.append({
                'base_instruction_id':base,'partition':partition,'category':category,
                'intended_entity_id':entity['entity_id'],'capture_pose':pose,
                'pose_occupancy_validated':True,'frame_budget':1,
                'full_context_retained':True,'horizontal_fov_rad':2.0,
                'category_targeting_supported':target_supported,'run_id':run_id,
                'command_argv':command,
                'execution_gate':('resource_guard_then_development_engineering_capture'
                    if partition=='development' else
                    'blocked_until_development_validation_and_validation_FOV_profile_authorization'),
                'label_status':'pending_genuine_human_review',
                'visibility_and_detector_success_guaranteed':False,
            })
    plan = {'schema_version':'research3-stationary-capture-plan/v1',
        'status':'engineering_draft_not_calibration_or_protocol_freeze',
        'protected_content_read':False,'simulation_launched':False,
        'view_count':len(views),'development_view_count':30,'validation_gated_view_count':12,
        'execution_mode':'serial_one_R3_capture_at_a_time_with_Research2_resource_guard',
        'coexistence_override_included':False,
        'source_sha256':hashes,'runner_sha256':hashlib.sha256(runner_source.encode()).hexdigest(),
        'review_policy':'retain_full_frames_and_all_failures_never_generate_human_verdicts',
        'calibration_coverage_claimed':False,'views':views}
    output.mkdir(parents=True,exist_ok=False)
    (output/'profiles').mkdir()
    for base,profile in profiles.items():
        with (output/'profiles'/f'{base}.yaml').open('x') as stream:
            yaml.safe_dump(profile,stream,sort_keys=False)
    with (output/'plan.json').open('x') as stream:
        json.dump(plan,stream,indent=2,sort_keys=True,allow_nan=False)
        stream.write('\n')
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worlds',type=Path,default=ROOT/'data/physical_worlds_readable_v1')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--ros-domain-id',type=int,default=91)
    parser.add_argument('--run-prefix',default='r3-stationary-draft-v1')
    args=parser.parse_args()
    plan=prepare_plan(args.worlds,args.output,args.ros_domain_id,args.run_prefix)
    print(f"Prepared {plan['view_count']} views:30 development,12 gated validation; no simulation")


if __name__=='__main__':
    main()
