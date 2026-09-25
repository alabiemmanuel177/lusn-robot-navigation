"""Replay development adapter and independently recompute association distances."""
import argparse
import json
import math
from pathlib import Path
from collections import Counter
import numpy as np
import yaml
from integrate_object_depth_candidate import ROOT,sha,write,decode_depth
from expansion_camera_model import rendering_camera
from bound_pose_observer import matrix
from candidate_rendering_transform import correction
from four_class_candidate_runtime import process_frame


def main(panel):
    prefix={'stage_a':'four_class_readiness','broad':'four_class_broad','live':'four_class_live','repeated':'four_class_repeated'}[panel]
    root=ROOT/f'reports/{prefix}_integration_20260924_v2';detector=ROOT/f'reports/{prefix}_detector_20260924_v1'
    ocr=ROOT/f'reports/{prefix}_ocr_20260924_v1';plan=json.loads((root/'plan.json').read_bytes());result=json.loads((root/'results.json').read_bytes())
    if sha(root/'plan.json')!=result['plan_sha256']:raise ValueError('result plan binding')
    for p,d in plan['input_sha256'].items():
        if sha(p)!=d:raise ValueError('pinned input changed')
    predictions={r['source_index']:r for r in map(json.loads,(detector/'results.jsonl').read_text().splitlines())}
    texts={r['source_index']:r for r in map(json.loads,(ocr/'results.jsonl').read_text().splitlines())}
    counts=Counter();repeated=Counter();replayed=0;observations=0;distances=[]
    for slot,row in zip(plan['slots'],result['rows'],strict=True):
        index=slot['source_index']
        if index!=row['source_index']:raise ValueError('order')
        if row['status']!='completed':counts[row['status']]+=1;continue
        frame=ROOT/slot['frame'];meta=json.loads(frame.read_bytes());req=json.loads((frame.parent.parent/'request.json').read_bytes())
        depth=decode_depth((frame.parent/meta['depth']['file']).read_bytes(),meta['depth'])
        if panel in ('broad','stage_a'):
            centre,rotation=rendering_camera(req['capture_pose']);t=np.eye(4);t[:3,:3]=rotation;t[:3,3]=centre
            camera_xy=[req['capture_pose']['x'],req['capture_pose']['y']];scene_path=frame.parent.parent/'runtime_scene.yaml'
        else:
            tf=meta['camera_to_map']['transform'];p=tf['translation'];q=tf['rotation']
            nominal=matrix([p[k] for k in ('x','y','z')],[q[k] for k in ('x','y','z','w')])
            mount=json.loads((frame.parent.parent.parent/'plan.json').read_bytes());t=correction(nominal,mount['nominal_mount'],mount['rendered_mount'])
            camera_xy=t[:2,3].tolist();scene_path=Path(req['world_directory'])/'landmark_scene.yaml'
        scene=yaml.safe_load(scene_path.read_bytes())
        refs=[dict(entity_id=e['entity_id'],category=e['category'],x=e['pose']['x'],y=e['pose']['y']) for e in scene['entities']]
        replay=process_frame(frame_id=str(frame),rgb_stamp_ns=meta['rgb_stamp_ns'],depth_stamp_ns=meta['depth_stamp_ns'],
            depth=depth,k=np.asarray(meta['camera_info']['k']).reshape(3,3),optical_to_map=t,
            detector_boxes=predictions[index]['boxes'],ocr_texts=texts[index]['texts'],catalogue=refs,camera_xy=camera_xy,
            template='research3-readable-corridor-sign-v1',partition=req['partition'])
        if replay['hypotheses']!=row['observations']:raise ValueError('runtime adapter replay mismatch')
        ids={c:set() for c in ('chair','doorway','laboratory_entrance','office_entrance')}
        for obs in row['observations']:
            observations+=1
            if obs['human_verdict'] is not None or obs['joint_probability'] is not None or obs['runtime_admitted'] or obs['calibration_eligible']:
                raise ValueError('unapproved scientific claim')
            a=obs['association']
            if a:
                x,y=obs['map_pose'];expected=[]
                for ref in refs:
                    distance=math.hypot(x-ref['x'],y-ref['y'])
                    if ref['category']==obs['visual_category'] and distance<=.9:
                        expected.append(dict(entity_id=ref['entity_id'],reference_distance_m=distance))
                expected.sort(key=lambda e:e['entity_id'])
                if expected!=a['candidates']:raise ValueError('independent reference arithmetic')
                if len(expected)==1 and expected[0]['reference_distance_m']<=.35:
                    ids[obs['visual_category']].add(expected[0]['entity_id']);distances.append(expected[0]['reference_distance_m'])
        for c,values in ids.items():
            if len(values)>=2:repeated[c]+=1
        replayed+=1;counts['completed']+=1
    pins={str(p.resolve()):sha(p) for p in (Path(__file__),ROOT/'scripts/four_class_candidate_runtime.py',root/'plan.json',root/'results.json')}
    write(root/'audit.json',dict(runtime_replay_passed=True,independent_association_arithmetic_passed=True,
        source_pins_unchanged=True,replayed_frames=replayed,hypotheses=observations,status_counts=counts,
        same_frame_two_distinct_in_radius_instances=repeated,maximum_in_radius_distance_m=max(distances,default=None),
        input_sha256=pins,identity_accuracy_verified=False,calibration_eligible=False))
    print(json.dumps(dict(frames=replayed,hypotheses=observations,repeated=repeated),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('panel',choices=('stage_a','broad','live','repeated'));main(p.parse_args().panel)
