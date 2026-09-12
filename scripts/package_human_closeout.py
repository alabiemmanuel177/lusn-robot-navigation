"""Create-once current human-gate instructions; never a ready-to-sign approval."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
RUN='reports/physical_live_episodes/r3-expansion-instrumentation-dev01-preflight-v2'


def build(output):
    output=Path(output)
    archive=output.with_suffix('.zip')
    if output.exists() or archive.exists():raise FileExistsError(output)
    mapping={
        'README.md':'docs/HUMAN_CLOSEOUT_NEXT_STEPS.md',
        'HUMAN_GATES.md':'docs/HUMAN_GATES.md',
        'VALIDATION_DELAYED_RELEASE.md':'docs/VALIDATION_DELAYED_RELEASE.md',
        'CLASSWISE_CALIBRATION_IMPLEMENTATION.md':'docs/CLASSWISE_CALIBRATION_IMPLEMENTATION.md',
        'reference/campaign_approval_contract.md':'docs/PHYSICAL_CAMPAIGN_EXECUTOR.md',
        'reference/heldout_approval_contract.md':'docs/PHYSICAL_HELDOUT_RUNTIME.md',
        'reference/final_release_contract.md':'docs/PHYSICAL_SCIENTIFIC_RELEASE_GATE.md',
        'engineering_preflight/capture_summary.json':RUN+'/capture_summary.json',
        'engineering_preflight/exact-frame.png':RUN+'/exact-frame.png',
    }
    summary=json.loads((ROOT/RUN/'capture_summary.json').read_bytes())
    attempt=json.loads((ROOT/RUN/'expansion_attempt.json').read_bytes())
    if (summary.get('complete') is not True or summary.get('protected_test_routes_used') is not False
            or summary.get('motion_commands_sent') is not False or attempt.get('status')!='emitted'):
        raise ValueError('expected completed nonprotected stationary preflight')
    files={name:(ROOT/source).read_bytes() for name,source in mapping.items()}
    files['manifest.json']=(json.dumps(dict(
        schema_version='research3-human-closeout-instructions/v2',
        packet_id='research3-human-closeout-v2',ready_for_new_human_decision=False,
        new_reviewable_observation_panel_included=False,engineering_preflight_images=1,
        execution_authorized=False,approved_model_included=False,
        files={name:hashlib.sha256(raw).hexdigest() for name,raw in files.items()}),
        indent=2,sort_keys=True)+'\n').encode()
    output.mkdir(parents=True,exist_ok=False)
    for name,raw in files.items():
        path=output/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(raw)
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as zipped:
        for name,raw in files.items():zipped.writestr(name,raw)
    with zipfile.ZipFile(archive) as zipped:
        if zipped.testzip() is not None:raise ValueError('archive CRC failure')
        manifest=json.loads(zipped.read('manifest.json'))
        for name,digest in manifest['files'].items():
            if hashlib.sha256(zipped.read(name)).hexdigest()!=digest:raise ValueError('archive integrity failure')
    return dict(archive=str(archive),sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=len(files))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    print(json.dumps(build(parser.parse_args().output)))
