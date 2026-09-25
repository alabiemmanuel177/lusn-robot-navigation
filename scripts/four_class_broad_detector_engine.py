"""Fixed development-only Grounding DINO feasibility, with explicit label ambiguity."""
import argparse
import json
import os
import time
from pathlib import Path
from collections import Counter
import numpy as np
from integrate_object_depth_candidate import ROOT, SOURCE, sha, write
from expansion_rendered_checks import decode_frame

OUT=ROOT/'reports/grounding_candidate_20260923_v1'
ASSETS=ROOT/'reports/grounding_candidate_assets_20260923_v1.json'
QUERIES=['chair','doorway','laboratory entrance','office entrance','sign','wall']


def classify_label(label):
    # Exact whole phrase only. "entrance" or "laboratory office entrance" is
    # unresolved, never repaired with catalogue identity or an expected target.
    normalized=' '.join(label.strip().lower().split())
    mapping=dict(zip(QUERIES,['chair','doorway','laboratory_entrance','office_entrance','sign','background']))
    return mapping.get(normalized)


def reconstruct(logits,boxes,width,height,threshold=.1):
    if logits.ndim!=3 or logits.shape[0]!=1 or boxes.shape!=(1,logits.shape[1],4):raise ValueError('raw shape')
    # Negative infinity in padded text columns is a normal model mask.
    if np.isnan(logits).any() or np.isposinf(logits).any() or not np.isfinite(boxes).all():raise ValueError('invalid arrays')
    scores=np.exp(-np.logaddexp(0.,-logits[0].astype(float))).max(-1)
    corners=np.concatenate((boxes[0,:,:2]-boxes[0,:,2:]/2,boxes[0,:,:2]+boxes[0,:,2:]/2),axis=1)
    corners=corners*np.array([width,height,width,height])
    keep=scores>threshold
    return scores[keep],corners[keep]


def prepare():
    assets=json.loads(ASSETS.read_bytes());previous=json.loads((SOURCE/'plan.json').read_bytes())
    pins={str(p):sha(p) for p in (ASSETS,Path(__file__),ROOT/'docs/GROUNDING_CANDIDATE_PROTOCOL_20260923.md',SOURCE/'plan.json')}
    for name,digest in assets['files'].items():
        p=Path(assets['model_path'])/name
        if sha(p)!=digest:raise ValueError('asset checksum')
        pins[str(p)]=digest
    for slot in previous['slots']:
        if slot['status']!='ready':continue
        frame=(ROOT/slot['frame']).resolve()
        if frame.parent.parent.parent!=ROOT/'reports/physical_live_episodes' or not frame.parent.parent.name.startswith('r3-redesign-v2-design_feasibility-'):
            raise ValueError('outside development namespace')
        request=frame.parent.parent/'request.json'
        if sha(request)!=previous['input_sha256'][str(request)]:raise ValueError('request changed')
        req=json.loads(request.read_bytes())
        if req['partition']!='development' or req['protected_test_routes_used']:raise ValueError('scope')
        if sha(frame)!=previous['input_sha256'][str(frame)]:raise ValueError('frame changed')
        meta=json.loads(frame.read_bytes());rgb=frame.parent/meta['rgb']['file']
        if rgb.resolve().parent!=frame.parent or sha(rgb)!=meta['rgb']['sha256']:raise ValueError('RGB changed')
        for p in (frame,request,rgb):pins[str(p)]=sha(p)
    OUT.mkdir(exist_ok=False)
    write(OUT/'plan.json',dict(slots=previous['slots'],queries_ordered=QUERIES,
        text='. '.join(QUERIES)+'.',box_threshold=.1,text_threshold=.25,
        model_path=assets['model_path'],input_sha256=pins,
        query_policy='one fixed period-separated query string; no prompt/threshold sweep',
        calibration_eligible=False,protected_or_validation_data_used=False,retries=0))


def checked():
    plan=json.loads((OUT/'plan.json').read_bytes())
    for name,digest in plan['input_sha256'].items():
        if sha(name)!=digest:raise ValueError('pinned bytes changed: '+name)
    return plan


def run():
    plan=checked();os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.nice(19)
    import torch
    import importlib.metadata
    from PIL import Image
    from transformers import AutoProcessor,AutoModelForZeroShotObjectDetection
    from language_nav.live_resources import coexistence_headroom
    if torch.version.cuda is not None or torch.version.hip is not None:raise ValueError('CPU-only environment')
    torch.set_num_threads(4);torch.set_num_interop_threads(1);torch.manual_seed(0)
    processor=AutoProcessor.from_pretrained(plan['model_path'],local_files_only=True,trust_remote_code=False)
    model=AutoModelForZeroShotObjectDetection.from_pretrained(plan['model_path'],local_files_only=True,trust_remote_code=False,use_safetensors=True).eval()
    started=time.time()
    with torch.inference_mode(),(OUT/'results.jsonl').open('x') as stream:
        for i,slot in enumerate(plan['slots']):
            if slot['status']!='ready':row=dict(slot,boxes=[])
            else:
                guard=coexistence_headroom();begin=time.time()
                rgb,info=decode_frame(ROOT/slot['frame'])
                inputs=processor(images=Image.fromarray(rgb),text=plan['text'],return_tensors='pt')
                output=model(**inputs)
                arrays=OUT/f"source-{slot['source_index']:03}.npz"
                np.savez_compressed(arrays,logits=output.logits.cpu().numpy(),pred_boxes=output.pred_boxes.cpu().numpy(),input_ids=inputs.input_ids.cpu().numpy())
                processed=processor.post_process_grounded_object_detection(output,inputs.input_ids,threshold=plan['box_threshold'],text_threshold=plan['text_threshold'],target_sizes=[(rgb.shape[0],rgb.shape[1])])[0]
                boxes=[dict(text_label=label,visual_category=classify_label(label),raw_score=float(score),xyxy=box.tolist(),human_verdict=None,joint_probability=None) for label,score,box in zip(processed['text_labels'],processed['scores'],processed['boxes'],strict=True)]
                row=dict(source_index=slot['source_index'],status='completed',boxes=boxes,
                    raw_arrays=arrays.name,raw_sha256=sha(arrays),elapsed_s=time.time()-begin,resource_sample=guard)
            stream.write(json.dumps(row,allow_nan=False)+'\n');stream.flush()
            print(f'Broad readiness {i+1}/{len(plan["slots"])} slots',flush=True)
    checked()
    write(OUT/'report.json',dict(plan_sha256=sha(OUT/'plan.json'),journal_sha256=sha(OUT/'results.jsonl'),
        elapsed_s=time.time()-started,calibration_eligible=False,accuracy_estimated=False,
        versions={p:importlib.metadata.version(p) for p in ('torch','transformers','numpy','Pillow')}))


def audit():
    plan=checked();rows=[json.loads(s) for s in (OUT/'results.jsonl').read_text().splitlines()]
    if [r['source_index'] for r in rows]!=[s['source_index'] for s in plan['slots']]:raise ValueError('schedule mismatch')
    report=json.loads((OUT/'report.json').read_bytes())
    if report['plan_sha256']!=sha(OUT/'plan.json') or report['journal_sha256']!=sha(OUT/'results.jsonl'):raise ValueError('report binding')
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(plan['model_path'],local_files_only=True,trust_remote_code=False)
    counts=Counter();bins={q:[0,0,0] for q in ('chair','doorway','laboratory_entrance','office_entrance','sign','background','unresolved')}
    for slot,row in zip(plan['slots'],rows,strict=True):
        if slot['status']!='ready':
            if row!=dict(slot,boxes=[]):raise ValueError('failure changed')
            continue
        info=json.loads((ROOT/slot['frame']).read_bytes())['rgb'];path=OUT/row['raw_arrays']
        if sha(path)!=row['raw_sha256']:raise ValueError('raw changed')
        with np.load(path,allow_pickle=False) as raw:
            scores,boxes=reconstruct(raw['logits'],raw['pred_boxes'],info['width'],info['height'])
            probs=np.exp(-np.logaddexp(0.,-raw['logits'][0].astype(float)))
            masks=probs[probs.max(-1)>.1]>.25
            ids=raw['input_ids'][0]
            # Reproduce upstream phrase extraction: exclude first/last column.
            masks[:,0]=False;masks[:,-1]=False
            labels=[tokenizer.decode(ids[np.flatnonzero(mask)].tolist()) for mask in masks]
        for score,box,label,saved in zip(scores,boxes,labels,row['boxes'],strict=True):
            if abs(score-saved['raw_score'])>1e-6 or not np.allclose(box,saved['xyxy'],atol=1e-3,rtol=0) or label!=saved['text_label']:raise ValueError('reconstruction')
            category=classify_label(label)
            if category!=saved['visual_category'] or saved['human_verdict'] is not None or saved['joint_probability'] is not None:raise ValueError('contract')
            name=category or 'unresolved';counts[name]+=1;bins[name][0 if score<.5 else 1 if score<.8 else 2]+=1
    write(OUT/'audit.json',dict(reconstruction_passed=True,counts=counts,raw_score_bins=bins,
        completed_frames=sum(r['status']=='completed' for r in rows),retained_source_failures=sum(r['status']!='completed' for r in rows),
        candidate_admitted=False,calibration_eligible=False,accuracy_estimated=False,report_sha256=sha(OUT/'report.json')))
    print(json.dumps(dict(counts=counts,bins=bins),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run','audit'));globals()[p.parse_args().action]()
