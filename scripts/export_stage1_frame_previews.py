"""Lossless full-frame RGB previews for design inspection, not human review labels."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from expansion_rendered_checks import decode_frame
from run_stage1_feasibility import ROOT,sha,write
from summarize_stage1_four_workers import summarize


def export():
    report=summarize()
    if not report['complete']:raise ValueError('completed accounting required')
    output=ROOT/'reports/stage1_frame_previews_20260922_v1'
    output.mkdir(exist_ok=False)
    records=[]
    for attempt in report['rows']:
        record=dict(candidate_id=attempt['candidate_id'],status=attempt['status'],
            category=attempt['category'],entity_id=attempt['entity_id'],
            assigned_confidence=attempt['confidence'],human_verdict=None,semantic_correctness_verified=False)
        if attempt['status']!='infrastructure_failure':
            frame=ROOT/'reports/physical_live_episodes'/attempt['candidate_id']/'perception_capture/frame-000.json'
            rgb,metadata=decode_frame(frame)
            image_path=output/(attempt['candidate_id']+'.png')
            Image.fromarray(rgb).save(image_path)
            with Image.open(image_path) as image:
                if not np.array_equal(np.asarray(image),rgb):raise ValueError('preview is not a lossless RGB conversion')
            record.update(preview=image_path.name,preview_sha256=sha(image_path),source_frame_sha256=sha(frame),
                width=int(rgb.shape[1]),height=int(rgb.shape[0]),rgb_standard_deviation=float(rgb.std()),
                full_frame=True,overlays_added=False,cropped=False,lossless_rgb_verified=True)
        records.append(record)
    result=dict(schema_version='research3-design-frame-previews/v1',rows=records,
        scheduled=80,previews=sum('preview' in r for r in records),human_labels_generated=False,
        calibration_eligible=False,scope='Optional full-scene engineering inspection; not a calibration review request or a category/instance correctness attestation')
    write(output/'index.json',result)
    print(json.dumps(dict(previews=result['previews'],output=str(output))))


if __name__=='__main__':export()
