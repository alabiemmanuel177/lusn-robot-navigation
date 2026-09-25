"""All exact OCR tokens in the fixed development panel; no threshold sweep."""
import json
from pathlib import Path
from collections import Counter
import numpy as np
import yaml
from integrate_object_depth_candidate import ROOT,sha,write,decode_depth
from entrance_context_candidate import text_category
from candidate_depth_support import estimate
from candidate_instance_association import associate
from expansion_camera_model import rendering_camera
from readable_sign_reference_candidate import reference_from_text


def main():
    root=ROOT/'reports/entrance_context_candidate_20260924_v1'
    out=ROOT/'reports/readable_reference_candidate_20260924_v1'
    plan=json.loads((root/'plan.json').read_bytes())
    rows=[json.loads(s) for s in (root/'results.jsonl').read_text().splitlines()]
    pins=dict(plan['input_sha256'])
    for p in (root/'results.jsonl',Path(__file__),ROOT/'scripts/readable_sign_reference_candidate.py',
              ROOT/'scripts/build_readable_physical_worlds.py',ROOT/'src/language_nav/world/physical.py'):
        pins[str(p.resolve())]=sha(p)
    for slot in plan['slots']:
        if slot['status']!='ready':continue
        frame=ROOT/slot['frame'];meta=json.loads(frame.read_bytes())
        for p in (frame,frame.parent/meta['depth']['file'],frame.parent.parent/'request.json',frame.parent.parent/'runtime_scene.yaml'):
            pins[str(p)]=sha(p)
    for p,d in pins.items():
        if sha(p)!=d:raise ValueError('input changed')
    out.mkdir(exist_ok=False)
    write(out/'plan.json',dict(input_sha256=pins,slots=plan['slots'],x_offset=.53,outward_y_offset=.40,
        offsets_origin='readable world builder and original reference definition; not fitted',
        template='research3-readable-corridor-sign-v1',calibration_eligible=False,
        human_method_approval_required=True,scope='authored-template engineering candidate only'))
    results=[];counts=Counter();within=Counter()
    for slot,row in zip(plan['slots'],rows,strict=True):
        if slot['source_index']!=row['source_index']:raise ValueError('order')
        if slot['status']!='ready':results.append(dict(source_index=slot['source_index'],status='retained_source_failure',observations=[]));continue
        frame=ROOT/slot['frame'];meta=json.loads(frame.read_bytes());req=json.loads((frame.parent.parent/'request.json').read_bytes())
        if req['partition']!='development' or req['protected_test_routes_used']:raise ValueError('scope')
        depth=decode_depth((frame.parent/meta['depth']['file']).read_bytes(),meta['depth'])
        centre,rotation=rendering_camera(req['capture_pose']);t=np.eye(4);t[:3,:3]=rotation;t[:3,3]=centre
        scene=yaml.safe_load((frame.parent.parent/'runtime_scene.yaml').read_bytes())
        refs=[dict(entity_id=e['entity_id'],category=e['category'],x=e['pose']['x'],y=e['pose']['y']) for e in scene['entities']]
        observations=[]
        for i,text in enumerate(row['texts']):
            category=text_category(text['text'])
            if category is None:continue
            quad=np.asarray(text['quad']);box=[*quad.min(axis=0),*quad.max(axis=0)]
            surface=estimate(depth,box,np.asarray(meta['camera_info']['k']).reshape(3,3),t)
            result=dict(text_index=i,text=text,visual_category=category,surface=surface,
                        status=surface['status'],human_verdict=None,joint_probability=None,association=None)
            if surface['map_pose'] is not None and not surface['multiple_surfaces_possible']:
                try:
                    converted=reference_from_text(surface['map_pose'],[req['capture_pose']['x'],req['capture_pose']['y']],template='research3-readable-corridor-sign-v1')
                    association=associate(dict(object_localized=True,visual_category=category,map_pose=converted['map_pose'],entity_id=None),refs)
                    result.update(converted=converted,association=association,status=association['status'])
                    if any(v['reference_distance_m']<=.35 for v in association['candidates']):within[category]+=1
                except ValueError as exc:result.update(status='unsupported_template_view',reason=str(exc))
            elif surface.get('multiple_surfaces_possible'):result['status']='unresolved_multiple_surfaces'
            counts[result['status']]+=1;observations.append(result)
        results.append(dict(source_index=slot['source_index'],status='completed',observations=observations))
    for p,d in pins.items():
        if sha(p)!=d:raise ValueError('input changed during replay')
    write(out/'results.json',dict(rows=results,status_counts=counts,within_radius_candidate_counts=within,
        plan_sha256=sha(out/'plan.json'),calibration_eligible=False,
        entrance_structure_verified=False,human_labels_generated=False))
    print(json.dumps(dict(status_counts=counts,within_radius=within),indent=2))


if __name__=='__main__':main()
