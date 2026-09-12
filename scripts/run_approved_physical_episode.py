#!/usr/bin/env python3
"""Execute one separately approved non-protected campaign episode.

Engineering CLI permissions remain unchanged. This wrapper does not authorize
held-out runs or turn a stationary settings freeze into campaign approval.
"""
import argparse
import importlib.util
import json
import math
from pathlib import Path

import yaml

from language_nav.adapters.landmark_palette import adapt_scene_palette
from language_nav.benchmark.physical_catalog import validate_physical_launch_inputs
from language_nav.campaign_authorization import (ROOT,sha,validate_campaign_episode,
                                                exclusive_campaign_runtime)
from language_nav.live_resources import require_research2_idle,coexistence_headroom


def runtime_module():
    path=ROOT/'scripts/run_physical_episode.py'
    spec=importlib.util.spec_from_file_location('approved_existing_runtime',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare_approved(supplied):
    binding=validate_campaign_episode(supplied)
    runtime=runtime_module()
    request,variant,catalog=runtime.prepare(Path(supplied['world']),supplied['variant_id'],
        supplied['run_id'],int(supplied['ros_domain_id']),float(supplied['timeout']),int(supplied['simulation_seed']))
    if request['partition']!=binding['partition'] or request['run_id']!=binding['run_id']:
        raise ValueError('runtime request differs from approved episode')
    request.update(system_id=supplied['system_id'],campaign_authorization=binding,
        evidence_scope='approved_nonprotected_comparative_campaign_episode',
        capture_only=False,capture_perception=False,capture_review=False,capture_context=False,
        capture_frame_budget=5,capture_target_categories=None,context_sampling=None,
        allow_coexistence_trial=False,calibration_sha256=sha(supplied['calibration']))
    if supplied.get('camera_profile') is not None:
        profile=Path(supplied['camera_profile'])
        settings=yaml.safe_load(profile.read_text())
        if request['partition'] not in settings.get('partition_scope',[]) or request['map_id'] not in settings.get('map_scope',[]):
            raise ValueError('approved profile does not cover actual runtime map/partition')
        request['camera_profile_sha256']=sha(profile)
        request['camera_color_tolerance']=float(settings['color_tolerance'])
        if not math.isfinite(request['camera_color_tolerance']) or request['camera_color_tolerance']<=0:
            raise ValueError('approved camera tolerance must remain finite and positive')
    if supplied.get('camera_horizontal_fov') is not None:
        request['camera_horizontal_fov']=float(supplied['camera_horizontal_fov'])
    start=catalog.execution[0].start
    request['simulation_launch_argv']=runtime.physical_simulation_command(request,dict(x=start.x,y=start.y,yaw=start.yaw))
    for name in ('scripts/run_approved_physical_episode.py','src/language_nav/campaign_authorization.py'):
        request['source_sha256'][name]=sha(ROOT/name)
    return runtime,request,variant,catalog


def execute_approved(supplied):
    with exclusive_campaign_runtime():
        require_research2_idle()
        coexistence_headroom()
        runtime,request,variant,catalog=prepare_approved(supplied)
        output=ROOT/'reports/physical_live_episodes'/request['run_id']
        output.mkdir(parents=True,exist_ok=False)
        try:
            if supplied.get('camera_profile') is not None:
                scene=output/'runtime_scene.yaml'
                adapt_scene_palette(Path(supplied['world'])/'landmark_scene.yaml',scene,Path(supplied['camera_profile']))
                validate_physical_launch_inputs(Path(supplied['world'])/'execution_catalog.json',scene)
                request.update(runtime_scene=str(scene),runtime_scene_sha256=sha(scene))
            runtime.write_once(output/'request.json',request)
            runtime.execute(request,variant,catalog,output,supplied['system_id'],Path(supplied['calibration']))
        except BaseException as exc:
            if not (output/'request.json').exists():
                runtime.write_once(output/'request.json',request)
            if not (output/'failure.json').exists():
                runtime.write_once(output/'failure.json',dict(error=str(exc),error_type=type(exc).__name__,
                    retry_policy='retain failure; no automatic replacement',execution_or_dispatch_not_inferred=True))
            raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('world','variant-id','run-id','system-id','calibration','campaign-authorization',
                 'campaign-manifest','campaign-episode-id'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--ros-domain-id',type=int,required=True)
    parser.add_argument('--simulation-seed',type=int,required=True)
    parser.add_argument('--timeout',type=float,required=True)
    parser.add_argument('--camera-profile')
    parser.add_argument('--camera-horizontal-fov',type=float)
    parser.add_argument('--prepare-only',action='store_true')
    options=vars(parser.parse_args())
    prepare_only=options.pop('prepare_only')
    if prepare_only:
        _,request,_,_=prepare_approved(options)
        print(json.dumps(request,indent=2,sort_keys=True,allow_nan=False))
    else:
        execute_approved(options)


if __name__=='__main__':
    main()
