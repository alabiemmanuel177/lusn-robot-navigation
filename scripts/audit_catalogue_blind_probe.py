"""Independently verify complete fixed-region outputs, without human accuracy claims."""
from collections import Counter
import json
from catalogue_blind_regions import evidence
from run_catalogue_blind_probe import OUTPUT
from run_stage1_feasibility import sha,write


def main():
    plan=json.loads((OUTPUT/'plan.json').read_bytes()); report=json.loads((OUTPUT/'report.json').read_bytes())
    if report['plan_sha256']!=sha(OUTPUT/'plan.json') or report['vectors_sha256']!=sha(OUTPUT/'vectors.jsonl'):
        raise ValueError('binding mismatch')
    expected={(r['frame_index'],name):box for r in plan['frames'] for name,box in r['regions']}
    seen=set();counts=Counter()
    for line in (OUTPUT/'vectors.jsonl').read_text().splitlines():
        row=json.loads(line); key=(row['frame_index'],row['region_id'])
        if key in seen or key not in expected or row['box']!=expected[key]:raise ValueError('region identity')
        rebuilt=evidence(row['region_id'],row['box'],row['cosine_similarity'],report['learned_logit_scale'])
        if row!={**rebuilt,'frame_index':row['frame_index']}:raise ValueError('score or scientific-scope drift')
        seen.add(key); counts[row['top_prompt']]+=1
    if seen!=set(expected) or len(seen)!=1410:raise ValueError('incomplete panel')
    result=dict(integrity_passed=True,vectors=len(seen),frames=141,top_prompt_counts=counts,
        class_agreement_or_accuracy_estimated=False,calibration_eligible=False,human_labels_generated=False,
        observation_localization_established=False,report_sha256=sha(OUTPUT/'report.json'))
    write(OUTPUT/'audit.json',result); print(json.dumps(result))


if __name__=='__main__': main()
