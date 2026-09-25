"""Fresh perception replay uses recorded localization TF, never commanded pose."""
import json
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
import yaml
from integrate_object_depth_candidate import ROOT,sha,write,decode_depth
from bound_pose_observer import matrix
from candidate_rendering_transform import correction
from four_class_perception_candidate_v2 import localize,associate_observations,frame_gate,CLASSES


def main():
    detector=ROOT/'reports/four_class_repeated_detector_20260924_v1';ocr=ROOT/'reports/four_class_repeated_ocr_20260924_v1'
    out=ROOT/'reports/four_class_repeated_integration_20260924_v2'
    plan=json.loads((detector/'plan.json').read_bytes());audit=json.loads((detector/'audit.json').read_bytes())
    if not audit['reconstruction_passed']:raise ValueError('raw audit required')
    op=json.loads((ocr/'plan.json').read_bytes());report=json.loads((ocr/'report.json').read_bytes())
    if report['journal_sha256']!=sha(ocr/'results.jsonl'):raise ValueError('OCR journal binding')
    pins={**plan['input_sha256'],**op['input_sha256']}
    for p in (Path(__file__),detector/'plan.json',detector/'results.jsonl',detector/'audit.json',ocr/'results.jsonl',ROOT/'scripts/four_class_perception_candidate.py',ROOT/'scripts/four_class_perception_candidate_v2.py',ROOT/'scripts/chair_foreground_depth_candidate.py'):
        pins[str(p.resolve())]=sha(p)
    for slot in plan['slots']:
        if slot['status']!='ready':continue
        frame=ROOT/slot['frame'];meta=json.loads(frame.read_bytes());req=json.loads((frame.parent.parent/'request.json').read_bytes())
        for p in (frame.parent/meta['depth']['file'],Path(req['world_directory'])/'landmark_scene.yaml'):
            pins[str(p)]=sha(p)
        source_plan=json.loads((frame.parent.parent.parent/'plan.json').read_bytes())
        pins.update(source_plan['input_sha256'])
    for p,d in pins.items():
        if sha(p)!=d:raise ValueError('source changed')
    out.mkdir(exist_ok=False)
    write(out/'plan.json',dict(input_sha256=pins,slots=plan['slots'],calibration_eligible=False,
        transform_source='recorded exact-time localization TF with source-bound static rendering correction; no evaluator truth input'))
    dr=[json.loads(s) for s in (detector/'results.jsonl').read_text().splitlines()]
    tr=[json.loads(s) for s in (ocr/'results.jsonl').read_text().splitlines()]
    rows=[];counts=Counter();support=defaultdict(Counter);statuses={c:Counter() for c in CLASSES}
    for slot,pred,text in zip(plan['slots'],dr,tr,strict=True):
        index=slot['source_index']
        if index!=pred['source_index'] or index!=text['source_index']:raise ValueError('order')
        row=dict(source_index=index,acquisition_category=slot['acquisition_category'],observations=[])
        if slot['status']!='ready':row['status']='retained_source_failure'
        else:
            frame=ROOT/slot['frame'];meta=json.loads(frame.read_bytes());req=json.loads((frame.parent.parent/'request.json').read_bytes())
            if req['partition']!='development' or req['protected_test_routes_used']:raise ValueError('scope')
            tf=meta['camera_to_map'];row['frame']=slot['frame']
            if not tf:row['status']='missing_localization_tf'
            elif meta['rgb_stamp_ns']!=meta['depth_stamp_ns']:row['status']='unsynchronized_rgbd'
            else:
                stamp=tf['header']['stamp'];stamp=stamp['sec']*10**9+stamp['nanosec']
                if stamp!=meta['rgb_stamp_ns'] or tf['header']['frame_id']!='map':raise ValueError('exact map TF required')
                p=tf['transform']['translation'];q=tf['transform']['rotation']
                nominal=matrix([p[k] for k in ('x','y','z')],[q[k] for k in ('x','y','z','w')])
                mount=json.loads((frame.parent.parent.parent/'plan.json').read_bytes())
                transform=correction(nominal,mount['nominal_mount'],mount['rendered_mount'])
                depth=decode_depth((frame.parent/meta['depth']['file']).read_bytes(),meta['depth'])
                scene=yaml.safe_load((Path(req['world_directory'])/'landmark_scene.yaml').read_bytes())
                refs=[dict(entity_id=e['entity_id'],category=e['category'],x=e['pose']['x'],y=e['pose']['y']) for e in scene['entities']]
                observations=associate_observations(localize(depth,np.asarray(meta['camera_info']['k']).reshape(3,3),transform,
                    pred['boxes'],text['texts'],camera_xy=transform[:2,3].tolist(),template='research3-readable-corridor-sign-v1'),refs)
                gate=frame_gate(observations)
                for c,value in gate.items():support[slot['acquisition_category']][c]+=int(value)
                for obs in observations:statuses[obs['visual_category']][obs['status']]+=1
                row.update(status='completed',observations=observations,necessary_geometry_gate=gate)
        counts[row['status']]+=1;rows.append(row)
    for p,d in pins.items():
        if sha(p)!=d:raise ValueError('source changed during replay')
    write(out/'results.json',dict(rows=rows,status_counts=counts,class_status_counts=statuses,
        supporting_frames_by_acquisition=support,calibration_eligible=False,human_labels_generated=False,
        identity_accuracy_verified=False,plan_sha256=sha(out/'plan.json'),independent_views=2))
    print(json.dumps(dict(status_counts=counts,support=support),indent=2))


if __name__=='__main__':main()
