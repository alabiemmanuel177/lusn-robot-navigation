"""Bounded engineering checks; never primary data, labels, or protocol approval."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import numpy as np
from integrate_object_depth_candidate import ROOT, SOURCE, sha, write, decode_depth
from expansion_camera_model import verify_against_depth
from expansion_rendered_checks import decode_frame

OUT = ROOT/'reports/steps14_feasibility_20260923_v1'
PROMPTS = {'chair':'a photo of a chair', 'doorway':'a photo of a doorway',
           'laboratory_entrance':'a photo of a laboratory entrance',
           'office_entrance':'a photo of an office entrance',
           'sign':'a photo of a sign', 'background':'a photo of a wall'}


def temperature(p, t):
    if not np.isfinite(t) or t <= 0: raise ValueError('positive temperature')
    p = np.asarray(p, dtype=float)
    if not np.isfinite(p).all() or np.any((p <= 0) | (p >= 1)):
        raise ValueError('strict interior raw probabilities')
    return np.exp(-np.logaddexp(0., -np.log(p/(1-p))/t))


def prepare():
    original = json.loads((SOURCE/'plan.json').read_bytes())
    pins = {}
    def pin(path, expected=None):
        digest = sha(path)
        if expected is not None and digest != expected: raise ValueError(str(path))
        pins[str(path)] = digest
    for name in ('plan.json','results.jsonl','report.json','audit.json'):
        pin(SOURCE/name)
    for name in ('research3_steps14_feasibility.py','expansion_camera_model.py',
                 'expansion_rendered_checks.py','integrate_object_depth_candidate.py'):
        pin(ROOT/'scripts'/name)
    pin(ROOT/'docs/STEPS14_FEASIBILITY_PROTOCOL_20260923.md')
    slots=[]
    for slot in original['slots']:
        if slot['status'] != 'ready': slots.append(slot); continue
        frame = (ROOT/slot['frame']).resolve()
        if frame.parent.parent.parent != ROOT/'reports/physical_live_episodes' or not frame.parent.parent.name.startswith('r3-redesign-v2-design_feasibility-'):
            raise ValueError('not approved development namespace')
        reqpath = frame.parent.parent/'request.json'
        pin(reqpath, original['input_sha256'][str(reqpath)])
        req = json.loads(reqpath.read_bytes())
        if req['partition']!='development' or req['protected_test_routes_used'] or not req['capture_only']:
            raise ValueError('development stationary only')
        pin(frame, original['input_sha256'][str(frame)])
        meta = json.loads(frame.read_bytes())
        for channel in ('rgb','depth'):
            child = (frame.parent/meta[channel]['file']).resolve()
            if child.parent != frame.parent: raise ValueError('capture escape')
            pin(child, meta[channel]['sha256'])
        manifest = Path(req['world_directory'])/'manifest.json'
        if manifest.resolve().parent.parent != ROOT/'data/physical_worlds_readable_v1' or manifest.parent.name not in ('base-r001','base-r006'):
            raise ValueError('nondevelopment manifest')
        pin(manifest, req['asset_sha256']['manifest.json'])
        slots.append(dict(slot, manifest=str(manifest)))
    assets = ROOT/'reports/owlv2_candidate_assets_20260923_v1.json'
    pin(assets, original['model_asset_sha256'])
    metadata = json.loads(assets.read_bytes())
    for name,digest in metadata['files'].items(): pin(Path(original['model_path'])/name,digest)
    OUT.mkdir(exist_ok=False)
    write(OUT/'plan.json', dict(slots=slots, input_sha256=pins, prompts=PROMPTS,
        model_path=original['model_path'], threshold=.1, no_retries=True,
        calibration_eligible=False, human_labels_generated=False,
        scope='fixed short-prompt sensitivity and camera consistency; no candidate selection/freeze'))


def checked_plan():
    plan=json.loads((OUT/'plan.json').read_bytes())
    for name,digest in plan['input_sha256'].items():
        if sha(name)!=digest: raise ValueError('pinned input changed: '+name)
    return plan


def camera():
    plan=checked_plan(); results=[]
    for slot in plan['slots']:
        if slot['status']!='ready': results.append(slot); continue
        frame=ROOT/slot['frame'];rgb,meta=decode_frame(frame)
        depth=decode_depth((frame.parent/meta['depth']['file']).read_bytes(),meta['depth'])
        req=json.loads((frame.parent.parent/'request.json').read_bytes())
        walls=json.loads(Path(slot['manifest']).read_bytes())['layout']['walls']
        with np.errstate(invalid='ignore'):
            check=verify_against_depth(req['capture_pose'],depth,meta['camera_info'],rgb,walls)
        # The historical verifier accepts height-only evidence. Explicitly require
        # both horizontal axes as well; never call height-only evidence 3D validation.
        axes=all(k in check for k in ('height_residual','x_residual','y_residual'))
        nominal=meta['camera_to_map']['transform']['translation']
        offset=float(np.linalg.norm(np.array([nominal[k] for k in 'xyz'])-check['model_centre']))
        results.append(dict(source_index=slot['source_index'],status='completed',check=check,
            all_translation_axes_observed=axes,
            translation_consistency_pass=axes and check['max_abs_residual_m']<=.03,
            nominal_tf_translation_difference_m=offset,
            full_rigid_transform_independently_validated=False))
    checked_plan()
    write(OUT/'camera.json',dict(rows=results,completed=sum(r['status']=='completed' for r in results),
        all_axis_consistency_passes=sum(r.get('translation_consistency_pass',False) for r in results),
        all_axis_observed=sum(r.get('all_translation_axes_observed',False) for r in results),
        plan_sha256=sha(OUT/'plan.json'),full_metric_validation_passed=False))
    print(json.dumps({k:v for k,v in json.loads((OUT/'camera.json').read_bytes()).items() if k!='rows'}))


def probe():
    plan=checked_plan()
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.nice(19)
    import torch
    from PIL import Image
    from transformers import Owlv2Processor,Owlv2ForObjectDetection
    from language_nav.live_resources import coexistence_headroom
    torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.manual_seed(0)
    processor=Owlv2Processor.from_pretrained(plan['model_path'],local_files_only=True,trust_remote_code=False)
    model=Owlv2ForObjectDetection.from_pretrained(plan['model_path'],local_files_only=True,trust_remote_code=False,use_safetensors=True).eval()
    with torch.inference_mode(),(OUT/'short_prompt_results.jsonl').open('x') as stream:
        for i,slot in enumerate(plan['slots']):
            if slot['status']!='ready': result=dict(slot,boxes=[])
            else:
                coexistence_headroom()
                rgb,meta=decode_frame(ROOT/slot['frame'])
                inputs=processor(text=[list(plan['prompts'].values())],images=Image.fromarray(rgb),return_tensors='pt')
                raw=model(**inputs)
                path=OUT/f"short-{slot['source_index']:03}.npz"
                np.savez_compressed(path,logits=raw.logits.cpu().numpy(),pred_boxes=raw.pred_boxes.cpu().numpy())
                selected=processor.post_process_object_detection(raw,threshold=plan['threshold'],target_sizes=torch.tensor([[rgb.shape[0],rgb.shape[1]]]))[0]
                names=list(plan['prompts'])
                boxes=[dict(query=names[int(label)],score=float(score),xyxy=box.tolist()) for label,score,box in zip(selected['labels'],selected['scores'],selected['boxes'],strict=True)]
                result=dict(source_index=slot['source_index'],status='completed',boxes=boxes,raw_arrays=path.name,sha256=sha(path))
            stream.write(json.dumps(result,allow_nan=False)+'\n');stream.flush()
            print(f'Short-prompt check {i+1}/24',flush=True)
    checked_plan()


def summarize():
    plan=checked_plan(); names=list(plan['prompts']); panels={}
    for key,folder,journal,arraykey in [('original',SOURCE,'results.jsonl','raw_arrays_sha256'),('short',OUT,'short_prompt_results.jsonl','sha256')]:
        rows=[json.loads(x) for x in (folder/journal).read_text().splitlines()]
        if [r['source_index'] for r in rows]!=[r['source_index'] for r in plan['slots']]: raise ValueError('accounting')
        counts=Counter(); maxima=np.zeros(6); above=np.zeros(6,dtype=int); bins=np.zeros((6,3),dtype=int)
        for row in rows:
            if row['status']!='completed':continue
            path=folder/row['raw_arrays']
            if sha(path)!=row[arraykey]: raise ValueError('raw arrays changed')
            with np.load(path,allow_pickle=False) as arrays:
                scores=np.exp(-np.logaddexp(0.,-arrays['logits'][0].astype(float)))
            maxima=np.maximum(maxima,scores.max(0));above+=(scores>.1).sum(0)
            labels=scores.argmax(1); top=scores.max(1); kept=top>.1
            counts.update(names[int(label)] for label in labels[kept])
            for label,p in zip(labels[kept],top[kept]):bins[label,0 if p<.5 else 1 if p<.8 else 2]+=1
            if len(row['boxes'])!=int(kept.sum()):raise ValueError('display count reconstruction')
        panels[key]=dict(display_counts=counts,per_query_max=dict(zip(names,maxima.tolist())),
            all_query_scores_above_threshold=dict(zip(names,above.tolist())),
            raw_display_bins=dict(zip(names,bins.tolist())))
    write(OUT/'detector_score_audit.json',dict(panels=panels,plan_sha256=sha(OUT/'plan.json'),
        candidate_selected=False,accuracy_estimated=False,calibration_eligible=False,
        temperature_property='positive temperature preserves which side of 0.5 a score lies on',
        score_is_joint_probability=False,primary_freeze_allowed=False))
    print(json.dumps(panels,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('prepare','camera','probe','summarize'))
    globals()[parser.parse_args().action]()
