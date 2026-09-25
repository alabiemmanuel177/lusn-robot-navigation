"""Refresh a non-executable design draft from actual human decisions and dev evidence."""
import json
from pathlib import Path
import yaml
from run_stage1_feasibility import ROOT,sha,write
from check_physical_design_readiness import check


def prepare():
    decision_path=ROOT/'reports/human_decisions_20260912_v1/decision_record.json'
    nuisance_path=ROOT/'reports/feasibility_nuisance_20260914_v1.json'
    design_path=ROOT/'configs/physical_experiment_design_draft_v2.yaml'
    decisions=json.loads(decision_path.read_bytes())['decisions']
    nuisance=json.loads(nuisance_path.read_bytes())
    draft=yaml.safe_load(design_path.read_text())
    draft['status']='draft_not_frozen_not_executable'
    analysis=draft['analysis_proposals']
    analysis['primary_contrast']=decisions['D1']['primary_contrast']
    analysis['primary_endpoint']=decisions['D1']['primary_endpoint']
    analysis['multiplicity_policy']=decisions['D2']['multiplicity_policy']
    analysis['candidate_method_for_human_final_review']='exact_two_sided_world_level_sign_flip_mean_paired_difference'
    analysis['confirmatory_inference_method']=None
    power=draft['power_inputs_requiring_freeze']
    power.update(target_effect=decisions['D3']['target_effect_absolute'],target_power=decisions['D4']['target_power'],
        alpha=decisions['D4']['alpha'],baseline_completion=nuisance['baseline_completion'],
        paired_discordance=nuisance['paired_discordance'],world_intracluster_correlation=nuisance['world_icc'])
    draft['nuisance_evidence_scope']=dict(scope=nuisance['evidence_scope'],complete_pairs=nuisance['complete_pairs'],
        scheduled_pairs=80,incomplete_pairs=8,calibration_used=None,
        limitations=['uncalibrated development feasibility, not future calibrated-model estimates',
                    'negative ICC estimate is retained, not silently clipped or treated as proof of independence',
                    'Monte Carlo sensitivity is not achieved power; no seed count selected or approved'])
    draft['input_sha256']={str(p.relative_to(ROOT)):sha(p) for p in (decision_path,nuisance_path,design_path)}
    draft['execution_authorized']=False
    folder=ROOT/'reports/completion_design_candidate_20260922_v1'
    folder.mkdir(exist_ok=False)
    write(folder/'design.json',draft)
    readiness=check(draft)
    write(folder/'readiness.json',readiness)
    print(json.dumps(readiness))


if __name__=='__main__':prepare()
