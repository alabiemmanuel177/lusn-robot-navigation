"""Offline development-map screening; no visibility, outcome or execution claims."""
import argparse
import concurrent.futures
import hashlib
import json
import math
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def clear_ray(pixels, origin, resolution, camera, target):
    """2-D map proxy only; omit the final 0.15 m around the target reference."""
    distance=math.dist(camera,target)
    if distance<=.6:return False
    steps=max(2,math.ceil(distance/(resolution/2)))
    for index in range(steps):
        fraction=index/steps
        if distance*(1-fraction)<.15:break
        x=camera[0]+fraction*(target[0]-camera[0]);y=camera[1]+fraction*(target[1]-camera[1])
        col=math.floor((x-origin[0])/resolution);row=pixels.shape[0]-1-math.floor((y-origin[1])/resolution)
        if not (0<=row<pixels.shape[0] and 0<=col<pixels.shape[1]) or pixels[row,col]<200:return False
    return True


def wall_ray_clear(walls,camera,target):
    """Analytic segment/axis-aligned wall boxes; not object visibility."""
    distance=math.dist(camera,target)
    if distance<=.6:return False
    end=[camera[i]+(target[i]-camera[i])*(1-.15/distance) for i in (0,1)]
    for wall in walls:
        low,high=0.,1.
        for i,axis in enumerate(('x','y')):
            delta=end[i]-camera[i]
            a=wall[axis]-wall['s'+axis]/2;b=wall[axis]+wall['s'+axis]/2
            if abs(delta)<1e-12:
                if not a<=camera[i]<=b:low,high=1.,0.;break
            else:
                first,last=sorted(((a-camera[i])/delta,(b-camera[i])/delta))
                low=max(low,first);high=min(high,last)
        if low<=high:return False
    return True


def screen(number):
    import numpy as np
    import yaml
    from scipy.ndimage import minimum_filter
    from language_nav.capture_view import validate_capture_pose
    from language_nav.live_resources import coexistence_headroom
    from expansion_camera_model import rendering_camera
    coexistence_headroom()
    if number not in range(1,11):raise ValueError('development maps only')
    world=ROOT/f'data/physical_worlds_readable_v1/base-r{number:03}'
    scene=yaml.safe_load((world/'landmark_scene.yaml').read_bytes())
    if scene['partition']!='development':raise ValueError('development scene required')
    config=yaml.safe_load((world/'map.yaml').read_bytes())
    if config['origin']!=[-1.,-5.,0.] or config['resolution']!=.05:raise ValueError('unsupported map convention')
    raw=(world/'map.pgm').read_bytes();magic,dimensions,maximum,data=raw.split(b'\n',3)
    if magic!=b'P5' or maximum!=b'255':raise ValueError('unsupported occupancy')
    width,height=map(int,dimensions.split());pixels=np.frombuffer(data,dtype=np.uint8).reshape(height,width)
    # Same 13-by-13 footprint stencil as the authoritative pose checker.
    safe=minimum_filter(pixels,size=13,mode='constant',cval=0)>=200
    walls=json.loads((world/'manifest.json').read_bytes())['layout']['walls']
    grid=[]
    for row in range(6,height-6,5):
        for col in range(6,width-6,5):
            if safe[row,col]:grid.append((-1+(col+.5)*.05,-5+(height-1-row+.5)*.05))
    plan=json.loads((ROOT/'reports/calibration_expansion_proposal_20260911_v2/plan.json').read_bytes())
    targets=[r for r in plan['rows'] if r['partition']=='development' and r['seed']==1
             and r['view_group'].startswith(f'base-r{number:03}-') and r['view_group'].endswith('-view0')]
    if len(targets)!=4:raise ValueError('four exact original targets required')
    results=[]
    for target in targets:
        entity=next(e for e in scene['entities'] if e['entity_id']==target['entity_id'])
        centre=(entity['pose']['x'],entity['pose']['y'])
        viable=[]
        for x,y in grid:
            yaw=math.atan2(centre[1]-y,centre[0]-x)
            camera,_=rendering_camera(dict(x=x,y=y,yaw=yaw))
            if wall_ray_clear(walls,camera[:2],centre):
                viable.append(dict(x=x,y=y,yaw=yaw,range_m=math.dist(camera[:2],centre)))
        ordered=sorted(viable,key=lambda p:(-p['range_m'],p['x'],p['y']))
        poses=[]
        if ordered:
            offsets=(0.,.65 if number%2 else -.65)
            # Choose by geometry only, retaining the fixed yaw offsets. Camera
            # translation under rotation can put the oblique ray behind a wall.
            compatible=[p for p in ordered if all(wall_ray_clear(walls,
                rendering_camera(dict(x=p['x'],y=p['y'],yaw=p['yaw']+offset))[0][:2],centre)
                for offset in offsets)]
            selected=compatible[0] if compatible else ordered[0]
            for index,offset in enumerate(offsets):
                pose={key:selected[key] for key in ('x','y','yaw')};pose['yaw']+=offset
                validate_capture_pose(world,**pose)
                camera,_=rendering_camera(pose)
                poses.append(dict(candidate_id=f'r3-recovery-feas-r{number:03}-{target["category"]}-v{index}',
                    pose=pose,yaw_offset_rad=offset,footprint_checked=True,
                    ray_proxy_clear=wall_ray_clear(walls,camera[:2],centre),
                    occupancy_ray_proxy_clear=clear_ray(pixels,config['origin'],.05,camera[:2],centre),
                    simulator_seed=1,world_directory=str(world.relative_to(ROOT)),
                    entity_id=target['entity_id'],category=target['category'],partition='development',
                    camera_profile=f'reports/fresh_current_capture_20260911_v1/profiles/base-r{number:03}.yaml',
                    horizontal_fov=2.0,raw_frames_per_attempt=1,capture_timeout_seconds=90,
                    execution_authorized=False,fit_or_validation_eligible=False))
        results.append(dict(category=target['category'],entity_id=target['entity_id'],
            safe_grid_points=len(grid),clear_ray_proxy_points=len(viable),
            maximum_screened_camera_range_m=ordered[0]['range_m'] if ordered else None,candidates=poses))
    return dict(map_number=number,targets=results,
        source_sha256={name:hashlib.sha256((world/name).read_bytes()).hexdigest()
                       for name in ('map.pgm','map.yaml','landmark_scene.yaml','world.sdf','manifest.json')})


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    os.nice(19)
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:maps=list(pool.map(screen,range(1,11)))
    report=dict(schema_version='research3-stage1-development-view-feasibility/v1',maps=maps,
        candidate_attempts=sum(len(t['candidates']) for m in maps for t in m['targets']),
        grid_spacing_m=.25,footprint_halfwidth_m=.30,worker_count=4,execution_authorized=False,
        status='offline_screened_proposal_not_rendered',calibration_rows_generated=False,
        validation_accessed=False,protected_accessed=False,
        limitations=['2-D wall-box ray is not 3-D rendered visibility or detection; non-wall visual occluders not checked',
                     'target terminal 0.15m omitted from ray proxy',
                     'grid search not exhaustive continuous geometry',
                     'distance does not guarantee low confidence or incorrect association',
                     'design-only candidates excluded from calibration fitting and certification'])
    with args.output.open('x') as stream:json.dump(report,stream,indent=2,sort_keys=True)
    print(json.dumps({k:v for k,v in report.items() if k!='maps'},indent=2))


if __name__=='__main__':main()
