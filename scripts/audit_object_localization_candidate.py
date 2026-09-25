"""Reconstruct display detections from retained arrays, without model reruns."""
from collections import Counter
import json
import numpy as np
from run_object_localization_candidate import OUTPUT, ROOT
from catalogue_blind_regions import PROMPTS
from run_stage1_feasibility import sha,write


def reconstruct(logits,boxes,width,height,threshold):
    if logits.ndim!=3 or logits.shape[0]!=1 or logits.shape[2]!=len(PROMPTS):raise ValueError('logit dimensions')
    if boxes.shape!=(1,logits.shape[1],4):raise ValueError('box dimensions')
    if not np.isfinite(logits).all() or not np.isfinite(boxes).all():raise ValueError('finite raw arrays')
    labels=logits[0].argmax(-1); values=logits[0].max(-1).astype(np.float64)
    scores=np.exp(-np.logaddexp(0.,-values))
    centres=boxes[0,:,:2];sizes=boxes[0,:,2:]
    # OWLv2 pads to a square before inference: both axes use max(H,W).
    corners=np.concatenate((centres-sizes/2,centres+sizes/2),axis=-1)*max(width,height)
    keep=scores>threshold
    return labels[keep],scores[keep],corners[keep]


def main():
    plan=json.loads((OUTPUT/'plan.json').read_bytes());report=json.loads((OUTPUT/'report.json').read_bytes())
    if report['plan_sha256']!=sha(OUTPUT/'plan.json') or report['journal_sha256']!=sha(OUTPUT/'results.jsonl'):
        raise ValueError('run binding')
    results=[json.loads(line) for line in (OUTPUT/'results.jsonl').read_text().splitlines()]
    if len(results)!=24 or [r['source_index'] for r in results]!=[s['source_index'] for s in plan['slots']]:
        raise ValueError('fixed source accounting')
    counts=Counter();empty=0;outside=0;total=0;durations=[];names=list(PROMPTS)
    for slot,row in zip(plan['slots'],results,strict=True):
        if slot['status']!='ready':
            if row!=dict(slot,boxes=[],human_verdict=None):raise ValueError('historical failure changed')
            continue
        if row['status']!='completed' or row['object_identity_verified'] or row['calibration_eligible']:
            raise ValueError('candidate scope')
        path=OUTPUT/row['raw_arrays']
        if sha(path)!=row['raw_arrays_sha256']:raise ValueError('raw arrays changed')
        info=json.loads((ROOT/slot['frame']).read_bytes())['rgb'];w,h=info['width'],info['height']
        with np.load(path,allow_pickle=False) as raw:
            labels,scores,boxes=reconstruct(raw['logits'],raw['pred_boxes'],w,h,plan['display_threshold'])
        if len(labels)!=len(row['boxes']):raise ValueError('display count')
        for label,score,box,actual in zip(labels,scores,boxes,row['boxes'],strict=True):
            if actual['query']!=names[int(label)] or abs(score-actual['raw_score'])>1e-6 or not np.allclose(box,actual['xyxy'],atol=1e-3,rtol=0):
                raise ValueError('display output reconstruction')
            if any(actual[k] is not None for k in ('entity_id','map_pose','joint_correctness_probability','human_verdict')):
                raise ValueError('fabricated identity/pose/probability/verdict')
            counts[actual['query']]+=1;total+=1
            outside+=int(box[0]<0 or box[1]<0 or box[2]>w or box[3]>h)
        empty+=int(len(labels)==0);durations.append(row['elapsed_s'])
    result=dict(integrity_passed=True,scheduled_source_slots=24,completed_frames=len(durations),
        retained_source_failures=24-len(durations),display_box_count=total,query_counts=counts,
        frames_without_display_boxes=empty,unclipped_boxes_extending_outside_image=outside,
        mean_frame_elapsed_s=sum(durations)/len(durations),all_display_outputs_reproduced=True,
        human_labels_generated=False,accuracy_estimated=False,calibration_eligible=False,
        metric_localization_established=False,duplicates_suppressed=False,report_sha256=sha(OUTPUT/'report.json'))
    write(OUTPUT/'audit.json',result);print(json.dumps(result))


if __name__=='__main__':main()
