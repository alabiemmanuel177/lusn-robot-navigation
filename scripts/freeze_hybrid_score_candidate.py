"""Create-once development candidate snapshot; never changes old study gates."""
from collections import Counter
from pathlib import Path
import json
from prepare_joint_score_protocol import ROOT, sha
from joint_score_collection import write_once
from joint_score_components import digest
from fit_joint_score_wave_s import reviewed_rows
from hybrid_score_candidate import score, PASS_THROUGH


def main():
    source=ROOT/'reports/wave_s_doorway_amendment_candidate_20260924_v1.json'
    doorway=json.loads(source.read_text())
    for path,h in {**doorway['input_sha256'],**doorway['source_sha256']}.items():
        if sha(path)!=h:raise ValueError('changed doorway source: '+path)
    if doorway['status']!='fitted':raise ValueError('fitted doorway candidate required')
    evidence_path=ROOT/'reports/joint_score_wave_s_primary_inference_20260924_v1/evidence.json'
    evidence=json.loads(evidence_path.read_text())
    review_path=ROOT/'reports/wave-s-review-return.json'
    schedule_path=ROOT/'reports/joint_score_protocol_20260924_v1/schedule.json'
    labels,_,accounted=reviewed_rows(json.loads(schedule_path.read_text()),evidence,json.loads(review_path.read_text()))
    for c in PASS_THROUGH:
        rows=[r for r in labels if r['category']==c]
        if len(rows)<50 or len({r['map_id'] for r in rows})!=10 or any(r['y']!=1 for r in rows):
            raise ValueError('requested pass-through selection rule not met')
    predictions=[];bins={c:[0,0,0] for c in (*PASS_THROUGH,'doorway')}
    for row in accounted:
        if not row['fitting_eligible']:continue
        for e in row['emissions']:
            result=score(e,doorway['model']);p=result['input_score']
            bins[e['category']][0 if p<.5 else 1 if p<.8 else 2]+=1
            predictions.append(dict(attempt_id=row['attempt_id'],emission_id=e['emission_id'],emission_sha256=digest(e),**result))
    root=ROOT/'reports/hybrid_score_candidate_20260925_v1';root.mkdir(exist_ok=False)
    files=[source,evidence_path,review_path,schedule_path,Path(__file__),ROOT/'scripts/hybrid_score_candidate.py',
           ROOT/'docs/HYBRID_SCORE_OPERATIONAL_SPEC_20260925.md']
    candidate=dict(schema_version='research3-hybrid-score-candidate/v1',selection_role='post-Wave-S development selection',
        class_rules={**{c:'identity_on_original_matching_score' for c in PASS_THROUGH},'doorway':'fixed_five_feature_logistic'},
        doorway_model=doorway['model'],doorway_diagnostics=doorway['leave_one_map_out'],
        input_sha256={str(p.resolve()):sha(p) for p in files},
        candidate_snapshot_frozen=True,runtime_admitted=False,calibration_validated=False,
        all_class_joint_probability_claim=False,development_freeze_human_signoff=False,
        wave_c_execution_manifest_ready=False,wave_v_execution_authorized=False,
        numerical_p2_clipping_only=[1e-9,1-1e-9],c_v_coverage_floors_unchanged=True)
    write_once(root/'candidate.json',candidate)
    write_once(root/'wave_s_replay_audit.json',dict(role='development replay only; not C/V evidence',
        candidate_sha256=digest(candidate),predictions=predictions,input_score_bins=bins,
        bin_edges=[0,.5,.8,1],human_labels_generated=False,new_captures=0,
        warning='Existing S bins diagnose support only; no claim of future C/V coverage or independent validation.'))
    print(json.dumps(dict(candidate=str(root/'candidate.json'),emissions=len(predictions),S_only_bins=bins),indent=2))


if __name__=='__main__':main()
