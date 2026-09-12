#!/usr/bin/env python3
"""Create a portable human-action register and decision-only return packet."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
TEMPLATE='''# Research 3 human decisions

Packet: research3-human-actions-v1
Name: PENDING
Role: PENDING
Actual date and timezone: PENDING

These are my own scientific decisions or requests for proposals. I am not
approving unseen assets/results, granting blanket execution or protected access,
or replacing the later observation review, calibration and final-result approvals.
Personal confirmation of the above (yes/no): PENDING

## D1. Primary contrast and endpoint
Answer: PENDING
Reason: PENDING

## D2. Secondary comparisons, weighting, pairing and missingness
Accept the D2 proposal, or specify each revision: PENDING
Reason: PENDING

## D3. Minimum scientifically meaningful absolute improvement
Percentage points (not an observed improvement): PENDING
Scientific reason: PENDING

## D4. Confirmatory planning targets
Alpha: PENDING
Target power: PENDING
Reason, or request for statistical advice: PENDING

## D5. Inferential ambition and method
Confirmatory or descriptive/exploratory: PENDING
Exact preferred method, or request an agent-authored proposal: PENDING
Reason and limits: PENDING

## D6. Review coordination
Primary reviewer: PENDING
Independent validation custodian available (name, or no): PENDING
Agree that validation labels remain outside model selection: PENDING
Other review arrangements: PENDING

## D7. Calibration-method constraints
Required method/constraints, or request an exact development-only proposal: PENDING
Reason: PENDING

## D8. Other required authority or constraints
Additional required reviewer/supervisor, or none: PENDING
Deadline/resource/other constraints, or none: PENDING

## Questions or deferred decisions
PENDING
'''


def build(output):
    output=Path(output)
    archive_path=output.with_suffix('.zip')
    if output.exists() or archive_path.exists(): raise FileExistsError(output)
    mapping={
        'README.md':'docs/HUMAN_ACTIONS_README.md',
        'DECISION_GUIDE.md':'docs/HUMAN_DECISION_GUIDE.md',
        'HUMAN_GATES.md':'docs/HUMAN_GATES.md',
        'return_packet.py':'scripts/return_human_decisions.py',
        'reference/experiment_design_draft.yaml':'configs/physical_experiment_design_draft_v2.yaml',
        'reference/campaign_draft.yaml':'configs/physical_campaign_draft_v1.yaml',
        'reference/accepted_expansion_amendment.yaml':'reports/calibration_expansion_proposal_20260911_v2/amendment.input.yaml',
        'reference/accepted_amendment_decision.json':'reports/calibration_expansion_handoff_20260912_v1/amendment_review_decision.json',
        'reference/pilot_receipt.json':'reports/calibration_expansion_handoff_20260912_v1/receipt.json',
        'reference/sphere_candidates_status.md':'reports/calibration_expansion_distractor_assets_20260912_v1/README.md',
        'reference/calibration_approval_contract.md':'docs/PHYSICAL_CALIBRATION_VALIDATION.md',
        'reference/campaign_approval_contract.md':'docs/PHYSICAL_CAMPAIGN_EXECUTOR.md',
        'reference/heldout_runtime_contract.md':'docs/PHYSICAL_HELDOUT_RUNTIME.md',
        'reference/release_approval_contract.md':'docs/PHYSICAL_SCIENTIFIC_RELEASE_GATE.md',
    }
    files={name:(ROOT/source).read_bytes() for name,source in mapping.items()}
    files['response.template.md']=TEMPLATE.encode()
    files['manifest.json']=(json.dumps({
        'schema_version':'research3-human-action-packet/v1',
        'packet_id':'research3-human-actions-v1',
        'scope':'decisions_now_and_complete_future_human_gate_register',
        'new_observations_included':0, 'execution_authorized':False,
        'files':{name:hashlib.sha256(raw).hexdigest() for name,raw in files.items()},
        'editable_response':'YOUR_RESPONSE.md',
    },sort_keys=True,indent=2)+'\n').encode()
    files['YOUR_RESPONSE.md']=TEMPLATE.encode()
    output.mkdir(parents=True,exist_ok=False)
    for name,raw in files.items():
        path=output/name; path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(raw)
    with zipfile.ZipFile(archive_path,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,raw in files.items(): archive.writestr(name,raw)
    print(json.dumps({'archive':str(archive_path),'sha256':hashlib.sha256(archive_path.read_bytes()).hexdigest(),
                      'files':len(files),'new_observations':0,'human_decisions_generated':False}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    build(parser.parse_args().output)
