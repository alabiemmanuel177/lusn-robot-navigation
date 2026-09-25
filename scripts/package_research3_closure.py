"""Package all final audit reports, authority records, and documentation for Research 3 closure."""
import hashlib
import json
from pathlib import Path
import zipfile
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / 'scripts') not in sys.path:
    sys.path.insert(0, str(ROOT / 'scripts'))

from run_stage1_feasibility import sha, write
from verify_stage1_bundle import verify


def main():
    packet = ROOT / 'reports/research3_final_closure_20260926_v1'
    packet.mkdir(parents=True, exist_ok=True)

    start = packet / 'START_HERE.md'
    with start.open('w') as stream:
        stream.write(
            '# Research 3 Final Closure: Descriptive and Exploratory Feasibility Deliverable\n\n'
            '**Reviewer**: Emmanuel Alabi Olasubomi  \n'
            '**Role**: Researcher  \n'
            '**Timezone**: Africa/Lagos  \n'
            '**Date**: 26 September 2026  \n'
            '**Scope Decision**: Option 2 — Narrow study scope to descriptive and exploratory feasibility; '
            'formally close Research 3.\n\n'
            '## Executive Summary of Findings\n\n'
            '1. **Structural OCR Support Limitation**:\n'
            '   Frozen upstream thresholding in RapidOCR (`text_score >= 0.5`) mathematically truncates entrance '
            'input support to [0.5, 1.0]. Because the localizer copies the retained text score directly to `raw_score` '
            'and identity pass-through is used, populating the required [0, 0.5) bin for laboratory and office entrances '
            'is structurally impossible (0 emissions vs 5 required). Unchanged collection waves cannot satisfy Coverage v2.\n'
            '   Audit: `reports/hybrid_score_candidate_20260925_v1/ocr_support_audit.json`.\n\n'
            '2. **Wave S Clean-View Precision Saturation & Error Localization**:\n'
            '   Grounding DINO and RapidOCR achieved 100% precision on chairs and signage across 261 views evaluated '
            'by human review (99 chair, 84 lab entrance, 78 office entrance; 0 incorrect). Geometric localization error '
            'was strictly isolated to doorway portal void penetration (20 correct, 6 incorrect out of 26 doorway emissions), '
            'where depth rays penetrate the open portal void rather than striking jamb boundaries.\n'
            '   Zero negative outcomes for three classes prohibited multi-class supervised logistic calibration under '
            'the pre-registered outcome floor (>= 5 incorrect per class).\n\n'
            '3. **Exploratory Hybrid Candidate**:\n'
            '   Retained in `reports/hybrid_score_candidate_20260925_v1/candidate.json`. Combines the fitted 5-feature '
            'doorway logistic model with raw-score pass-through for chairs and signage. Retained strictly as an '
            'exploratory feasibility candidate; not admitted for runtime robot navigation.\n\n'
            '4. **Final Closure & Policy Actions**:\n'
            '   - Research 3 is formally terminated under the descriptive and exploratory feasibility deliverable.\n'
            '   - Wave C (calibration) and Wave V (validation) are not scheduled or launched.\n'
            '   - Four-class runtime calibration is not claimed.\n'
            '   - Blockers B03 and B09 are formally resolved.\n'
            '   - All dangling locks and tasks have been cleared.\n'
        )

    paths = {
        ROOT / 'reports/research3_closure_authority_20260926.json',
        ROOT / 'reports/hybrid_score_candidate_20260925_v1/candidate.json',
        ROOT / 'reports/hybrid_score_candidate_20260925_v1/ocr_support_audit.json',
        ROOT / 'reports/hybrid_score_candidate_20260925_v1/wave_s_replay_audit.json',
        ROOT / 'reports/wave_s_review_receipt_20260924_v1.json',
        ROOT / 'reports/wave_s_saturation_amendment_authority_20260924.json',
        ROOT / 'reports/wave_s_doorway_amendment_candidate_20260924_v1.json',
        ROOT / 'reports/review_decision.json',
        ROOT / 'docs/HYBRID_SCORE_SUPPORT_BLOCKER_20260925.md',
        ROOT / 'docs/AMENDMENT_WAVE_S_SATURATED_CLASSES_20260924.md',
        ROOT / 'docs/RESEARCH3_RESULTS.md',
        ROOT / 'docs/STATUS.md',
        ROOT / 'docs/RESEARCH3_BLOCKER_LEDGER_20260922.md',
        ROOT / 'scripts/hybrid_score_candidate.py',
        ROOT / 'scripts/audit_hybrid_ocr_support.py',
        ROOT / 'scripts/fit_wave_s_doorway_amendment.py',
        ROOT / 'scripts/package_research3_closure.py',
        ROOT / 'tests/test_hybrid_score_candidate.py',
        start,
    }

    manifest = dict(
        schema_version='research3-engineering-evidence-bundle/v1',
        files=[
            dict(path=str(p.relative_to(ROOT)), sha256=sha(p), bytes=p.stat().st_size)
            for p in sorted(paths)
        ],
        scientific_release_complete=False,
        calibration_eligible=False,
        protected_data_included=False,
        human_labels_generated=False,
        scope='Research 3 final closure under descriptive and exploratory feasibility deliverable',
        entrypoint=str(start.relative_to(ROOT)),
        runtime_note='Read Markdown/JSON locally; no installation required'
    )

    destination = ROOT / 'reports/research3_final_closure_20260926_v1.zip'
    if destination.exists():
        destination.unlink()

    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            archive.write(path, str(path.relative_to(ROOT)))
        archive.writestr('bundle_manifest.json', json.dumps(manifest, sort_keys=True, indent=2))

    result = verify(destination, sha(destination))
    result['archive'] = str(destination.relative_to(ROOT))
    write(packet / 'bundle_verification.json', result)
    write(packet / 'manifest.json', manifest)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
