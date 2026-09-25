"""Bounded, pinned offline RGB-only inference; no calibration or ROS publishing."""
import argparse
import importlib.metadata
import json
import math
import os
from pathlib import Path
import time
from catalogue_blind_regions import PROMPTS, regions, evidence
from run_stage1_feasibility import ROOT, sha, write

OUTPUT = ROOT / 'reports/catalogue_blind_candidate_20260923_v1'
AUDIT = ROOT / 'reports/redesign_stage_a_20260923_v1/independent_audit.json'
WEIGHTS = Path('/home/eao/.cache/huggingface/hub/models--laion--CLIP-ViT-B-32-laion2B-s34B-b79K/snapshots/1a25a446712ba5ee05982a381eed697ef9b435cf/open_clip_model.safetensors')


def prepare():
    audit = json.loads(AUDIT.read_bytes())
    if not audit['passed'] or audit['scheduled'] != 144:
        raise ValueError('complete historical engineering audit required')
    inputs = {str(p): sha(p) for p in (AUDIT, WEIGHTS, Path(__file__),
        ROOT/'scripts/catalogue_blind_regions.py', ROOT/'docs/CATALOGUE_BLIND_CANDIDATE_20260923.md')}
    frames, failures = [], []
    for index, row in enumerate(audit['rows']):
        if row['status'] == 'infrastructure_failure':
            failures.append(row['candidate_id'])
            continue
        run = ROOT/'reports/physical_live_episodes'/row['candidate_id']
        request = json.loads((run/'request.json').read_bytes())
        if request['partition'] != 'development' or request['protected_test_routes_used'] is not False:
            raise ValueError('development only before image access')
        frame = run/'perception_capture/frame-000.json'
        metadata = json.loads(frame.read_bytes())
        rgb = frame.parent/metadata['rgb']['file']
        if sha(rgb) != metadata['rgb']['sha256']:
            raise ValueError('RGB checksum mismatch')
        for path in (run/'request.json', frame, rgb): inputs[str(path)] = sha(path)
        frames.append(dict(frame_index=index, frame=str(frame.relative_to(ROOT)),
                           regions=regions(metadata['rgb']['width'], metadata['rgb']['height'])))
    if len(frames) != 141 or len(failures) != 3:
        raise ValueError('fixed intact-frame accounting')
    OUTPUT.mkdir(exist_ok=False)
    write(OUTPUT/'plan.json', dict(frames=frames, retained_infrastructure_failures=failures,
        input_sha256=inputs, prompts=PROMPTS, scheduled_vectors=1410,
        device='cpu', threads=1, fitting=False, calibration_eligible=False,
        inference_reads_catalogue=False, inference_uses_detector_pixels=False,
        sampling_was_catalogue_directed=True))


def run():
    plan = json.loads((OUTPUT/'plan.json').read_bytes())
    for name, digest in plan['input_sha256'].items():
        if sha(name) != digest: raise ValueError('pinned input changed: '+name)
    if plan['prompts'] != PROMPTS: raise ValueError('prompt drift')
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.nice(19)
    import torch
    import open_clip
    from PIL import Image, ImageOps
    from language_nav.live_resources import coexistence_headroom
    if torch.version.cuda is not None or torch.version.hip is not None:
        raise ValueError('isolated CPU-only build required')
    torch.set_num_threads(1); torch.set_num_interop_threads(1); torch.manual_seed(0)
    model, _, preprocess = open_clip.create_model_and_transforms('ViT-B-32', pretrained=str(WEIGHTS), device='cpu')
    model.eval()
    names = list(PROMPTS); count = 0; started = time.time()
    with torch.inference_mode(), (OUTPUT/'vectors.jsonl').open('x') as journal:
        texts = model.encode_text(open_clip.get_tokenizer('ViT-B-32')(list(PROMPTS.values())))
        texts = texts/texts.norm(dim=-1, keepdim=True)
        scale = float(model.logit_scale.exp())
        for i, row in enumerate(plan['frames']):
            coexistence_headroom()
            # Read RGB alone; no task, observation, catalogue, detector pixel or depth inputs.
            frame = ROOT/row['frame']; info = json.loads(frame.read_bytes())['rgb']
            raw = (frame.parent/info['file']).read_bytes()
            import hashlib
            if hashlib.sha256(raw).hexdigest() != info['sha256']: raise ValueError('image changed')
            mode = {'rgb8':'RGB', 'bgr8':'BGR'}[info['encoding']]
            image = Image.frombytes('RGB', (info['width'], info['height']), raw, 'raw', mode, info['step'], 1)
            crops = [preprocess(ImageOps.pad(image.crop(tuple(box)), (224,224),
                method=Image.Resampling.BICUBIC, color=(123,117,104))) for _, box in row['regions']]
            vectors = model.encode_image(torch.stack(crops))
            vectors = vectors/vectors.norm(dim=-1, keepdim=True)
            cosines = (vectors@texts.T).tolist()
            for (name, box), values in zip(row['regions'], cosines, strict=True):
                result = evidence(name, box, dict(zip(names, values)), scale)
                result['frame_index'] = row['frame_index']
                journal.write(json.dumps(result, sort_keys=True, allow_nan=False)+'\n'); count += 1
            journal.flush()
            if (i+1)%20 == 0: print(f'Catalogue-blind frames: {i+1}/141', flush=True)
    if count != 1410: raise ValueError('incomplete fixed panel')
    write(OUTPUT/'report.json', dict(vectors=count, frames=141, elapsed_s=time.time()-started,
        plan_sha256=sha(OUTPUT/'plan.json'), vectors_sha256=sha(OUTPUT/'vectors.jsonl'),
        checkpoint_sha256=sha(WEIGHTS), learned_logit_scale=scale, device='cpu', threads=1,
        runtime_versions={p:importlib.metadata.version(p) for p in ('torch','torchvision','open_clip_torch','Pillow')},
        human_labels_generated=False, calibration_eligible=False, live_runtime_modified=False,
        protected_or_validation_data_read=False))
    print('Complete: 1410 unlabelled region vectors; no localized semantic observations.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=('prepare','run'))
    args = parser.parse_args()
    prepare() if args.action == 'prepare' else run()
