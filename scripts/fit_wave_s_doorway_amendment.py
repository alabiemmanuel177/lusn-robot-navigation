"""Explicitly authorized post-Wave-S doorway-only exploratory fit.

Retains the original numerical solver and fold failure rules. Not an upstream
four-class freeze, a calibrated probability claim, or C/V execution admission.
"""
import json
from collections import Counter
from pathlib import Path
import numpy as np
from fit_joint_score_wave_s import reviewed_rows, fit_class, predict, weights, validate_execution, sha
from joint_score_components import digest
from joint_score_collection import write_once
from prepare_joint_score_protocol import ROOT


def main():
    inputs={
        'schedule':ROOT/'reports/joint_score_protocol_20260924_v1/schedule.json',
        'evidence':ROOT/'reports/joint_score_wave_s_primary_inference_20260924_v1/evidence.json',
        'human_review':ROOT/'reports/wave-s-review-return.json',
        'manifest':ROOT/'reports/joint_score_wave_s_execution_20260924_v1/execution_manifest.json',
        'approval':ROOT/'reports/joint_score_wave_s_execution_20260924_v1/execution_approval.json',
        'amendment_authority':ROOT/'reports/wave_s_saturation_amendment_authority_20260924.json',
    }
    d={k:json.loads(p.read_text()) for k,p in inputs.items()}
    validate_execution(d['manifest'],d['approval'],protocol_sha=d['evidence']['protocol_sha256'],schedule_sha=d['evidence']['schedule_sha256'])
    if digest(d['manifest'])!=d['evidence']['execution_manifest_sha256']:raise ValueError('execution binding')
    if not d['amendment_authority']['authorizes_doorway_only_candidate_fit']:raise PermissionError('named authority required')
    rows,excluded,attempts=reviewed_rows(d['schedule'],d['evidence'],d['human_review'])
    selected=[r for r in rows if r['category']=='doorway'];maps={f'r3geo_base_r{i:03}' for i in range(1,11)}
    output=dict(schema_version='research3-post-wave-s-doorway-candidate/v1',category='doorway',
        study_role='post_outcome_selected_exploratory_candidate',model=None,leave_one_map_out=[],
        input_sha256={str(p):sha(p) for p in inputs.values()},
        source_sha256={str(p):sha(p) for p in (Path(__file__),ROOT/'scripts/fit_joint_score_wave_s.py',ROOT/'scripts/joint_score_components.py')},
        counts=dict(Counter('correct' if r['y'] else 'incorrect' for r in selected)),
        runtime_admitted=False,upstream_freeze_approved=False,calibration_validated=False,
        other_class_probabilities_assigned=False)
    try:
        output['model']=fit_class(selected,maps);output['status']='fitted'
        for held in sorted(maps):
            train=[r for r in selected if r['map_id']!=held];test=[r for r in selected if r['map_id']==held]
            fold=dict(held_out_map=held,training_outcomes=dict(Counter('correct' if r['y'] else 'incorrect' for r in train)))
            try:
                fitted=fit_class(train,maps-{held});p=predict(fitted,[r['features'] for r in test])
                fold.update(status='fitted',model=fitted,held_out_emission_ids=[r['emission_id'] for r in test],
                    probabilities=p.tolist(),brier=float(np.sum(weights(test)*(p-np.array([r['y'] for r in test]))**2)))
            except ValueError as exc:fold.update(status='unfit',reason=str(exc))
            output['leave_one_map_out'].append(fold)
    except ValueError as exc:output.update(status='unfit',reason=str(exc))
    path=ROOT/'reports/wave_s_doorway_amendment_candidate_20260924_v1.json';write_once(path,output)
    print(json.dumps(dict(status=output['status'],reason=output.get('reason'),fold_statuses=dict(Counter(r['status'] for r in output['leave_one_map_out'])),output=str(path)),indent=2))


if __name__=='__main__':main()
