"""Package the explicit redesign for protocol inspection, not observation review."""
import json
import zipfile
from prepare_calibration_redesign import CONFIG,OUTPUT
from run_stage1_feasibility import ROOT,sha,write
from verify_stage1_bundle import verify


def main():
    destination=ROOT/'reports/research3_calibration_redesign_20260923_v1.zip'
    if destination.exists():raise FileExistsError(destination)
    plan=json.loads((OUTPUT/'plan.json').read_bytes())
    paths={CONFIG,ROOT/'docs/CALIBRATION_REDESIGN_AMENDMENT_20260923.md',
        ROOT/'docs/CALIBRATION_FEASIBILITY_INTERPRETATION_20260922.md',
        ROOT/'docs/RESEARCH3_BLOCKER_LEDGER_20260922.md',
        ROOT/'scripts/prepare_calibration_redesign.py',ROOT/'scripts/verify_calibration_redesign.py',
        ROOT/'scripts/package_calibration_redesign.py',ROOT/'tests/test_calibration_redesign.py',
        ROOT/'scripts/verify_stage1_bundle.py',ROOT/'scripts/verify_physical_release.py',
        ROOT/'reports/calibration_expansion_proposal_20260911_v2/plan.json',
        ROOT/'reports/expansion_instrumentation_snapshot_20260922_v8/snapshot.json'}
    paths.update(ROOT/name for name in plan['source_sha256'])
    paths.update(p for p in OUTPUT.rglob('*') if p.is_file())
    for path in paths:
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT):
            raise ValueError('contained regular proposal sources required')
    records=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(paths)]
    manifest=dict(schema_version='research3-engineering-evidence-bundle/v1',files=records,
        scientific_release_complete=False,calibration_eligible=False,protected_data_included=False,
        scope='unrendered calibration redesign and static geometry checks; not human observation labeling or execution approval',
        validation_content_scope='static map/world/profile/planning metadata only, no validation outcomes or labels',
        entrypoint='docs/CALIBRATION_REDESIGN_AMENDMENT_20260923.md',
        runtime_note='not a standalone ROS runtime; preparation scripts require the matching checkout; archive integrity verifier uses only Python standard library')
    with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths):archive.write(path,str(path.relative_to(ROOT)))
        archive.writestr('bundle_manifest.json',json.dumps(manifest,indent=2,sort_keys=True))
    result=verify(destination,sha(destination));result.update(archive=str(destination.relative_to(ROOT)),bytes=destination.stat().st_size)
    write(ROOT/'reports/calibration_redesign_bundle_verification_20260923_v1.json',result)
    print(json.dumps(result))


if __name__=='__main__':main()
