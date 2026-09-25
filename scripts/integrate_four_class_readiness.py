"""Fixed all-frame readiness accounting; geometry-only gates and explicit abstention."""
import argparse
import json
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
import yaml
from integrate_object_depth_candidate import ROOT,sha,write,decode_depth
from expansion_camera_model import rendering_camera
from four_class_perception_candidate import localize,associate_observations,frame_gate,CLASSES


def main(panel):
    prefix='four_class_broad' if panel=='broad' else 'four_class_readiness'
    detector=ROOT/f'reports/{prefix}_detector_20260924_v1';ocr=ROOT/f'reports/{prefix}_ocr_20260924_v1'
    out=ROOT/f'reports/{prefix}_integration_20260924_v1'
    plan=json.loads((detector/'plan.json').read_bytes());audit=json.loads((detector/'audit.json').read_bytes())
    if not audit['reconstruction_passed']:raise ValueError('detector raw reconstruction required')
    op=json.loads((ocr/'plan.json').read_bytes());report=json.loads((ocr/'report.json').read_bytes())
    if report['journal_sha256']!=sha(ocr/'results.jsonl') or report['plan_sha256']!=sha(ocr/'plan.json'):raise ValueError('OCR report binding')
    pins={**plan['input_sha256'],**op['input_sha256']}
    for p in [detector/'plan.json',detector/'results.jsonl',detector/'audit.json',ocr/'plan.json',ocr/'results.jsonl',
              Path(__file__),ROOT/'scripts/four_class_perception_candidate.py',ROOT/'scripts/candidate_depth_support.py',
              ROOT/'scripts/candidate_portal_depth.py',ROOT/'scripts/candidate_instance_association.py',
              ROOT/'scripts/readable_sign_reference_candidate.py',ROOT/'scripts/entrance_context_candidate.py']:
        pins[str(p.resolve())]=sha(p)
    for slot in plan['slots']:
        if slot['status']!='ready':continue
        frame=ROOT/slot['frame'];meta=json.loads(frame.read_bytes())
        for p in (frame.parent/meta['depth']['file'],frame.parent.parent/'runtime_scene.yaml'):pins[str(p)]=sha(p)
    for p,d in pins.items():
        if sha(p)!=d:raise ValueError('pinned input changed: '+p)
    out.mkdir(exist_ok=False)
    write(out/'plan.json',dict(input_sha256=pins,slots=plan['slots'],calibration_eligible=False,
        template='research3-readable-corridor-sign-v1',uses_human_labels=False))
    dr=[json.loads(s) for s in (detector/'results.jsonl').read_text().splitlines()]
    tr=[json.loads(s) for s in (ocr/'results.jsonl').read_text().splitlines()]
    rows=[];counts=Counter();support=defaultdict(Counter);assigned_support=defaultdict(Counter);scheduled=defaultdict(Counter)
    repeated=Counter();class_status={c:Counter() for c in CLASSES}
    for slot,pred,text in zip(plan['slots'],dr,tr,strict=True):
        index=slot['source_index']
        if index!=pred['source_index'] or index!=text['source_index']:raise ValueError('frame order')
        if slot['status']!='ready':
            rows.append(dict(source_index=index,status='retained_source_failure',observations=[]));counts['infrastructure_failure']+=1;continue
        frame=ROOT/slot['frame'];meta=json.loads(frame.read_bytes());req=json.loads((frame.parent.parent/'request.json').read_bytes())
        if req['partition']!='development' or req['protected_test_routes_used']:raise ValueError('scope')
        if meta['rgb_stamp_ns']!=meta['depth_stamp_ns']:raise ValueError('exact RGB-D required')
        depth=decode_depth((frame.parent/meta['depth']['file']).read_bytes(),meta['depth'])
        centre,rotation=rendering_camera(req['capture_pose']);t=np.eye(4);t[:3,:3]=rotation;t[:3,3]=centre
        scene=yaml.safe_load((frame.parent.parent/'runtime_scene.yaml').read_bytes())
        if scene['partition']!='development':raise ValueError('scene scope')
        refs=[dict(entity_id=e['entity_id'],category=e['category'],x=e['pose']['x'],y=e['pose']['y']) for e in scene['entities']]
        visual=localize(depth,np.asarray(meta['camera_info']['k']).reshape(3,3),t,pred['boxes'],text['texts'],
            camera_xy=[req['capture_pose']['x'],req['capture_pose']['y']],template='research3-readable-corridor-sign-v1')
        observations=associate_observations(visual,refs);gate=frame_gate(observations)
        map_id=req['map_id'];assigned=req['capture_target_categories'][0];scheduled[map_id][assigned]+=1
        for category,passed in gate.items():
            support[map_id][category]+=int(passed)
            if assigned==category:assigned_support[map_id][category]+=int(passed)
            ids={o['association']['entity_id'] for o in observations if o['visual_category']==category and o['association'] and o['association']['status']=='unique_geometric_candidate'}
            if len(ids)>1:repeated[category]+=1
        for o in observations:class_status[o['visual_category']][o['status']]+=1
        counts['completed']+=1
        if not observations:counts['no_visual_candidate']+=1
        rows.append(dict(source_index=index,status='completed',map_id=map_id,acquisition_category=assigned,
            frame=slot['frame'],observations=observations,necessary_geometry_gate=gate))
    for p,d in pins.items():
        if sha(p)!=d:raise ValueError('source changed during integration')
    deficits=[dict(map_id=m,category=c) for m in scheduled for c in CLASSES if support[m][c]<1]
    write(out/'results.json',dict(rows=rows,frame_status_counts=counts,class_status_counts=class_status,
        supporting_frames_by_map_class=support,assigned_category_support=assigned_support,scheduled_by_map_class=scheduled,
        multiple_same_class_geometric_instances_frames=repeated,missing_map_class_geometry=deficits,
        necessary_map_class_geometry_passed=not deficits,identity_accuracy_verified=False,
        four_class_scientific_readiness=False,calibration_eligible=False,human_labels_generated=False,
        plan_sha256=sha(out/'plan.json'),transform_provenance='historical commanded stationary rendering model; not measured pose'))
    print(json.dumps(dict(frame_counts=counts,support=support,deficits=deficits,repeated_geometric_instances=repeated),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('panel',choices=('broad','stage_a'));main(p.parse_args().panel)
