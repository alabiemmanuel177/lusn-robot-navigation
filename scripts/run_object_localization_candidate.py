"""Fixed R3-only object-box probe; no catalogue assignment, map pose or labels."""
import argparse
import json
import os
import time
from pathlib import Path
from catalogue_blind_regions import PROMPTS
from run_stage1_feasibility import ROOT,sha,write

OUTPUT=ROOT/'reports/object_localization_candidate_20260923_v1'
ASSETS=ROOT/'reports/owlv2_candidate_assets_20260923_v1.json'
AUDIT=ROOT/'reports/redesign_stage_a_20260923_v1/independent_audit.json'


def prepare():
    asset=json.loads(ASSETS.read_bytes()); model=ROOT/'.research_models/owlv2-base-patch16-ensemble'/asset['revision']
    for name,digest in asset['files'].items():
        if sha(model/name)!=digest:raise ValueError('model asset changed')
    audit=json.loads(AUDIT.read_bytes())
    if not audit['passed'] or len(audit['rows'])!=144:raise ValueError('complete original audit required')
    inputs={str(p):sha(p) for p in (ASSETS,AUDIT,Path(__file__),ROOT/'scripts/catalogue_blind_regions.py',
        ROOT/'docs/OBJECT_LOCALIZATION_CANDIDATE_20260923.md')};slots=[]
    for i in range(0,144,6):
        row=audit['rows'][i]
        if row['status']=='infrastructure_failure':slots.append(dict(source_index=i,status='retained_source_failure'));continue
        folder=ROOT/'reports/physical_live_episodes'/row['candidate_id']
        request=json.loads((folder/'request.json').read_bytes())
        if request['partition']!='development' or request['protected_test_routes_used'] is not False:raise ValueError('scope')
        frame=folder/'perception_capture/frame-000.json';info=json.loads(frame.read_bytes())['rgb'];rgb=frame.parent/info['file']
        if sha(rgb)!=info['sha256']:raise ValueError('RGB integrity')
        for p in (folder/'request.json',frame,rgb):inputs[str(p)]=sha(p)
        slots.append(dict(source_index=i,status='ready',frame=str(frame.relative_to(ROOT))))
    OUTPUT.mkdir(exist_ok=False)
    write(OUTPUT/'plan.json',dict(slots=slots,model_path=str(model),model_asset_sha256=sha(ASSETS),
        input_sha256=inputs,prompts=PROMPTS,display_threshold=.1,scheduled_source_slots=24,
        retries=0,calibration_eligible=False,fit=False,protected_or_validation_data_read=False))
    print(json.dumps(dict(slots=24,ready=sum(r['status']=='ready' for r in slots))))


def run():
    import hashlib
    import importlib.metadata
    import subprocess
    plan=json.loads((OUTPUT/'plan.json').read_bytes())
    for name,digest in plan['input_sha256'].items():
        if sha(name)!=digest:raise ValueError('pinned source/input changed')
    assets=json.loads(ASSETS.read_bytes())
    for name,digest in assets['files'].items():
        if sha(Path(plan['model_path'])/name)!=digest:raise ValueError('pinned model changed')
    if plan['prompts']!=PROMPTS:raise ValueError('fixed prompts required')
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.nice(19)
    import torch
    import numpy as np
    from PIL import Image
    from transformers import Owlv2Processor, Owlv2ForObjectDetection
    from language_nav.live_resources import coexistence_headroom
    if torch.version.cuda is not None or torch.version.hip is not None:raise ValueError('CPU-only build')
    torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.manual_seed(0)
    processor=Owlv2Processor.from_pretrained(plan['model_path'],local_files_only=True,trust_remote_code=False)
    model=Owlv2ForObjectDetection.from_pretrained(plan['model_path'],local_files_only=True,trust_remote_code=False,use_safetensors=True)
    model.eval(); names=list(PROMPTS);results=[];started=time.time()
    with torch.inference_mode(),(OUTPUT/'results.jsonl').open('x') as stream:
        for slot in plan['slots']:
            if slot['status']!='ready':
                result=dict(slot,boxes=[],human_verdict=None)
            else:
                coexistence_headroom();t=time.time();frame=ROOT/slot['frame'];info=json.loads(frame.read_bytes())['rgb']
                raw=(frame.parent/info['file']).read_bytes()
                if hashlib.sha256(raw).hexdigest()!=info['sha256']:raise ValueError('RGB changed')
                image=Image.frombytes('RGB',(info['width'],info['height']),raw,'raw',{'rgb8':'RGB','bgr8':'BGR'}[info['encoding']],info['step'],1)
                inputs=processor(text=[list(PROMPTS.values())],images=image,return_tensors='pt')
                outputs=model(**inputs)
                raw_path=OUTPUT/f"source-{slot['source_index']:03}-raw.npz"
                np.savez_compressed(raw_path,logits=outputs.logits.cpu().numpy(),pred_boxes=outputs.pred_boxes.cpu().numpy())
                selected=processor.post_process_object_detection(outputs,threshold=plan['display_threshold'],
                    target_sizes=torch.tensor([[image.height,image.width]]))[0]
                boxes=[dict(query=names[int(label)],raw_score=float(score),xyxy=box.tolist(),entity_id=None,map_pose=None,
                    joint_correctness_probability=None,human_verdict=None) for box,score,label in zip(selected['boxes'],selected['scores'],selected['labels'],strict=True)]
                result=dict(source_index=slot['source_index'],status='completed',elapsed_s=time.time()-t,boxes=boxes,
                    raw_arrays=raw_path.name,raw_arrays_sha256=sha(raw_path),object_identity_verified=False,calibration_eligible=False)
            stream.write(json.dumps(result,sort_keys=True,allow_nan=False)+'\n');stream.flush();results.append(result)
            print(f"Object probe: {len(results)}/24 slots",flush=True)
    write(OUTPUT/'report.json',dict(slots=len(results),completed=sum(r['status']=='completed' for r in results),
        elapsed_s=time.time()-started,plan_sha256=sha(OUTPUT/'plan.json'),journal_sha256=sha(OUTPUT/'results.jsonl'),
        model_asset_sha256=sha(ASSETS),versions={p:importlib.metadata.version(p) for p in ('torch','torchvision','transformers','Pillow')},
        human_labels_generated=False,calibration_eligible=False,live_runtime_modified=False,protected_data_read=False))
    with (OUTPUT/'runtime_freeze.txt').open('x') as f:f.write(subprocess.check_output([os.sys.executable,'-m','pip','freeze'],text=True))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'));a=p.parse_args()
    prepare() if a.action=='prepare' else run()
