"""Eighty prespecified original development captures; never their human labels."""
import argparse
import json
from pathlib import Path
from integrate_object_depth_candidate import ROOT,sha,write
import four_class_broad_detector_engine as engine

OUT=ROOT/'reports/four_class_broad_detector_20260924_v1'


def prepare():
    assets_path=ROOT/'reports/grounding_candidate_assets_20260923_v3.json'
    assets=json.loads(assets_path.read_bytes())
    pins={str(p.resolve()):sha(p) for p in (assets_path,Path(__file__),ROOT/'scripts/four_class_broad_detector_engine.py',
        ROOT/'docs/FOUR_CLASS_READINESS_PROTOCOL_20260924.md',ROOT/'reports/world_specific_method_approval_20260924.json')}
    for name,digest in assets['files'].items():
        p=Path(assets['model_path'])/name
        if sha(p)!=digest:raise ValueError('asset changed')
        pins[str(p)]=digest
    slots=[]
    for m in range(1,11):
        for category in ('chair','doorway','laboratory_entrance','office_entrance'):
            for view in (0,1):
                run=ROOT/f'reports/physical_live_episodes/expansion-v1-r{m:03}-{category}-s1-view{view}'
                frame=run/'perception_capture/frame-000.json'
                slot=dict(source_index=len(slots),acquisition_category=category,map_id=f'r{m:03}',status='retained_source_failure')
                if frame.exists():
                    request=run/'request.json';req=json.loads(request.read_bytes());meta=json.loads(frame.read_bytes())
                    if req['partition']!='development' or req['protected_test_routes_used']:raise ValueError('scope')
                    media=frame.parent/meta['rgb']['file']
                    if media.resolve().parent!=frame.parent or sha(media)!=meta['rgb']['sha256']:raise ValueError('RGB')
                    for p in (request,frame,media):pins[str(p)]=sha(p)
                    slot.update(status='ready',frame=str(frame.relative_to(ROOT)))
                slots.append(slot)
    OUT.mkdir(exist_ok=False)
    write(OUT/'plan.json',dict(slots=slots,input_sha256=pins,model_path=assets['model_path'],
        queries_ordered=engine.QUERIES,text='. '.join(engine.QUERIES)+'.',box_threshold=.1,text_threshold=.25,
        threads=4,device='cpu',calibration_eligible=False,uses_original_human_labels=False,
        protected_or_validation_data_used=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('prepare','run','audit'))
    action=parser.parse_args().action;engine.OUT=OUT
    if action=='prepare':prepare()
    else:getattr(engine,action)()
