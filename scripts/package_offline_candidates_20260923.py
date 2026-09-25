"""Package completed offline candidates, explicitly excluding model admission."""
import json
import zipfile
from pathlib import Path
from run_stage1_feasibility import ROOT, sha, write
from verify_stage1_bundle import verify


def main():
    output = ROOT / 'reports/offline_candidates_20260923_v1'
    output.mkdir(exist_ok=False)
    names = [
        'scripts/missingness_contract_candidate.py', 'tests/test_missingness_contract_candidate.py',
        'docs/MISSINGNESS_CONTRACT_CANDIDATE_20260923.md',
        'scripts/semantic_verifier_probe.py', 'scripts/summarize_semantic_verifier_probe.py',
        'tests/test_semantic_verifier_probe.py', 'docs/SEMANTIC_VERIFIER_PROBE_20260923.md',
        'docs/SEMANTIC_VERIFIER_PROBE_RESULTS_20260923.md',
        'scripts/package_offline_candidates_20260923.py', 'scripts/verify_stage1_bundle.py',
        'scripts/verify_physical_release.py']
    paths = {ROOT / name for name in names}
    paths.update(p for p in (ROOT / 'reports/semantic_verifier_probe_20260923_v1').rglob('*') if p.is_file())
    readme = output / 'README.md'
    with readme.open('x') as stream:
        stream.write('# Offline candidates — engineering evidence only\n\n'
            'Contains the tested missingness accounting contract candidate and the completed '
            'fixed-model semantic probe with source, pinned prompts, input/output hashes and '
            'runtime package versions. Neither candidate is activated in the navigation system. '
            'No labels, models, calibration, held-out access or release claims are approved.\n\n'
            'The semantic probe uses 119 development-only Stage A emissions. Raw inputs remain '
            'in the separately verified research3_redesign_stage_a_20260923_v1.zip archive '
            '(SHA-256 088a4c70466ca7e893848d2e5585bd5bfa4647a4826b0ae1dc957f9d1155b16c). '
            'The pretrained checkpoint is referenced by exact digest, not duplicated here. '
            'This is a lightweight results/source package, not a standalone runtime or a '
            'reviewer labeling kit. Absolute runtime paths in the probe plan preserve historical provenance.\n')
    paths.add(readme)
    for path in paths:
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT):
            raise ValueError('contained regular source/evidence only')
    manifest = dict(schema_version='research3-engineering-evidence-bundle/v1',
        files=[dict(path=str(p.relative_to(ROOT)), sha256=sha(p), bytes=p.stat().st_size) for p in sorted(paths)],
        scientific_release_complete=False, calibration_eligible=False, protected_data_included=False,
        human_labels_generated=False, scope='Offline candidate methods and semantic probe, not deployed',
        entrypoint=str(readme.relative_to(ROOT)), runtime_note='Requires separately referenced raw inputs and checkpoint to repeat inference')
    destination = ROOT / 'reports/research3_offline_candidates_20260923_v1.zip'
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths): archive.write(path, str(path.relative_to(ROOT)))
        archive.writestr('bundle_manifest.json', json.dumps(manifest, sort_keys=True, indent=2))
    result = verify(destination, sha(destination))
    result['archive'] = str(destination.relative_to(ROOT))
    write(output / 'bundle_verification.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
