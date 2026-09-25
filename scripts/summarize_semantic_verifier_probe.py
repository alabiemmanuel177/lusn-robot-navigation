"""Audit relative prompt vectors; never compute accuracy without human labels."""
from collections import Counter
import json
import math
from semantic_verifier_probe import OUTPUT,PROMPTS,sha,write


def main():
    plan=json.loads((OUTPUT/'plan.json').read_bytes());report=json.loads((OUTPUT/'report.json').read_bytes())
    if report['plan_sha256']!=sha(OUTPUT/'plan.json') or report['journal_sha256']!=sha(OUTPUT/'inference.jsonl'):
        raise ValueError('probe evidence binding')
    rows=[json.loads(line) for line in (OUTPUT/'inference.jsonl').read_text().splitlines()]
    expected={(r['run_id'],v) for r in plan['rows'] for v in plan['views']};seen=set()
    for row in rows:
        key=(row['run_id'],row['view'])
        if key not in expected or key in seen:raise ValueError('unexpected/duplicate output')
        seen.add(key)
        if set(row['cosine_similarity'])!=set(PROMPTS) or set(row['relative_prompt_softmax'])!=set(PROMPTS):raise ValueError('prompt set')
        if row['human_verdict'] is not None or row['correctness_verified'] or row['calibration_eligible']:raise ValueError('scope')
        logits={k:report['learned_logit_scale']*v for k,v in row['cosine_similarity'].items()};top=max(logits.values())
        values={k:math.exp(v-top) for k,v in logits.items()};total=sum(values.values())
        if any(abs(values[k]/total-row['relative_prompt_softmax'][k])>3e-6 for k in values):raise ValueError('softmax reconstruction')
        if max(logits,key=logits.get)!=row['top_prompt']:raise ValueError('rank mismatch')
    if seen!=expected:raise ValueError('incomplete output panel')
    strata=[]
    for view in plan['views']:
        for category in ('chair','doorway','laboratory_entrance','office_entrance'):
            group=[r for r in rows if r['view']==view and r['provider_claim']==category]
            values=[r['relative_prompt_softmax'][category] for r in group]
            strata.append(dict(view=view,provider_claim=category,count=len(group),
                top_prompt_counts=dict(Counter(r['top_prompt'] for r in group)),
                claimed_prompt_relative_score_bins=[sum(v<.5 for v in values),sum(.5<=v<.8 for v in values),sum(v>=.8 for v in values)],
                agreement_is_not_accuracy=True))
    result=dict(schema_version='research3-semantic-probe-summary/v1',integrity_passed=True,
        vector_count=len(rows),observations=len(plan['rows']),softmax_vectors_reconstructed=True,strata=strata,
        human_labels_used=False,accuracy_estimated=False,calibration_certified=False,
        interpretation='Context/prompt-sensitive exploratory evidence, not an admitted semantic verifier or repaired provider')
    write(OUTPUT/'summary.json',result);print(json.dumps(result))


if __name__=='__main__':main()
