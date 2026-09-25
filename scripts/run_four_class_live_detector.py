"""All twenty context frames from each of four prespecified fresh live views."""
import argparse
import json
from pathlib import Path
from integrate_object_depth_candidate import ROOT,sha,write
import four_class_broad_detector_engine as engine

OUT=ROOT/'reports/four_class_live_detector_20260924_v1'
CAPTURE=ROOT/'reports/four_class_live_capture_20260924_v1'


def prepare():
    schedule=json.loads((CAPTURE/'schedule.json').read_bytes())
    ap=ROOT/'reports/grounding_candidate_assets_20260923_v3.json';assets=json.loads(ap.read_bytes())
    pins={str(p.resolve()):sha(p) for p in (ap,Path(__file__),ROOT/'scripts/four_class_broad_detector_engine.py',CAPTURE/'schedule.json')}
    for name,digest in assets['files'].items():
        p=Path(assets['model_path'])/name
        if sha(p)!=digest:raise ValueError('model binding')
        pins[str(p)]=digest
    slots=[]
    for i,view in enumerate(schedule['views']):
        run=CAPTURE/f"view-{i:02}-{view['category']}"
        if not (run/'execution.json').exists() and not (run/'execution_failure.json').exists():raise ValueError('capture not finished')
        for j in range(20):
            frame=run/f'episode/context_capture/frame-{j:03}.json'
            slot=dict(source_index=len(slots),status='retained_source_failure',acquisition_category=view['category'])
            if frame.exists():
                meta=json.loads(frame.read_bytes());request=run/'episode/request.json';req=json.loads(request.read_bytes())
                if req['partition']!='development' or req['protected_test_routes_used']:raise ValueError('scope')
                media=frame.parent/meta['rgb']['file']
                if media.resolve().parent!=frame.parent or sha(media)!=meta['rgb']['sha256']:raise ValueError('media integrity')
                for p in (frame,request,media,run/'plan.json'):pins[str(p)]=sha(p)
                slot.update(status='ready',frame=str(frame.relative_to(ROOT)))
            slots.append(slot)
    OUT.mkdir(exist_ok=False)
    write(OUT/'plan.json',dict(slots=slots,input_sha256=pins,model_path=assets['model_path'],
        queries_ordered=engine.QUERIES,text='. '.join(engine.QUERIES)+'.',box_threshold=.1,text_threshold=.25,
        threads=4,device='cpu',calibration_eligible=False,independent_views=4,
        repeated_frames_are_not_independent_trials=True,protected_or_validation_data_used=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run','audit'));action=p.parse_args().action
    engine.OUT=OUT
    if action=='prepare':prepare()
    else:getattr(engine,action)()
