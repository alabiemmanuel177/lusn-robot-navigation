"""Export lossless complete RGB frames and accounting, never human labels."""
import json
import numpy as np
from PIL import Image
from expansion_rendered_checks import decode_frame
from run_stage1_feasibility import ROOT,sha,write
from run_redesign_stage_a import assignments,OUTPUT


def export():
    output=OUTPUT/'previews';output.mkdir(exist_ok=True)
    records=[]
    for row in assignments():
        source=ROOT/'reports/physical_live_episodes'/row['candidate_id']/'perception_capture/frame-000.json'
        if not source.exists():continue
        rgb,metadata=decode_frame(source)
        target=output/(row['candidate_id']+'.png')
        if not target.exists():Image.fromarray(rgb).save(target)
        with Image.open(target) as image:
            if not np.array_equal(np.asarray(image),rgb):raise ValueError('lossless full-frame check')
        records.append(dict(candidate_id=row['candidate_id'],preview=str(target.relative_to(ROOT)),
            preview_sha256=sha(target),source_frame_sha256=sha(source),human_verdict=None,
            cropped=False,overlays_added=False,lossless_rgb_verified=True))
    report=dict(previews=len(records),records=records,human_labels_generated=False)
    if all((OUTPUT/(r['candidate_id']+'.result.json')).exists() for r in assignments()):
        write(output/'index.json',report)
    print(json.dumps(dict(previews=len(records),human_labels_generated=False)))


if __name__=='__main__':export()
