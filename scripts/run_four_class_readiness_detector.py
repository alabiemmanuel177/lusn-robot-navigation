"""All 144 existing development slots, unchanged checkpoint/prompts/thresholds."""
import argparse
import json
from pathlib import Path
from integrate_object_depth_candidate import ROOT,sha,write
import run_grounding_candidate as engine

OUT=ROOT/'reports/four_class_readiness_detector_20260924_v1'
ASSETS=ROOT/'reports/grounding_candidate_assets_20260923_v3.json'


def prepare():
    historical=ROOT/'reports/catalogue_blind_candidate_20260923_v1/plan.json'
    old=json.loads(historical.read_bytes());assets=json.loads(ASSETS.read_bytes())
    for name,digest in old['input_sha256'].items():
        if sha(ROOT/name)!=digest:raise ValueError('historical input changed: '+name)
    frames={f['frame_index']:f['frame'] for f in old['frames']}
    if len(frames)!=141 or set(frames)-set(range(144)):raise ValueError('fixed panel accounting')
    pins={str(p.resolve()):sha(p) for p in (historical,ASSETS,Path(__file__),ROOT/'scripts/run_grounding_candidate.py',
        ROOT/'reports/world_specific_method_approval_20260924.json',ROOT/'docs/REFERENCE_METHOD_DECISION_20260924.md')}
    for name,digest in assets['files'].items():
        p=Path(assets['model_path'])/name
        if sha(p)!=digest:raise ValueError('checkpoint changed')
        pins[str(p)]=digest
    slots=[]
    for index in range(144):
        if index not in frames:slots.append(dict(source_index=index,status='retained_source_failure'));continue
        frame=(ROOT/frames[index]).resolve();request=frame.parent.parent/'request.json'
        req=json.loads(request.read_bytes());meta=json.loads(frame.read_bytes())
        if req['partition']!='development' or req['protected_test_routes_used']:raise ValueError('scope')
        media=frame.parent/meta['rgb']['file']
        if media.resolve().parent!=frame.parent or sha(media)!=meta['rgb']['sha256']:raise ValueError('RGB integrity')
        for p in (frame,request,media):pins[str(p)]=sha(p)
        slots.append(dict(source_index=index,status='ready',frame=str(frame.relative_to(ROOT))))
    OUT.mkdir(exist_ok=False)
    write(OUT/'plan.json',dict(slots=slots,queries_ordered=engine.QUERIES,text='. '.join(engine.QUERIES)+'.',
        box_threshold=.1,text_threshold=.25,model_path=assets['model_path'],input_sha256=pins,
        scope='complete existing development engineering panel; not calibration or held-out evidence',
        calibration_eligible=False,protected_or_validation_data_used=False,retries=0))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run','audit','integrate'));action=p.parse_args().action
    engine.OUT=OUT
    if action=='prepare':prepare()
    elif action=='integrate':
        import integrate_grounding_candidate as integration
        integration.OUT=OUT;integration.main()
    else:getattr(engine,action)()
