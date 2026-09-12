#!/usr/bin/env python3
"""Create-once human method-review addendum; never grant approval or launch."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def build(output):
    output=Path(output);archive_path=output.with_suffix('.zip')
    if output.exists() or archive_path.exists():raise FileExistsError(output)
    mapping={
        'STATISTICAL_METHOD_PROPOSAL_20260912.md':'docs/STATISTICAL_METHOD_PROPOSAL_20260912.md',
        'CALIBRATION_METHOD_PROPOSAL_20260912.md':'docs/CALIBRATION_METHOD_PROPOSAL_20260912.md',
        'VALIDATION_DELAYED_RELEASE.md':'docs/VALIDATION_DELAYED_RELEASE.md',
        'EXPANSION_IMPLEMENTATION_GATE.md':'docs/EXPANSION_IMPLEMENTATION_GATE.md',
        'PROPOSAL_RESPONSE.md':'reports/human_decisions_20260912_v1/PROPOSAL_RESPONSE.md',
        'sign_flip_sensitivity.json':'reports/human_decisions_20260912_v1/sign_flip_sensitivity.json',
        'seal_validation_review.py':'scripts/seal_validation_review.py',
        'candidate_source/expansion_sampling.py':'scripts/expansion_sampling.py',
        'candidate_source/physical_expansion_capture_candidate.py':'scripts/physical_expansion_capture_candidate.py',
        'candidate_source/world_sign_flip_sensitivity.py':'scripts/world_sign_flip_sensitivity.py',
    }
    files={name:(ROOT/path).read_bytes() for name,path in mapping.items()}
    files['README.md']=b'''# Research 3 method proposal addendum

Your D1-D8 response is recorded. B6 minus B5, the +10 percentage-point planning
effect, two-sided alpha .05 and target power .80 are not being asked again.
Neither achieved power nor a fitted model is claimed.

1. Read the statistical and calibration proposals and delayed-release guide.
2. Read EXPANSION_IMPLEMENTATION_GATE.md for the separate capture-source issue.
3. Fill PROPOSAL_RESPONSE.md and send that document back privately. No software
   installation or rerun of the completed pilot review is needed for these decisions.

Statistical sensitivity is analytic under explicit assumptions, not empirical
power. The agent still owes nonprotected paired nuisance estimates and final
method/replication feasibility. P1 must not be treated as a final confirmatory freeze.
The calibration proposal defines one concrete candidate; you may revise/reject it.
P2 does not accept any unseen fitted model or validation results.

The crypto script is supplied for inspection/future validation kits. Do not run it
on the pilot or upload any key or plaintext validation judgments. It uses the
cryptography Python library and has only been tested with synthetic return bytes.
No real validation labels or keys are included. Script hashes prove byte integrity,
not external security certification or independent reviewer blinding.

The source candidate is unwired and cannot launch simulations. P4 asks to revise
R3 capture instrumentation only, preserving detector behavior, geometry and coverage.
It is not approval of unfinished rendered assets, a campaign or protected access.

All earlier published ZIPs remain unchanged. This addendum contains no new
observation review images. The full scene/target asset review still requires
rendered preflight evidence and is not requested from code or static geometry alone.
'''
    files['manifest.json']=(json.dumps({'schema_version':'research3-method-proposal-addendum/v1',
        'status':'pending_human_review','execution_authorized':False,'calibration_approved':False,
        'files':{name:hashlib.sha256(raw).hexdigest() for name,raw in files.items()}},indent=2,sort_keys=True)+'\n').encode()
    output.mkdir(parents=True,exist_ok=False)
    for name,raw in files.items():
        path=output/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(raw)
    with zipfile.ZipFile(archive_path,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,raw in files.items():archive.writestr(name,raw)
    print(json.dumps({'archive':str(archive_path),'sha256':hashlib.sha256(archive_path.read_bytes()).hexdigest(),
                      'files':len(files),'human_decisions_generated':False}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    build(parser.parse_args().output)
