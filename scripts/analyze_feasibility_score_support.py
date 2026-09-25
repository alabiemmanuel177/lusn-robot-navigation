"""Development-only design-feasibility score reconstruction, not calibration."""
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



def analyze(row):
    from language_nav.live_resources import coexistence_headroom
    headroom=coexistence_headroom()
    import numpy as np
    from expansion_rendered_checks import decode_frame
    sys.path.insert(0,str(PROVIDER))
    from research3_landmark_bridge.core import load_landmark_scene,detect_color_markers
    if row['partition']!='development' or row['panel']!='design_feasibility':raise ValueError('development design-only')
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
    from run_stage1_feasibility import assignments,write
    os.nice(19)
    output=ROOT/'reports/stage1_design_score_support_20260922_v1.json'
    if output.exists():raise FileExistsError(output)
    rows=[]
    for target in assignments():
        folder=ROOT/'reports/physical_live_episodes'/target['candidate_id']
        path=folder/'expansion_attempt.json'
        if not path.exists():continue
        selected=json.loads(path.read_bytes()).get('selected_observation')
        if selected:
            rows.append(dict(run_id=target['candidate_id'],category=target['category'],
                partition='development',panel='design_feasibility',
                observation_id=selected['observation_id'],probability=selected['confidence']))
    results=[];failures=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
        for row,future in zip(rows,[pool.submit(analyze,row) for row in rows]):
            try:results.append(future.result())
            except Exception as exc:failures.append(dict(run_id=row['run_id'],error=str(exc)))
    classes={}
    for category in sorted({r['category'] for r in results}):
        group=[r for r in results if r['category']==category]
        classes[category]=dict(emissions=len(group),minimum_pixels=min(r['pixels'] for r in group),
            maximum_pixels=max(r['pixels'] for r in group),
            saturated_support=sum(r['support_score']==1 for r in group),
            minimum_probability=min(r['probability'] for r in group),
            maximum_probability=max(r['probability'] for r in group),
            minimum_color_score=min(r['color_score_inferred'] for r in group),
            maximum_reconstruction_residual=max(r['absolute_score_residual'] for r in group))
    report=dict(schema_version='research3-design-feasibility-score-audit/v1',
        classes=classes,rows=results,failures=failures,scheduled_attempts=80,
        selected_emissions=len(rows),calibration_eligible=False,human_labels_generated=False,
        provider_core_sha256=hashlib.sha256((PROVIDER/'research3_landmark_bridge/core.py').read_bytes()).hexdigest(),
        assumptions=dict(min_pixels=18,association_radius_m=.9,temperature=1),
        validation_read=False,simulator_launched=False)
    write(output,report)
    print(json.dumps(dict(classes=classes,failures=failures)))
    if failures or not all(r['score_reconstruction_matches'] for r in results):raise SystemExit(1)


if __name__=='__main__':main()
