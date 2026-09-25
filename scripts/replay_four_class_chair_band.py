"""All-frame v3 replay, replacing only the separately versioned chair estimator."""
import argparse
import copy
import json
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
import yaml
from integrate_object_depth_candidate import ROOT,sha,write,decode_depth
from expansion_camera_model import rendering_camera
from bound_pose_observer import matrix
from candidate_rendering_transform import correction
from chair_foreground_band_candidate import chair_surface_estimate
from candidate_instance_association import associate
from four_class_perception_candidate import frame_gate,CLASSES


def main(panel):
    prefix={'stage_a':'four_class_readiness','broad':'four_class_broad','live':'four_class_live','repeated':'four_class_repeated'}[panel]
    source=ROOT/f'reports/{prefix}_integration_20260924_v2';out=ROOT/f'reports/{prefix}_integration_20260924_v3'
    plan=json.loads((source/'plan.json').read_bytes());result=json.loads((source/'results.json').read_bytes())
    if result['plan_sha256']!=sha(source/'plan.json'):raise ValueError('source binding')
    pins=dict(plan['input_sha256'])
    for p in (source/'plan.json',source/'results.json',Path(__file__),ROOT/'scripts/chair_foreground_band_candidate.py',ROOT/'scripts/four_class_perception_candidate_v3.py'):
        pins[str(p.resolve())]=sha(p)
    for p,d in pins.items():
        if sha(p)!=d:raise ValueError('pinned source changed')
    out.mkdir(exist_ok=False)
    write(out/'plan.json',dict(input_sha256=pins,slots=plan['slots'],chair_depth_band_width_m=.10,
        minimum_support_fraction=.10,minimum_support_pixels=16,calibration_eligible=False,
        other_class_estimators_unchanged=True))
    rows=copy.deepcopy(result['rows']);support=defaultdict(Counter);counts=Counter();statuses={c:Counter() for c in CLASSES}
    repeated=Counter()
    for slot,row in zip(plan['slots'],rows,strict=True):
        if slot['source_index']!=row['source_index']:raise ValueError('order')
        counts[row['status']]+=1
        if row['status']!='completed':continue
        frame=ROOT/slot['frame'];meta=json.loads(frame.read_bytes());req=json.loads((frame.parent.parent/'request.json').read_bytes())
        if req['partition']!='development' or req['protected_test_routes_used']:raise ValueError('scope')
        depth=decode_depth((frame.parent/meta['depth']['file']).read_bytes(),meta['depth'])
        if panel in ('broad','stage_a'):
            centre,rotation=rendering_camera(req['capture_pose']);t=np.eye(4);t[:3,:3]=rotation;t[:3,3]=centre
            scene_path=frame.parent.parent/'runtime_scene.yaml'
        else:
            tf=meta['camera_to_map']['transform'];p=tf['translation'];q=tf['rotation']
            nominal=matrix([p[k] for k in ('x','y','z')],[q[k] for k in ('x','y','z','w')])
            mount=json.loads((frame.parent.parent.parent/'plan.json').read_bytes());t=correction(nominal,mount['nominal_mount'],mount['rendered_mount'])
            scene_path=Path(req['world_directory'])/'landmark_scene.yaml'
        scene=yaml.safe_load(scene_path.read_bytes());refs=[dict(entity_id=e['entity_id'],category=e['category'],x=e['pose']['x'],y=e['pose']['y']) for e in scene['entities']]
        for obs in row['observations']:
            if obs['visual_category']=='chair':
                surface=chair_surface_estimate(depth,obs['box'],np.asarray(meta['camera_info']['k']).reshape(3,3),t)
                obs.update(surface=surface,map_pose=surface['map_pose'],association=None,status=surface['status'])
                if surface['map_pose'] is not None:
                    a=associate(dict(object_localized=True,visual_category='chair',map_pose=surface['map_pose'],entity_id=None),refs)
                    obs.update(association=a,status=a['status'])
            statuses[obs['visual_category']][obs['status']]+=1
        gate=frame_gate(row['observations']);row['necessary_geometry_gate']=gate;row['map_id']=req['map_id']
        for c,value in gate.items():support[req['map_id']][c]+=int(value)
        for c in CLASSES:
            ids={o['association']['entity_id'] for o in row['observations'] if o['visual_category']==c and o['association'] and o['association']['status']=='unique_geometric_candidate' and o['association']['candidates'][0]['reference_distance_m']<=.35}
            if len(ids)>1:repeated[c]+=1
    for p,d in pins.items():
        if sha(p)!=d:raise ValueError('input changed during replay')
    deficits=[dict(map_id=m,category=c) for m in support for c in CLASSES if support[m][c]<1]
    write(out/'results.json',dict(rows=rows,status_counts=counts,class_status_counts=statuses,
        supporting_frames_by_map_class=support,missing_map_class_geometry=deficits,
        same_frame_two_distinct_in_radius_instances=repeated,plan_sha256=sha(out/'plan.json'),
        necessary_geometry_passed=not deficits,identity_accuracy_verified=False,calibration_eligible=False))
    print(json.dumps(dict(counts=counts,support=support,deficits=deficits,repeated=repeated),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('panel',choices=('stage_a','broad','live','repeated'));main(p.parse_args().panel)
