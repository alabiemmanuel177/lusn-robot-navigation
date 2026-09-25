"""Retain every Grounding DINO proposal through the existing offline depth contract."""
from collections import Counter
import json
import numpy as np
import yaml
from integrate_object_depth_candidate import ROOT, sha, write, decode_depth, integrate_box
from run_grounding_candidate_v3 import OUT
from expansion_camera_model import rendering_camera


def main():
    plan=json.loads((OUT/'plan.json').read_bytes())
    audit=json.loads((OUT/'audit.json').read_bytes())
    if not audit['reconstruction_passed']:raise ValueError('detector audit required')
    rows=[json.loads(s) for s in (OUT/'results.jsonl').read_text().splitlines()]
    if len(rows)!=len(plan['slots']):raise ValueError('schedule accounting')
    pins={str(p):sha(p) for p in (OUT/'plan.json',OUT/'report.json',OUT/'results.jsonl',OUT/'audit.json',
        ROOT/'scripts/integrate_grounding_candidate.py',ROOT/'scripts/integrate_object_depth_candidate.py',
        ROOT/'scripts/candidate_depth_support.py',ROOT/'scripts/candidate_instance_association.py',
        ROOT/'scripts/expansion_camera_model.py')}
    outputs=[];counts=Counter()
    for slot,row in zip(plan['slots'],rows,strict=True):
        if slot['source_index']!=row['source_index']:raise ValueError('source order')
        if slot['status']!='ready':
            outputs.append(dict(source_index=slot['source_index'],status='retained_source_failure',boxes=[]));continue
        frame=(ROOT/slot['frame']).resolve();request=frame.parent.parent/'request.json'
        if str(request) not in plan['input_sha256'] or sha(request)!=plan['input_sha256'][str(request)]:raise ValueError('request binding')
        req=json.loads(request.read_bytes())
        if req['partition']!='development' or req['protected_test_routes_used']:raise ValueError('development only')
        if sha(frame)!=plan['input_sha256'][str(frame)]:raise ValueError('frame binding')
        meta=json.loads(frame.read_bytes());depth_path=(frame.parent/meta['depth']['file']).resolve()
        if depth_path.parent!=frame.parent:raise ValueError('depth path')
        pins[str(depth_path)]=sha(depth_path)
        if pins[str(depth_path)]!=meta['depth']['sha256']:raise ValueError('depth hash')
        if meta['sync_difference_ns']!=0 or meta['rgb_stamp_ns']!=meta['depth_stamp_ns']:raise ValueError('synchronization')
        scene_path=frame.parent.parent/'runtime_scene.yaml'
        pins[str(scene_path)]=sha(scene_path)
        if pins[str(scene_path)]!=req['runtime_scene_sha256']:raise ValueError('scene hash')
        scene=yaml.safe_load(scene_path.read_bytes())
        if scene['partition']!='development' or scene['map_id']!=req['map_id']:raise ValueError('scene scope')
        refs=[dict(entity_id=e['entity_id'],category=e['category'],x=e['pose']['x'],y=e['pose']['y']) for e in scene['entities']]
        depth=decode_depth(depth_path.read_bytes(),meta['depth'])
        centre,rotation=rendering_camera(req['capture_pose']);transform=np.eye(4)
        transform[:3,:3]=rotation;transform[:3,3]=centre
        boxes=[]
        for predicted in row['boxes']:
            if predicted['visual_category'] is None:
                result=dict(status='unresolved_text_hypothesis',prediction=predicted,
                    human_verdict=None,joint_correctness_probability=None,calibration_eligible=False,runtime_admitted=False)
            else:
                result=integrate_box(dict(predicted,query=predicted['visual_category']),depth,
                    np.asarray(meta['camera_info']['k']).reshape(3,3),transform,refs)
            boxes.append(result);counts[result['status']]+=1
        outputs.append(dict(source_index=slot['source_index'],status='completed',boxes=boxes))
    for path,digest in pins.items():
        if sha(path)!=digest:raise ValueError('input changed during integration')
    write(OUT/'depth_integration.json',dict(rows=outputs,status_counts=counts,input_sha256=pins,
        transform_provenance='commanded_stationary_pose_plus_rendering_model_not_independent_ground_truth',
        all_proposals_retained=True,calibration_eligible=False,runtime_admitted=False,human_labels_generated=False))
    print(json.dumps(counts,indent=2))


if __name__=='__main__':main()
