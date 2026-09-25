"""Fixed all-portal replay of side-depth hypothesis, no model or label changes."""
import json
from collections import Counter
import numpy as np
import yaml
from integrate_object_depth_candidate import ROOT,sha,write,decode_depth
from run_grounding_candidate_v3 import OUT as SOURCE
from candidate_portal_depth import portal_estimate
from candidate_instance_association import associate
from expansion_camera_model import rendering_camera

OUT=ROOT/'reports/portal_depth_candidate_20260923_v1'
CLASSES=('doorway','laboratory_entrance','office_entrance')


def main():
    source_plan=json.loads((SOURCE/'plan.json').read_bytes())
    audit=json.loads((SOURCE/'audit.json').read_bytes())
    if not audit['reconstruction_passed']:raise ValueError('audited detector required')
    integration=json.loads((SOURCE/'depth_integration.json').read_bytes())
    for p,digest in integration['input_sha256'].items():
        if sha(p)!=digest:raise ValueError('integration source changed')
    pins=dict(integration['input_sha256'])
    for p in (ROOT/'scripts/candidate_portal_depth.py',ROOT/'scripts/run_portal_depth_candidate.py',
              ROOT/'docs/PORTAL_SIDE_DEPTH_PROTOCOL_20260923.md',SOURCE/'depth_integration.json'):
        pins[str(p)]=sha(p)
    OUT.mkdir(exist_ok=False)
    write(OUT/'plan.json',dict(input_sha256=pins,classes=list(CLASSES),
        source_plan_sha256=sha(SOURCE/'plan.json'),side_width_fraction=.15,vertical_trim_fraction=.15,
        maximum_side_relative_disagreement=.15,calibration_eligible=False))
    rows=[];counts=Counter();within=Counter();nearest=[]
    for slot,original in zip(source_plan['slots'],integration['rows'],strict=True):
        if slot['source_index']!=original['source_index']:raise ValueError('source order')
        if slot['status']!='ready':rows.append(dict(source_index=slot['source_index'],status='retained_source_failure',boxes=[]));continue
        frame=ROOT/slot['frame'];meta=json.loads(frame.read_bytes());req=json.loads((frame.parent.parent/'request.json').read_bytes())
        if req['partition']!='development' or req['protected_test_routes_used']:raise ValueError('scope')
        depth=decode_depth((frame.parent/meta['depth']['file']).read_bytes(),meta['depth'])
        scene=yaml.safe_load((frame.parent.parent/'runtime_scene.yaml').read_bytes())
        refs=[dict(entity_id=e['entity_id'],category=e['category'],x=e['pose']['x'],y=e['pose']['y']) for e in scene['entities']]
        centre,rotation=rendering_camera(req['capture_pose']);t=np.eye(4);t[:3,:3]=rotation;t[:3,3]=centre
        boxes=[]
        for index,box in enumerate(original['boxes']):
            prediction=box['prediction'];category=prediction.get('visual_category')
            if category not in CLASSES:continue
            result=portal_estimate(depth,prediction['xyxy'],np.asarray(meta['camera_info']['k']).reshape(3,3),t)
            association=None
            if result['map_pose'] is not None:
                association=associate(dict(object_localized=True,map_pose=result['map_pose'],visual_category=category,entity_id=None),refs)
                for candidate in association['candidates']:
                    nearest.append(candidate['reference_distance_m'])
                if any(c['reference_distance_m']<=.35 for c in association['candidates']):within[category]+=1
            status=result['status'] if association is None else association['status']
            counts[status]+=1
            boxes.append(dict(source_box_index=index,prediction=prediction,surface=result,association=association,
                prior_status=box['status'],human_verdict=None,calibration_eligible=False))
        rows.append(dict(source_index=slot['source_index'],status='completed',boxes=boxes))
    for p,digest in pins.items():
        if sha(p)!=digest:raise ValueError('input changed during replay')
    write(OUT/'results.json',dict(rows=rows,status_counts=counts,
        portal_predictions=sum(counts.values()),within_reference_radius_candidate_counts=within,
        minimum_candidate_reference_distance_m=min(nearest) if nearest else None,
        actual_identity_verified=False,human_labels_generated=False,calibration_eligible=False,
        plan_sha256=sha(OUT/'plan.json')))
    print(json.dumps(dict(status_counts=counts,within_reference_radius=within),indent=2))


if __name__=='__main__':main()
