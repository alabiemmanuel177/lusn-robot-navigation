#!/usr/bin/env python3
"""Verify and preserve a returned pilot and amendment; never dispatch or label.

The output is a preparation handoff, NOT a new observation review kit.
The frozen proposal is retained byte-for-byte, with approval stored separately.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
GATES = {
    'pilot_only', 'rubric_scope', 'unchanged_coverage', 'fixed_primary_schedule',
    'diagnostic_exclusion', 'partition_separation', 'fixed_budget_stopping',
    'source_resource_guards',
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def validate_decision(decision, template, bindings):
    """Validate artifact binding, not identity or scientific truth of rationales."""
    if (decision.get('schema_version') != 'research3-calibration-expansion-review/v1'
            or decision.get('overall_decision') != 'accept'
            or decision.get('grants_execution_by_itself') is not False
            or decision.get('protected_outcomes_consulted') is not False
            or decision.get('reviewer_role') not in ('Researcher', 'Supervisor')):
        raise ValueError('amendment acceptance scope invalid')
    name = decision.get('reviewer_name')
    if not isinstance(name, str) or not name.strip():
        raise ValueError('named reviewer required')
    stamp = datetime.fromisoformat(decision.get('reviewed_at', '').replace('Z', '+00:00'))
    if stamp.tzinfo is None:
        raise ValueError('timezone-aware review date required')
    gates = decision.get('decisions', {})
    if set(gates) != GATES or set(template['decisions']) != GATES:
        raise ValueError('exact eight gates required')
    for gate in gates.values():
        if (gate.get('decision') != 'accept' or not isinstance(gate.get('rationale'), str)
                or not gate['rationale'].strip()):
            raise ValueError('all gates need acceptance and rationale')
    for key, raw in bindings.items():
        if decision.get(key) != digest(raw):
            raise ValueError('artifact hash mismatch: ' + key)
    for key in ('amendment_sha256', 'plan_sha256'):
        if decision[key] != template[key]:
            raise ValueError('approval is for another frozen proposal')


def safe_unpack_kit(raw, destination):
    import io
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('duplicate kit member')
        for info in archive.infolist():
            path = Path(info.filename)
            if (path.is_absolute() or '..' in path.parts or '\\' in info.filename
                    or (info.external_attr >> 16) & 0o170000 == 0o120000):
                raise ValueError('unsafe kit member')
        archive.extractall(destination)


def package(root, returned, decision_path, usability_path, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists() or output.with_suffix('.zip').exists():
        raise FileExistsError('create-once destination already exists')
    proposal = root / 'reports/calibration_expansion_proposal_20260911_v2'
    inputs = {
        'phase_1_return_sha256': Path(returned).read_bytes(),
        'phase_1_usability_audit_sha256': Path(usability_path).read_bytes(),
        'amendment_sha256': (proposal / 'amendment.input.yaml').read_bytes(),
        'plan_sha256': (proposal / 'plan.json').read_bytes(),
    }
    decision_raw = Path(decision_path).read_bytes()
    decision = json.loads(decision_raw)
    template_raw = (proposal / 'review.template.json').read_bytes()
    validate_decision(decision, json.loads(template_raw), inputs)
    plan = json.loads(inputs['plan_sha256'])
    kit_raw = (root / 'reports/research3_reviewer_kit_v1.zip').read_bytes()
    if digest(kit_raw) != plan['review_kit_sha256']:
        raise ValueError('original review kit changed')
    with tempfile.TemporaryDirectory(prefix='r3-review-receipt-') as temporary:
        tmp = Path(temporary)
        kit = tmp / 'kit'
        kit.mkdir()
        safe_unpack_kit(kit_raw, kit)
        # Validate the same bytes that will be archived, avoiding a changing input.
        returned_copy = tmp / 'return.zip'
        returned_copy.write_bytes(inputs['phase_1_return_sha256'])
        result = subprocess.run(
            [sys.executable, 'review.py', 'validate-return', '--input', str(returned_copy)],
            cwd=kit, capture_output=True, text=True, check=True, timeout=120)
        validation = json.loads(result.stdout)
    # Approval of the amendment is separate from mutable live source readiness.
    from prepare_calibration_expansion import prepare
    with tempfile.TemporaryDirectory(prefix='r3-amendment-check-') as temporary:
        path = Path(temporary) / 'amendment.yaml'
        path.write_bytes(inputs['amendment_sha256'])
        current_plan = prepare(root, path)
    if current_plan != plan:
        raise ValueError('current source/asset plan differs from approved proposal')
    readiness = validation['readiness']
    if (validation['reviewed_binary_labels'] != 60 or readiness['provider_review_rows'] != 60
            or readiness['excluded']):
        raise ValueError('complete 60-target pilot return required')
    import io
    with zipfile.ZipFile(io.BytesIO(inputs['phase_1_return_sha256'])) as archive:
        approval = json.loads(archive.read('approval.json'))
        events = [json.loads(line) for line in archive.read('progress.jsonl').splitlines()][1:]
    if approval['reviewer_name'] != decision['reviewer_name']:
        raise ValueError('pilot and amendment reviewers differ; explicit reconciliation required')
    counts = {key: sum(row['verdict'] == key for row in events)
              for key in ('correct', 'incorrect', 'unreviewable')}
    receipt = {
        'schema_version': 'research3-expansion-preparation-handoff/v1',
        'status': 'pilot_and_amendment_verified_collection_not_started',
        'reviewer_name': decision['reviewer_name'],
        'human_identity_cryptographically_authenticated': False,
        'pilot_latest_binary_labels': validation['reviewed_binary_labels'],
        'pilot_journal_event_counts': counts,
        'pilot_calibration_coverage_blockers': readiness['blockers'],
        'amendment_gates_accepted': sorted(GATES),
        'current_plan_matches_approved_plan': True,
        'scheduled_primary_attempts': plan['primary_attempts'],
        'scheduled_diagnostic_attempts': plan['diagnostic_attempts'],
        'new_expansion_observations_in_this_package': 0,
        'pilot_in_final_fit_or_validation': False,
        'calibration_approved': False, 'campaign_authorized': False,
        'execution_authorized_by_this_package': False,
        'outstanding_gates': [
            'exact_diagnostic_assets_build_and_static_visual_preflight',
            'exact_diagnostic_assets_review_before_collection_per_approved_amendment',
            'execution_input_and_resource_guard_freeze',
            'development_capture_complete_before_validation_capture',
            'new_evidence_item_by_item_presentation_checks_and_portable_kit',
            'new_human_labels_and_separate_calibration_fit_protocol',
        ],
    }
    readme = '''# Research 3 expansion preparation handoff

This is NOT the next observation review kit. It contains zero new expansion
observations and requires no repeat review of the accepted 60-item pilot.

The original return, usability audit, amendment decision and frozen proposal are
preserved byte-for-byte. return_validation.json is the original kit validator's
result: a structurally valid return can still have blocked calibration coverage.
receipt.json records current source/asset-plan agreement without granting launch,
calibration or protected evaluation authority. Hashes do not authenticate people.

Human review provenance must also be confirmed through the researcher's normal
communication channel. Rapid recording timestamps do not establish how long
visual inspection took. This tool does not generate or substitute judgments.

Collection is still gated by exact diagnostic asset construction, visual/static
preflight and asset review, plus execution-input/resource checks. The accepted
amendment explicitly requires these before collection; general acceptance of
treatment categories is not approval of assets that do not yet exist.

Planned final observation handoff: retain separate development, validation and
diagnostic panels. Keep validation verdicts unavailable to model selection until
the development-only model is fixed. Retain nondetections and failed attempts
without inventing labels. Review counts are determined by usable evidence, not
assumed equal to 560 primary plus 80 diagnostic attempts. A fixed schedule does
not guarantee coverage, and insufficient coverage requires a new amendment.

Interpretation corrections (original reviewer documents remain unchanged):
- Static footprint checks do not guarantee visibility or live safety.
- Resource guards reduce, but do not guarantee zero, Research 2 interference.
- Validation maps 11–14 appeared in the pilot: these are not unseen worlds or
  protected held-out maps. New validation outcomes must remain excluded from fit.
- Pilot residual separation is not a general accuracy or calibration guarantee.
- Fixed-budget stopping controls one source of bias; it does not eliminate all bias.

No Research 1/2 files, jobs or old evidence are modified by this packaging tool.
Do not distribute reviewer-identifying returns publicly without authorization.
'''
    files = {
        'my-review-return.zip': inputs['phase_1_return_sha256'],
        'amendment_review_decision.json': decision_raw,
        'phase_1_rubric_usability_audit.md': inputs['phase_1_usability_audit_sha256'],
        'amendment.input.yaml': inputs['amendment_sha256'],
        'plan.json': inputs['plan_sha256'],
        'review.template.json': template_raw,
        'return_validation.json': encode(validation),
        'receipt.json': encode(receipt),
        'README.md': readme.encode(),
    }
    files['manifest.json'] = encode({
        'schema_version': 'research3-expansion-handoff-files/v1',
        'files': {name: digest(raw) for name, raw in files.items()},
    })
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        with (output / name).open('xb') as stream:
            stream.write(raw)
    with zipfile.ZipFile(output.with_suffix('.zip'), 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in files.items():
            archive.writestr(name, raw)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--return-zip', required=True, type=Path)
    parser.add_argument('--decision', required=True, type=Path)
    parser.add_argument('--usability-audit', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(package(ROOT, args.return_zip, args.decision, args.usability_audit,
                             args.output), indent=2))


if __name__ == '__main__':
    main()
