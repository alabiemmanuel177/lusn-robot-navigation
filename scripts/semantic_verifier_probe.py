"""Offline, design-only semantic evidence probe. No labels, calibration or ROS."""
import argparse
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import subprocess
import time
from PIL import Image,ImageOps

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'reports/semantic_verifier_probe_20260923_v1'
AUDIT=ROOT/'reports/redesign_stage_a_20260923_v1/independent_audit.json'
WEIGHTS=Path('/home/eao/.cache/huggingface/hub/models--laion--CLIP-ViT-B-32-laion2B-s34B-b79K/snapshots/1a25a446712ba5ee05982a381eed697ef9b435cf/open_clip_model.safetensors')
PROMPTS={
    'chair':'a chair with a seat, backrest and legs in an indoor corridor',
    'doorway':'an open doorway with a door frame leading into a room',
    'laboratory_entrance':'a laboratory entrance with a LAB sign above the opening',
    'office_entrance':'an office entrance with an OFFICE sign above the opening',
    'sign':'a sign or coloured panel on a wall without a visible entrance',
    'background':'a wall or floor without a visible chair, doorway or entrance',
}


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def write(path,value):
    with Path(path).open('x') as stream:json.dump(value,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')


def crop_box(width,height,u,v,size=256):
    if width<size or height<size or not all(math.isfinite(x) for x in (u,v)) or not (0<=u<width and 0<=v<height):
        raise ValueError('valid in-frame detector pixel and context size required')
    x=max(0,min(width-size,math.floor(u-size/2)));y=max(0,min(height-size,math.floor(v-size/2)))
    return (x,y,x+size,y+size)


def prepare():
    audit=json.loads(AUDIT.read_bytes())
    if not audit['passed'] or audit['scheduled']!=144:raise ValueError('complete Stage A integrity audit required')
    inputs={str(AUDIT):sha(AUDIT),str(Path(__file__).resolve()):sha(__file__),str(WEIGHTS):sha(WEIGHTS)};rows=[]
    for row in audit['rows']:
        if row['status']!='emitted':continue
        folder=ROOT/'reports/physical_live_episodes'/row['candidate_id']
        request=json.loads((folder/'request.json').read_bytes())
        if request['partition']!='development' or request['protected_test_routes_used'] is not False:
            raise ValueError('development only before image access')
        attempt=json.loads((folder/'expansion_attempt.json').read_bytes());obs=attempt['selected_observation']
        tasks=[json.loads(line) for line in (folder/'landmark_review_tasks.jsonl').read_text().splitlines()]
        matches=[t for t in tasks if t['observation_id']==obs['observation_id']]
        if len(matches)!=1:raise ValueError('unique actual detection location required')
        task=matches[0];frame=folder/'perception_capture/frame-000.json';metadata=json.loads(frame.read_bytes())
        box=crop_box(metadata['rgb']['width'],metadata['rgb']['height'],task['pixel']['u'],task['pixel']['v'])
        for path in (folder/'request.json',folder/'expansion_attempt.json',folder/'landmark_review_tasks.jsonl',frame,
                     frame.parent/metadata['rgb']['file']):inputs[str(path)]=sha(path)
        rows.append(dict(run_id=row['candidate_id'],observation_id=obs['observation_id'],
            provider_claim=row['category'],frame=str(frame.relative_to(ROOT)),context_box=list(box)))
    if len(rows)!=119:raise ValueError('all Stage A emissions, no confidence-based selection')
    OUTPUT.mkdir(exist_ok=False)
    write(OUTPUT/'plan.json',dict(schema_version='research3-semantic-verifier-probe-plan/v1',rows=rows,
        prompts=PROMPTS,views=['full_frame_letterbox','detector_centered_context_256'],model='ViT-B-32',
        checkpoint='laion2b_s34b_b79k',weights_path=str(WEIGHTS),input_sha256=inputs,
        device='cpu',threads=1,fit=False,temperature_tuning=False,calibration_eligible=False,
        source_selection='all_119_emissions_from_completed_design_only_Stage_A',
        limitations=['Marker-conditioned proposal locations; not an independent object detector',
            'Full-frame view may contain several categories; prompt rank is not localization',
            'Relative prompt softmax is not probability of category correctness',
            'No human labels or model admission; no change to live semantic observations']))
    print('Prepared all 119 emissions, fixed prompts and two views; no inference yet',flush=True)


def run():
    plan=json.loads((OUTPUT/'plan.json').read_bytes())
    for name,digest in plan['input_sha256'].items():
        if sha(name)!=digest:raise ValueError('probe input changed: '+name)
    if plan['prompts']!=PROMPTS or plan['device']!='cpu' or plan['threads']!=1:raise ValueError('fixed model/prompt/runtime scope')
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    os.nice(19)
    import torch
    import open_clip
    from expansion_rendered_checks import decode_frame
    from language_nav.live_resources import coexistence_headroom
    torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.manual_seed(0)
    if torch.version.cuda is not None or torch.version.hip is not None:raise ValueError('CPU-only isolated build required')
    model,_,preprocess=open_clip.create_model_and_transforms('ViT-B-32',pretrained=str(WEIGHTS),device='cpu')
    model.eval();tokenizer=open_clip.get_tokenizer('ViT-B-32')
    names=list(PROMPTS);started=time.time();results=[]
    with torch.inference_mode():
        text=model.encode_text(tokenizer(list(PROMPTS.values())));text=text/text.norm(dim=-1,keepdim=True)
        scale=float(model.logit_scale.exp())
        with (OUTPUT/'inference.jsonl').open('x') as journal:
            for index,row in enumerate(plan['rows']):
                coexistence_headroom()
                rgb,meta=decode_frame(ROOT/row['frame']);image=Image.fromarray(rgb)
                full=ImageOps.pad(image,(224,224),method=Image.Resampling.BICUBIC,color=(123,117,104))
                context=image.crop(tuple(row['context_box']))
                embeddings=model.encode_image(torch.stack([preprocess(full),preprocess(context)]))
                embeddings=embeddings/embeddings.norm(dim=-1,keepdim=True)
                cosine=embeddings@text.T;relative=(scale*cosine).softmax(dim=-1)
                for view,c,p in zip(plan['views'],cosine.tolist(),relative.tolist(),strict=True):
                    if not all(math.isfinite(v) for v in c+p):raise ValueError('nonfinite semantic output')
                    predicted=names[max(range(len(names)),key=lambda i:c[i])]
                    result=dict(row,view=view,cosine_similarity=dict(zip(names,c)),relative_prompt_softmax=dict(zip(names,p)),
                        top_prompt=predicted,prompt_agrees_with_provider_claim=predicted==row['provider_claim'],
                        human_verdict=None,correctness_verified=False,calibration_eligible=False)
                    journal.write(json.dumps(result,sort_keys=True,allow_nan=False)+'\n');journal.flush();results.append(result)
                if (index+1)%10==0:print(f'Semantic probe: {index+1}/119 observations',flush=True)
    write(OUTPUT/'report.json',dict(schema_version='research3-semantic-verifier-probe-report/v1',
        observations=len(plan['rows']),view_outputs=len(results),elapsed_s=time.time()-started,device='cpu',threads=1,
        learned_logit_scale=scale,learned_scale_changed=False,plan_sha256=sha(OUTPUT/'plan.json'),
        checkpoint_sha256=sha(WEIGHTS),journal_sha256=sha(OUTPUT/'inference.jsonl'),
        runtime_versions={p:importlib.metadata.version(p) for p in ('torch','torchvision','open_clip_torch','Pillow','numpy','safetensors')},
        human_labels_generated=False,calibration_eligible=False,live_provider_modified=False,
        primary_or_validation_data_used=False,protected_data_used=False,
        next_gate='inspect_semantic_evidence_and_define_prospective_method_before_any_runtime_integration'))
    packages=subprocess.check_output([str(Path(os.sys.executable)),'-m','pip','freeze'],text=True)
    with (OUTPUT/'runtime_freeze.txt').open('x') as stream:stream.write(packages)
    print('Semantic probe complete; no correctness or calibration claims',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'));args=p.parse_args()
    if args.action=='prepare':prepare()
    else:run()
