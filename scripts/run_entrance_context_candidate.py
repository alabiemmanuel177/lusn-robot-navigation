"""One fixed full-scene OCR replay; preserve all 24 slots and all raw OCR results."""
import importlib.metadata
import json
import os
from pathlib import Path
from collections import Counter
from integrate_object_depth_candidate import ROOT, sha, write
import numpy as np
from entrance_context_candidate import contextual_candidates

OUT=ROOT/'reports/entrance_context_candidate_20260924_v1'
SOURCE=ROOT/'reports/grounding_candidate_20260923_v3'


def decode_frame(path):
    meta=json.loads(path.read_bytes());rgb=meta['rgb'];raw=path.parent/rgb['file']
    if raw.resolve().parent!=path.parent.resolve() or sha(raw)!=rgb['sha256']:
        raise ValueError('RGB integrity')
    if rgb['encoding'] not in ('rgb8','bgr8'):raise ValueError('RGB encoding')
    array=np.frombuffer(raw.read_bytes(),dtype=np.uint8).reshape(rgb['height'],rgb['step'])[:,:rgb['width']*3]
    array=array.reshape(rgb['height'],rgb['width'],3)
    if rgb['encoding']=='bgr8':array=array[:,:,::-1]
    return np.ascontiguousarray(array),meta


def main():
    import rapidocr_onnxruntime
    from rapidocr_onnxruntime import RapidOCR
    os.nice(19)
    source=json.loads((SOURCE/'plan.json').read_bytes())
    for path,digest in source['input_sha256'].items():
        if sha(path)!=digest:raise ValueError('source pin changed: '+path)
    rows=[json.loads(s) for s in (SOURCE/'results.jsonl').read_text().splitlines()]
    report=json.loads((SOURCE/'report.json').read_bytes())
    if report['journal_sha256']!=sha(SOURCE/'results.jsonl'):raise ValueError('journal binding')
    package=Path(rapidocr_onnxruntime.__file__).parent
    pins={str(p):sha(p) for p in package.rglob('*') if p.is_file() and p.suffix in ('.onnx','.yaml','.py','.txt')}
    for p in (Path(__file__),ROOT/'scripts/entrance_context_candidate.py',SOURCE/'plan.json',SOURCE/'results.jsonl'):
        pins[str(p.resolve())]=sha(p)
    OUT.mkdir(exist_ok=False)
    settings=dict(intra_op_num_threads=1,inter_op_num_threads=1,
                  det_use_cuda=False,cls_use_cuda=False,rec_use_cuda=False,text_score=.5)
    write(OUT/'plan.json',dict(slots=source['slots'],input_sha256=pins,
        settings=settings,versions={p:importlib.metadata.version(p) for p in ('rapidocr-onnxruntime','onnxruntime','numpy')},
        calibration_eligible=False,protected_or_validation_data_used=False,
        text_policy='exact LAB, LABORATORY, OFFICE; no fuzzy matching; full RGB scene; no target/catalogue inputs'))
    engine=RapidOCR(**settings)
    counts=Counter()
    with (OUT/'results.jsonl').open('x') as stream:
        for slot,row in zip(source['slots'],rows,strict=True):
            if slot['source_index']!=row['source_index']:raise ValueError('slot order')
            if slot['status']!='ready':result=dict(source_index=slot['source_index'],status='retained_source_failure')
            else:
                rgb,_=decode_frame(ROOT/slot['frame'])
                raw,elapsed=engine(rgb[:,:,::-1].copy())
                texts=[dict(quad=quad,text=text,score=float(score)) for quad,text,score in (raw or [])]
                doors=[b for b in row['boxes'] if b['visual_category']=='doorway']
                candidates=contextual_candidates(doors,texts)
                counts.update(c['status'] for c in candidates)
                result=dict(source_index=slot['source_index'],status='completed',texts=texts,
                            doorway_candidates=candidates,ocr_elapsed_s=elapsed)
            stream.write(json.dumps(result,allow_nan=False)+'\n');stream.flush()
            print('OCR slot',slot['source_index'],result['status'],flush=True)
    for path,digest in pins.items():
        if sha(path)!=digest:raise ValueError('input changed during replay')
    write(OUT/'report.json',dict(plan_sha256=sha(OUT/'plan.json'),journal_sha256=sha(OUT/'results.jsonl'),
        candidate_status_counts=counts,calibration_eligible=False,human_labels_generated=False))


if __name__=='__main__':main()
