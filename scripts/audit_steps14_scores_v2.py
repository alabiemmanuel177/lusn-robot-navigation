"""Supersede the initial cross-panel summary using each run's actual query order."""
from collections import Counter
import json
import numpy as np
from catalogue_blind_regions import PROMPTS as ORIGINAL_PROMPTS
from research3_steps14_feasibility import OUT, checked_plan
from integrate_object_depth_candidate import SOURCE, ROOT, sha, write


def summarize_arrays(logits, names):
    if logits.ndim!=3 or logits.shape[0]!=1 or logits.shape[2]!=len(names) or len(set(names))!=len(names):
        raise ValueError('explicit unique query order must match logits')
    scores=np.exp(-np.logaddexp(0.,-logits[0].astype(float)))
    if not np.isfinite(scores).all():raise ValueError('finite logits required')
    labels=scores.argmax(1);top=scores.max(1);keep=top>.1
    emitted=[names[int(i)] for i in labels[keep]]
    bins={n:[0,0,0] for n in names}
    for label,p in zip(emitted,top[keep],strict=True):bins[label][0 if p<.5 else 1 if p<.8 else 2]+=1
    return dict(query_order=names,emitted=emitted,bins=bins,
        maxima=dict(zip(names,scores.max(0).tolist())),
        above=dict(zip(names,(scores>.1).sum(0).tolist())))


def main():
    plan=checked_plan();original=json.loads((SOURCE/'plan.json').read_bytes())
    source=ROOT/'scripts/catalogue_blind_regions.py'
    if sha(source)!=original['input_sha256'][str(source)]:raise ValueError('historical prompt source changed')
    panels={}
    for label,folder,journal,hashkey,names in (
        ('original',SOURCE,'results.jsonl','raw_arrays_sha256',list(ORIGINAL_PROMPTS)),
        ('short',OUT,'short_prompt_results.jsonl','sha256',list(plan['prompts']))):
        rows=[json.loads(s) for s in (folder/journal).read_text().splitlines()]
        counts=Counter();bins={n:[0,0,0] for n in names};maxima={n:0. for n in names};above=Counter()
        if [r['source_index'] for r in rows]!=[s['source_index'] for s in plan['slots']]:raise ValueError('source accounting')
        for row in rows:
            if row['status']!='completed':continue
            path=folder/row['raw_arrays']
            if sha(path)!=row[hashkey]:raise ValueError('raw arrays')
            with np.load(path,allow_pickle=False) as arrays:summary=summarize_arrays(arrays['logits'],names)
            if summary['emitted']!=[b['query'] for b in row['boxes']]:raise ValueError('query-order reconstruction failed')
            counts.update(summary['emitted']);above.update(summary['above'])
            for n in names:
                bins[n]=[a+b for a,b in zip(bins[n],summary['bins'][n],strict=True)]
                maxima[n]=max(maxima[n],summary['maxima'][n])
        panels[label]=dict(query_order=names,display_counts=counts,raw_display_bins=bins,
            per_query_max=maxima,all_query_scores_above_threshold=above)
    write(OUT/'detector_score_audit_v2.json',dict(panels=panels,all_emitted_query_labels_reconstructed=True,
        supersedes='detector_score_audit.json',superseded_sha256=sha(OUT/'detector_score_audit.json'),
        correction='original inference used module insertion order; short inference used sorted serialized plan order',
        source_sha256=sha(__file__),plan_sha256=sha(OUT/'plan.json'),candidate_selected=False,
        accuracy_estimated=False,calibration_eligible=False,primary_freeze_allowed=False))
    gate=json.loads((OUT/'primary_protocol_gate.json').read_bytes())
    gate['supersedes']='primary_protocol_gate.json'
    gate['evidence_sha256'].pop('detector_score_audit.json')
    gate['evidence_sha256']['detector_score_audit_v2.json']=sha(OUT/'detector_score_audit_v2.json')
    write(OUT/'primary_protocol_gate_v2.json',gate)
    print(json.dumps(panels,indent=2))


if __name__=='__main__':main()
