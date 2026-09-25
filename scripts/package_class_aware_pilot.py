"""Hash-verified complete class-aware engineering archive; no release claim."""
import json
import zipfile
from class_aware_acquisition_pilot import ROOT, OUTPUT, rows, check_pins
from run_stage1_feasibility import sha, write
from verify_stage1_bundle import verify


def main():
    check_pins()
    schedule = rows()
    audit = json.loads((OUTPUT / 'final/audit.json').read_bytes())
    if not audit['integrity_passed'] or audit['scheduled'] != 96 or len(audit['rows']) != 96:
        raise ValueError('complete independent audit required')
    if not (OUTPUT / 'RESULTS.md').is_file():
        raise ValueError('results handoff missing')
    bindings = json.loads((OUTPUT / 'source_binding.json').read_bytes())
    paths = {ROOT / name for name in bindings['input_sha256']}
    paths.update(p for p in OUTPUT.rglob('*') if p.is_file() and p.suffix != '.zip')
    paths.update(ROOT / 'scripts' / name for name in (
        'finalize_class_aware_pilot.py', 'build_class_aware_review_kit.py', 'package_class_aware_pilot.py',
        'launch_class_aware_pilot.sh',
        'verify_class_aware_review_kit.py',
        'audit_pilot_joint_feasibility.py',
        'analyze_feasibility_score_support.py', 'verify_stage1_bundle.py', 'verify_physical_release.py',
        'portable_physical_review.py', 'prepare_consolidated_review.py', 'serve_physical_review.py',
        'export_physical_human_review.py', 'prepare_joint_review_evidence.py', 'join_physical_review_capture.py'))
    paths.update(ROOT / 'tests' / name for name in ('test_class_aware_acquisition_pilot.py', 'test_class_aware_review_kit.py',
                                                  'test_class_aware_launch_wrapper.py', 'test_pilot_joint_feasibility.py'))
    paths.add(ROOT / 'docs/RESEARCH3_METHOD_DECISION_20260923.md')
    for row in schedule:
        paths.update(p for p in (ROOT / 'reports/physical_live_episodes' / row['candidate_id']).rglob('*') if p.is_file())
    for path in paths:
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT):
            raise ValueError('contained regular evidence only')
    manifest = dict(schema_version='research3-engineering-evidence-bundle/v1',
        files=[dict(path=str(p.relative_to(ROOT)), sha256=sha(p), bytes=p.stat().st_size) for p in sorted(paths)],
        scientific_release_complete=False, calibration_eligible=False, protected_data_included=False,
        human_labels_generated=False, scope='Fresh exploratory class-aware development pilot; no primary coverage credit',
        entrypoint=str((OUTPUT / 'RESULTS.md').relative_to(ROOT)),
        runtime_note='Engineering evidence only; portable reviewer kit is a separate archive')
    destination = ROOT / 'reports/research3_class_aware_pilot_20260923_v1.zip'
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            archive.write(path, str(path.relative_to(ROOT)))
        archive.writestr('bundle_manifest.json', json.dumps(manifest, sort_keys=True, indent=2))
    result = verify(destination, sha(destination))
    result['archive'] = str(destination.relative_to(ROOT))
    write(OUTPUT / 'bundle_verification.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
