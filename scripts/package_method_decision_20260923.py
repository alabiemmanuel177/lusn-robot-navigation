"""Small human method-decision evidence packet; deliberately not a labeling kit."""
import json
import zipfile
from class_aware_acquisition_pilot import ROOT, OUTPUT
from run_stage1_feasibility import sha, write
from verify_stage1_bundle import verify


def main():
    packet = ROOT / 'reports/method_decision_20260923_v1'
    packet.mkdir(exist_ok=False)
    paths = {ROOT / name for name in (
        'docs/RESEARCH3_METHOD_DECISION_20260923.md',
        'docs/SEMANTIC_VERIFIER_PROBE_RESULTS_20260923.md',
        'docs/MISSINGNESS_CONTRACT_CANDIDATE_20260923.md',
        'scripts/audit_pilot_joint_feasibility.py', 'scripts/package_method_decision_20260923.py',
        'tests/test_pilot_joint_feasibility.py',
        'reports/semantic_verifier_probe_20260923_v1/summary.json')}
    paths.update(OUTPUT / name for name in (
        'RESULTS.md', 'plan.json', 'necessary_joint_feasibility.json', 'final/audit.json',
        'final/score_reconstruction.json', 'review_packet/attempt_accounting.json',
        'review_packet/relocation_verification.json', 'resume_environment_incident.md', 'resource_pause_51.md'))
    paths.update((OUTPUT / 'final/previews').glob('*.png'))
    start = packet / 'START_HERE.md'
    with start.open('x') as stream:
        stream.write('# Human action: method decision, not image labeling\n\n'
            'Read docs/RESEARCH3_METHOD_DECISION_20260923.md in this extracted archive. '
            'Reply with your name, role, actual date/time and decision A, B, or your revision. '
            'A requests a separately versioned R3-only observation-method redesign; '
            'B changes the study to a narrower descriptive engineering completion. '
            'Neither approves an unseen model, primary execution, protected access or labels.\n\n'
            'Do not label 76 images: the retained panel cannot meet its correct-doorway '
            'floor under the existing pose rule. All 94 full frames are included for '
            'optional evidence inspection, not as a new labeling assignment. '
            'The full engineering archive separately retains raw RGB-D and launch logs.\n\n'
            'This ZIP contains no executable review server, no prefilled decision, '
            'no human labels, no private validation key and no protected evidence. '
            'Cryptographic integrity is not scientific approval.\n')
    paths.add(start)
    manifest = dict(schema_version='research3-engineering-evidence-bundle/v1',
        files=[dict(path=str(p.relative_to(ROOT)), sha256=sha(p), bytes=p.stat().st_size) for p in sorted(paths)],
        scientific_release_complete=False, calibration_eligible=False, protected_data_included=False,
        human_labels_generated=False, scope='Human method decision with nonprotected design evidence; not a labeling request',
        entrypoint=str(start.relative_to(ROOT)), runtime_note='Read Markdown/JSON/PNG locally; no installation required')
    destination = ROOT / 'reports/research3_method_decision_20260923_v1.zip'
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths): archive.write(path, str(path.relative_to(ROOT)))
        archive.writestr('bundle_manifest.json', json.dumps(manifest, sort_keys=True, indent=2))
    result = verify(destination, sha(destination))
    result['archive'] = str(destination.relative_to(ROOT))
    write(packet / 'bundle_verification.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
