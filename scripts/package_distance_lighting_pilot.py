"""Create a verified engineering evidence archive, never a calibration release."""
import json
import zipfile
from distance_lighting_pilot import ROOT,OUTPUT,PROTOCOL,SNAPSHOT,rows,check_pins
from run_stage1_feasibility import sha,write
from verify_stage1_bundle import verify


def main():
    check_pins();schedule=rows();audit=json.loads((OUTPUT/'final/audit.json').read_bytes())
    if not audit['integrity_passed'] or audit['scheduled']!=96 or len(audit['rows'])!=96:
        raise ValueError('complete independent audit required')
    source=json.loads((OUTPUT/'source_binding.json').read_bytes())
    paths={ROOT/name for name in source['input_sha256']}
    paths.update(p for p in OUTPUT.rglob('*') if p.is_file())
    paths.update(ROOT/'scripts'/n for n in ('finalize_distance_lighting_pilot.py','package_distance_lighting_pilot.py',
        'analyze_feasibility_score_support.py','verify_stage1_bundle.py','verify_physical_release.py',
        'analyze_distance_lighting_geometry.py'))
    paths.update([ROOT/'tests/test_distance_lighting_pilot.py',ROOT/'memory/2026-09-23-distance-lighting-mechanism.md'])
    for row in schedule:
        paths.update(p for p in (ROOT/'reports/physical_live_episodes'/row['candidate_id']).rglob('*') if p.is_file())
    for path in paths:
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT):raise ValueError('contained regular evidence only')
    manifest=dict(schema_version='research3-engineering-evidence-bundle/v1',
        files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(paths)],
        scientific_release_complete=False,calibration_eligible=False,protected_data_included=False,
        human_labels_generated=False,scope='Fixed exploratory development distance-lighting pilot; no primary coverage credit',
        entrypoint=str((OUTPUT/'RESULTS.md').relative_to(ROOT)),
        runtime_note='Engineering evidence archive, not a standalone ROS installation or human calibration return')
    if not (OUTPUT/'RESULTS.md').is_file():raise ValueError('results handoff missing')
    destination=ROOT/'reports/research3_distance_lighting_pilot_20260923_v1.zip'
    with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths):archive.write(path,str(path.relative_to(ROOT)))
        archive.writestr('bundle_manifest.json',json.dumps(manifest,sort_keys=True,indent=2))
    result=verify(destination,sha(destination));result['archive']=str(destination.relative_to(ROOT))
    write(OUTPUT/'bundle_verification.json',result);print(json.dumps(result))


if __name__=='__main__':main()
