#!/usr/bin/env python3
"""Bind a validated human return to the accepted plan and fit the P2 classwise candidate.

`develop`: verify the development kit and its return, export the human binary
labels through the existing exporter, bind each label to its prespecified map
and view group, check the accepted coverage floors, fit the four class
temperatures on development only, run leave-one-map-out diagnostics, and write
a development artifact plus a freeze proposal for human approval. Nothing is
frozen or released here.

`validate`: after the human release gate, evaluate the frozen development
temperatures on the validation return without refitting and apply the accepted
point-estimate admission screen. A failed screen is reported, not waived.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import portable_physical_review as portable  # noqa: E402
import classwise_temperature_candidate as classwise  # noqa: E402
from run_expansion_collection import load_plan  # noqa: E402

PROTOCOL_DOC = ROOT / 'docs/CALIBRATION_METHOD_PROPOSAL_20260912.md'
AMENDMENT = ROOT / 'configs/physical_calibration_expansion_amendment_v1.yaml'
DEV_MAPS = [f'r3geo_base_r{i:03d}' for i in range(1, 11)]
VAL_MAPS = [f'r3geo_base_r{i:03d}' for i in range(11, 15)]


def sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_once(path, payload):
    with Path(path).open('x') as stream:
        json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def labelled_rows(kit_root, return_zip, partition):
    """Human binary labels from a validated return, bound to prespecified plan identities."""
    kit_root = Path(kit_root).resolve()
    portable.activate()
    previous = os.getcwd()
    os.chdir(kit_root)
    try:
        validation = portable.validate_return(kit_root, Path(return_zip).resolve())
        with zipfile.ZipFile(return_zip) as archive:
            files = {name: archive.read(name) for name in archive.namelist()}
        with tempfile.TemporaryDirectory(prefix='r3-labels-') as temporary:
            out = Path(temporary)
            for name, raw in files.items():
                (out / name).write_bytes(raw)
            requirements = json.loads(files['requirements.json'])
            reviewed, samples, readiness = portable.export_payload(
                kit_root / 'inventory.json', kit_root / 'qa.jsonl', out / 'progress.jsonl', requirements,
                evidence=kit_root / 'evidence.json', policy=out / 'policy.json')
    finally:
        os.chdir(previous)
    plan, plan_sha, _ = load_plan()
    by_run = {row['candidate_id']: row for row in plan['rows'] if row['partition'] == partition}
    bindings = {b['observation_id']: b for b in readiness['joint_review_contract']['accepted_label_bindings']}
    rows = []
    for task in reviewed:
        binding = bindings[task['observation_id']]
        plan_row = by_run.get(binding['run_id'])
        if plan_row is None or plan_row['entity_id'] != task['entity_id'] or plan_row['category'] != task['category']:
            raise ValueError('reviewed label is not the prespecified entity of its attempt: ' + binding['run_id'])
        rows.append(dict(partition=partition, panel='primary_expansion', reviewer_type='human',
                         reviewer_name=binding['reviewer_id'], map_id=plan_row['map_id'], category=task['category'],
                         view_group=plan_row['view_group'], seed=plan_row['seed'], run_id=binding['run_id'],
                         correct=bool(task['correct']), observation_id=task['observation_id'],
                         probability=float(task['probability']), recorded_at=binding['recorded_at']))
    return rows, readiness, validation, plan_sha


def develop(args):
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    rows, readiness, validation, plan_sha = labelled_rows(args.kit, args.return_zip, 'development')
    coverage_policy = yaml.safe_load(AMENDMENT.read_text())['coverage']
    accounting = json.loads(Path(args.accounting).read_bytes())
    report = json.loads(Path(args.collection_report).read_bytes())
    if accounting.get('plan_sha256') != plan_sha or report.get('plan_sha256') != plan_sha or report.get('partition') != 'development':
        raise ValueError('accounting and collection report must bind the accepted development plan')
    fit = classwise.fit_development(rows, DEV_MAPS)
    folds = classwise.leave_one_map_out(rows, DEV_MAPS) if fit['classes'] else None
    with (output / 'development_labels.jsonl').open('x') as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True) + '\n')
    artifact = dict(schema_version='research3-expansion-development-calibration-candidate/v1',
                    status=fit['status'], partition='development', method='classwise_temperature_scaling_p2',
                    classes=({c: dict(temperature=v['temperature'], objective=v['objective'], boundary=v['boundary'],
                                      samples=v['samples']) for c, v in fit['classes'].items()} if fit['classes'] else None),
                    grid=list(classwise.GRID), coverage=fit['coverage'], coverage_policy=coverage_policy,
                    export_readiness=readiness, labels=len(rows), label_file_sha256=sha_file(output / 'development_labels.jsonl'),
                    leave_one_map_out=([dict(held_development_map=f['held_development_map'], fit_status=f['fit']['status'],
                                             temperatures=({c: f['fit']['classes'][c]['temperature'] for c in classwise.CLASSES}
                                                           if f['fit']['classes'] else None),
                                             diagnostic=f['diagnostic']) for f in folds] if folds else None),
                    attempt_accounting=dict(sha256=sha_file(args.accounting), scheduled=accounting['scheduled'],
                                            accounted=accounting['accounted'], status_counts=accounting['status_counts'],
                                            review_targets=accounting['review_targets']),
                    provenance=dict(plan_sha256=plan_sha, kit_manifest_sha256=sha_file(Path(args.kit) / 'kit_manifest.json'),
                                    return_sha256=sha_file(args.return_zip), collection_report_sha256=sha_file(args.collection_report),
                                    snapshot_sha256=report.get('snapshot_sha256'), protocol_doc_sha256=sha_file(PROTOCOL_DOC),
                                    classwise_module_sha256=sha_file(ROOT / 'scripts/classwise_temperature_candidate.py'),
                                    amendment_sha256=sha_file(AMENDMENT)),
                    validation_used=False, pilot_or_diagnostic_rows_included=False, human_freeze_approved=False,
                    written_at_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    if fit['classes']:
        artifact['full_grid_objectives'] = {c: v['objectives'] for c, v in fit['classes'].items()}
    write_once(output / 'development_calibration_candidate.json', artifact)
    proposal = dict(schema_version='research3-expansion-development-freeze-proposal/v1', status='proposed_not_frozen',
                    development_model_sha256=sha_file(output / 'development_calibration_candidate.json'),
                    fit_status=fit['status'], coverage_passed=fit['coverage']['passed'], coverage_deficits=fit['coverage']['deficits'],
                    export_blockers=readiness['blockers'],
                    temperatures=({c: v['temperature'] for c, v in fit['classes'].items()} if fit['classes'] else None),
                    provenance=artifact['provenance'],
                    human_decision_required='approve or reject this exact development freeze before releasing the validation key',
                    release_gate_template=dict(schema_version='research3-validation-release-gate/v1', status='pending',
                                               development_model_sha256=sha_file(output / 'development_calibration_candidate.json'),
                                               calibration_protocol_sha256=sha_file(PROTOCOL_DOC), approved_by='', approved_at='',
                                               protected_outcomes_consulted=False, validation_results_inspected=False),
                    human_labels_generated=False, calibration_frozen=False)
    write_once(output / 'development_freeze_proposal.json', proposal)
    print(json.dumps({k: proposal[k] for k in ('fit_status', 'coverage_passed', 'coverage_deficits', 'export_blockers', 'temperatures')}))


def validate(args):
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    model = json.loads(Path(args.development_model).read_bytes())
    if model.get('classes') is None or model.get('partition') != 'development':
        raise ValueError('fitted development model required')
    gate = json.loads(Path(args.release_gate).read_bytes())
    if (gate.get('schema_version') != 'research3-validation-release-gate/v1' or gate.get('status') != 'approved'
            or gate.get('development_model_sha256') != sha_file(args.development_model) or not gate.get('approved_by', '').strip()):
        raise PermissionError('human-approved release gate bound to this exact development model required')
    rows, readiness, validation, plan_sha = labelled_rows(args.kit, args.return_zip, 'validation')
    temperatures = {c: v['temperature'] for c, v in model['classes'].items()}
    evaluation = classwise.evaluate(rows, 'validation', VAL_MAPS, temperatures)
    accounting = json.loads(Path(args.accounting).read_bytes())
    full_accounting = (accounting.get('plan_sha256') == plan_sha and accounting.get('partition') == 'validation'
                       and accounting.get('scheduled') == accounting.get('accounted') == 160)
    screen = classwise.admission_screen(model['coverage'], evaluation, full_attempt_accounting_verified=bool(full_accounting))
    with (output / 'validation_labels.jsonl').open('x') as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True) + '\n')
    result = dict(schema_version='research3-expansion-validation-evaluation/v1', partition='validation',
                  development_model_sha256=sha_file(args.development_model), release_gate_sha256=sha_file(args.release_gate),
                  temperatures=temperatures, labels=len(rows), evaluation=evaluation, admission_screen=screen,
                  export_readiness=readiness, refit_performed=False, human_model_approved=False,
                  provenance=dict(plan_sha256=plan_sha, kit_manifest_sha256=sha_file(Path(args.kit) / 'kit_manifest.json'),
                                  return_sha256=sha_file(args.return_zip), accounting_sha256=sha_file(args.accounting)),
                  written_at_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    write_once(output / 'validation_evaluation.json', result)
    print(json.dumps(dict(labels=len(rows), screen=screen)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p_dev = sub.add_parser('develop')
    p_dev.add_argument('--kit', type=Path, required=True, help='extracted development kit root')
    p_dev.add_argument('--return-zip', type=Path, required=True)
    p_dev.add_argument('--accounting', type=Path, required=True)
    p_dev.add_argument('--collection-report', type=Path, required=True)
    p_dev.add_argument('--output', type=Path, required=True)
    p_dev.set_defaults(func=develop)
    p_val = sub.add_parser('validate')
    p_val.add_argument('--kit', type=Path, required=True, help='extracted validation kit root')
    p_val.add_argument('--return-zip', type=Path, required=True, help='opened plaintext validation return')
    p_val.add_argument('--development-model', type=Path, required=True)
    p_val.add_argument('--release-gate', type=Path, required=True)
    p_val.add_argument('--accounting', type=Path, required=True)
    p_val.add_argument('--output', type=Path, required=True)
    p_val.set_defaults(func=validate)
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
