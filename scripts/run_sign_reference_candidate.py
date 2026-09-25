"""Fixed sign-anchor replay motivated by the existing entrance-reference convention.

Scene text only produces hypotheses: it never establishes sign ownership. Every
generic sign box is retained; conflicting recognized classes abstain. Catalogue
coordinates are used only after visual category and depth localization.
"""
import json
from collections import Counter
import numpy as np
import yaml
from integrate_object_depth_candidate import ROOT,sha,write,decode_depth
from entrance_context_candidate import text_category
from candidate_depth_support import estimate
from candidate_instance_association import associate
from expansion_camera_model import rendering_camera


def main():
    source=ROOT/'reports/grounding_candidate_20260923_v3'
    ocr=ROOT/'reports/entrance_context_candidate_20260924_v1'
    out=ROOT/'reports/sign_reference_candidate_20260924_v1'
    plan=json.loads((source/'plan.json').read_bytes())
    pins=dict(plan['input_sha256'])
    for p in (source/'results.jsonl',ocr/'results.jsonl',ocr/'audit.json',Path(__file__),
              ROOT/'scripts/candidate_depth_support.py',ROOT/'scripts/candidate_instance_association.py',
              ROOT/'src/language_nav/world/physical.py'):
        pins[str(p.resolve())]=sha(p)
    predictions=[json.loads(s) for s in (source/'results.jsonl').read_text().splitlines()]
    contexts=[json.loads(s) for s in (ocr/'results.jsonl').read_text().splitlines()]
    for slot in plan['slots']:
        if slot['status']!='ready':continue
        frame=ROOT/slot['frame'];meta=json.loads(frame.read_bytes())
        for p in (frame.parent/meta['depth']['file'],frame.parent.parent/'runtime_scene.yaml'):
            pins[str(p)]=sha(p)
    for p,d in pins.items():
        if sha(p)!=d:raise ValueError('source changed')
    out.mkdir(exist_ok=False)
    write(out/'plan.json',dict(input_sha256=pins,slots=plan['slots'],calibration_eligible=False,
        rule='every existing generic sign box; unique exact OCR class in full image creates only a hypothesis; central depth; retain all associations',
        no_parameter_sweep=True,uses_catalogue_for_visual_inference=False))
    counts=Counter();within=Counter();rows=[]
    for slot,pred,context in zip(plan['slots'],predictions,contexts,strict=True):
        index=slot['source_index']
        if index!=pred['source_index'] or index!=context['source_index']:raise ValueError('order')
        if slot['status']!='ready':rows.append(dict(source_index=index,status='retained_source_failure',boxes=[]));continue
        frame=ROOT/slot['frame'];meta=json.loads(frame.read_bytes());req=json.loads((frame.parent.parent/'request.json').read_bytes())
        if req['partition']!='development' or req['protected_test_routes_used']:raise ValueError('scope')
        classes=sorted({c for t in context['texts'] if (c:=text_category(t['text'])) is not None})
        depth=decode_depth((frame.parent/meta['depth']['file']).read_bytes(),meta['depth'])
        centre,rotation=rendering_camera(req['capture_pose']);transform=np.eye(4);transform[:3,:3]=rotation;transform[:3,3]=centre
        scene=yaml.safe_load((frame.parent.parent/'runtime_scene.yaml').read_bytes())
        refs=[dict(entity_id=e['entity_id'],category=e['category'],x=e['pose']['x'],y=e['pose']['y']) for e in scene['entities']]
        boxes=[]
        for i,box in enumerate(pred['boxes']):
            if box['visual_category']!='sign':continue
            result=dict(source_box_index=i,prediction=box,context_classes=classes,human_verdict=None,
                        context_ownership_verified=False,calibration_eligible=False,association=None)
            if len(classes)!=1:result['status']='no_unique_scene_context'
            else:
                surface=estimate(depth,box['xyxy'],np.asarray(meta['camera_info']['k']).reshape(3,3),transform)
                result['surface']=surface;result['status']=surface['status']
                if surface['map_pose'] is not None and not surface['multiple_surfaces_possible']:
                    association=associate(dict(object_localized=True,visual_category=classes[0],map_pose=surface['map_pose'],entity_id=None),refs)
                    result.update(association=association,status=association['status'])
                    if any(v['reference_distance_m']<=.35 for v in association['candidates']):within[classes[0]]+=1
                elif surface.get('multiple_surfaces_possible'):result['status']='unresolved_multiple_surfaces'
            counts[result['status']]+=1;boxes.append(result)
        rows.append(dict(source_index=index,status='completed',boxes=boxes))
    for p,d in pins.items():
        if sha(p)!=d:raise ValueError('source changed during replay')
    write(out/'results.json',dict(rows=rows,status_counts=counts,within_radius_candidate_counts=within,
        plan_sha256=sha(out/'plan.json'),calibration_eligible=False,human_labels_generated=False))
    print(json.dumps(dict(status_counts=counts,within_radius=within),indent=2))


from pathlib import Path
if __name__=='__main__':main()
