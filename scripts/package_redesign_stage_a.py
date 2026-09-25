"""Package the completed Stage A pilot as engineering evidence, not calibration."""
import json
import zipfile
from run_redesign_stage_a import ROOT,OUTPUT,APPROVAL,PLAN,SNAPSHOT,assignments
from run_stage1_feasibility import sha,write
from audit_redesign_stage_a import audit
from verify_stage1_bundle import verify


def main():
    result=audit()
    paths={APPROVAL,PLAN,SNAPSHOT,ROOT/'configs/calibration_redesign_v2.yaml',
        ROOT/'docs/CALIBRATION_REDESIGN_AMENDMENT_20260923.md',
        ROOT/'docs/REDESIGN_STAGE_A_RESULTS_20260923.md',
        ROOT/'memory/2026-09-23-stage-a-launch-environment.md',
        ROOT/'tests/test_redesign_stage_a.py'}
    binding=json.loads((OUTPUT/'source_binding.json').read_bytes())
    paths.update(ROOT/name for name in binding['input_sha256'])
    paths.update(ROOT/'scripts'/name for name in ('audit_redesign_stage_a.py','export_redesign_stage_a.py',
        'package_redesign_stage_a.py','launch_redesign_stage_a.sh','verify_stage1_bundle.py','verify_physical_release.py',
        'reconstruct_redesign_stage_a.py','analyze_feasibility_score_support.py'))
    paths.update(p for p in OUTPUT.rglob('*') if p.is_file())
    for row in assignments():
        paths.update(p for p in (ROOT/'reports/physical_live_episodes'/row['candidate_id']).rglob('*') if p.is_file())
        paths.update(p for p in (ROOT/row['world_directory']).rglob('*') if p.is_file())
    for path in paths:
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT):
            raise ValueError('contained regular evidence only')
    manifest=dict(schema_version='research3-engineering-evidence-bundle/v1',
        files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(paths)],
        scientific_release_complete=False,calibration_eligible=False,protected_data_included=False,
        scope='Completed fixed design-only lighting pilot; no human correctness labels or primary coverage credit',
        entrypoint='docs/REDESIGN_STAGE_A_RESULTS_20260923.md',
        runtime_note='Raw evidence plus source bindings; not a standalone ROS installation')
    destination=ROOT/'reports/research3_redesign_stage_a_20260923_v1.zip'
    with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths):archive.write(path,str(path.relative_to(ROOT)))
        archive.writestr('bundle_manifest.json',json.dumps(manifest,sort_keys=True,indent=2))
    verified=verify(destination,sha(destination));verified['archive']=str(destination.relative_to(ROOT))
    write(OUTPUT/'bundle_verification.json',verified);print(json.dumps(verified))


if __name__=='__main__':main()
