"""Four-worker development-only score reconstruction, not new collection."""
import concurrent.futures
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
PROVIDER=Path('/home/eao/risk-calibrated-nav/extensions/research3_landmark_bridge')
LABELS=ROOT/'reports/expansion_development_calibration_candidate_20260914_v1/development_labels.jsonl'


def analyze(row):
    from language_nav.live_resources import coexistence_headroom
    headroom=coexistence_headroom()
    import numpy as np
    from expansion_rendered_checks import decode_frame
    sys.path.insert(0,str(PROVIDER))
    from research3_landmark_bridge.core import load_landmark_scene,detect_color_markers
    if row['partition']!='development' or row['panel']!='primary_expansion':raise ValueError('development primary only')
    run_id=row['run_id']
    if Path(run_id).name!=run_id:raise ValueError('unsafe run ID')
    folder=ROOT/'reports/physical_live_episodes'/run_id
    request=json.loads((folder/'request.json').read_bytes())
    if request['partition']!='development' or request['protected_test_routes_used'] is not False:raise ValueError('scope')
    image,frame=decode_frame(folder/'perception_capture/frame-000.json')
    meta=frame['depth']
    if meta['file']!='frame-000-depth.bin' or meta['encoding']!='32FC1':raise ValueError('unexpected depth input')
    raw=(folder/'perception_capture'/meta['file']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=meta['sha256']:raise ValueError('depth integrity')
    depth=np.frombuffer(raw,dtype='>f4' if meta['is_bigendian'] else '<f4').reshape(meta['height'],meta['step']//4)[:,:meta['width']]
    scene=load_landmark_scene(folder/'runtime_scene.yaml')
    tasks=[json.loads(line) for line in (folder/'landmark_review_tasks.jsonl').read_text().splitlines()]
    matches=[t for t in tasks if t['observation_id']==row['observation_id']]
    if len(matches)!=1:raise ValueError('nonunique observation')
    task=matches[0]
    if task['probability']!=row['probability']:raise ValueError('probability join')
    detections=detect_color_markers(image,depth,scene,color_tolerance=request['camera_color_tolerance'],min_pixels=18)
    matches=[d for d in detections if d.category==task['category'] and d.pixels==task['pixels']
             and abs(d.u-task['pixel']['u'])<1e-6 and abs(d.v-task['pixel']['v'])<1e-6]
    if len(matches)!=1:raise ValueError('retained detector component does not reconstruct uniquely')
    detection=matches[0]
    observation=json.loads((folder/'expansion_attempt.json').read_bytes())['selected_observation']
    if observation['observation_id']!=row['observation_id']:raise ValueError('selected identity')
    entity=next(e for e in scene.entities if e.entity_id==task['entity_id'])
    error=math.hypot(observation['x']-entity.x,observation['y']-entity.y)
    spatial_factor=.7+.3*max(0.,1-error/.9)
    reconstructed=detection.raw_confidence*spatial_factor
    support=min(1.,detection.pixels/72.)
    color=(detection.raw_confidence-.45*support)/.55
    return dict(run_id=run_id,category=row['category'],observation_id=row['observation_id'],
        probability=row['probability'],detector_raw_confidence=detection.raw_confidence,
        color_score_inferred=color,support_score=support,pixels=detection.pixels,
        association_error_m=error,spatial_factor=spatial_factor,
        reconstructed_confidence=reconstructed,absolute_score_residual=abs(reconstructed-row['probability']),
        score_reconstruction_matches=abs(reconstructed-row['probability'])<1e-8,
        depth_m=detection.depth_m,
        idealized_depth_for_72_pixels_m=detection.depth_m*math.sqrt(detection.pixels/72.),
        source_binding={name:hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in
            ('request.json','runtime_scene.yaml','perception_capture/frame-000.json','landmark_review_tasks.jsonl','expansion_attempt.json')},
        headroom=headroom,human_label_generated=False)


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    os.nice(19)
    from language_nav.live_resources import coexistence_headroom
    before=coexistence_headroom()
    raw=LABELS.read_bytes();rows=[json.loads(line) for line in raw.splitlines()]
    args.output.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();results=[];failures=[]
    with (args.output/'progress.jsonl').open('x') as progress:
        with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
            # Batches bound outstanding work and recheck headroom before dispatch.
            for offset in range(0,len(rows),4):
                coexistence_headroom()
                batch=rows[offset:offset+4]
                futures=[pool.submit(analyze,row) for row in batch]
                for row,future in zip(batch,futures):
                    try:result=future.result();results.append(result)
                    except Exception as exc:
                        result=dict(run_id=row['run_id'],error=str(exc));failures.append(result)
                    progress.write(json.dumps(result,sort_keys=True)+'\n');progress.flush()
                if offset%40==0:print(f'Accounted {offset+len(batch)}/{len(rows)}',flush=True)
    summary={}
    for category in sorted({r['category'] for r in results}):
        group=[r for r in results if r['category']==category]
        summary[category]=dict(count=len(group),all_scores_match=all(r['score_reconstruction_matches'] for r in group),
            max_score_residual=max(r['absolute_score_residual'] for r in group),
            minimum_color_score=min(r['color_score_inferred'] for r in group),
            all_support_saturated=all(r['support_score']==1 for r in group),
            idealized_depth_for_72_pixels_min_m=min(r['idealized_depth_for_72_pixels_m'] for r in group),
            idealized_depth_for_72_pixels_median_m=statistics.median(r['idealized_depth_for_72_pixels_m'] for r in group))
    report=dict(schema_version='research3-stage1-offline-score-reconstruction/v1',workers=4,
        nice=os.nice(0),elapsed_seconds=time.monotonic()-started,attempted=len(rows),completed=len(results),
        failures=failures,classes=summary,headroom_before=before,headroom_after=coexistence_headroom(),
        labels_sha256=hashlib.sha256(raw).hexdigest(),
        provider_core_sha256=hashlib.sha256((PROVIDER/'research3_landmark_bridge/core.py').read_bytes()).hexdigest(),
        assumptions=dict(min_pixels=18,association_radius_m=.9,temperature=1),
        depth_estimate_scope='inverse-square pixel-area heuristic at fixed orientation; not a verified pose, visibility, reachable distance or prediction of errors',
        validation_read=False,simulator_launched=False,human_labels_generated=False)
    with (args.output/'report.json').open('x') as stream:json.dump(report,stream,indent=2,sort_keys=True)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
