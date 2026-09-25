"""Recompute design-only emitted scores from retained pixels and frozen provider."""
import json
import os
from analyze_feasibility_score_support import analyze,PROVIDER
from run_redesign_stage_a import ROOT,OUTPUT,assignments,validate_pins
from run_stage1_feasibility import sha,write


def main():
    os.nice(19);validate_pins();results=[]
    for row in assignments():
        path=OUTPUT/(row['candidate_id']+'.result.json')
        if not path.exists():raise ValueError('complete schedule required')
        result=json.loads(path.read_bytes());observation=result.get('selected_observation')
        if observation is None:continue
        output=analyze(dict(run_id=row['candidate_id'],partition='development',panel='design_feasibility',
            observation_id=observation['observation_id'],probability=observation['confidence'],category=row['category']))
        if not output['score_reconstruction_matches']:raise ValueError('provider score mismatch')
        results.append(output)
    report=dict(schema_version='research3-redesign-stage-a-score-reconstruction/v1',
        emissions_reconstructed=len(results),all_scores_match=True,rows=results,
        provider_core_sha256=sha(PROVIDER/'research3_landmark_bridge/core.py'),
        analyzer_sha256=sha(ROOT/'scripts/analyze_feasibility_score_support.py'),
        human_labels_generated=False,calibration_certified=False)
    write(OUTPUT/'score_reconstruction.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='rows'}))


if __name__=='__main__':main()
