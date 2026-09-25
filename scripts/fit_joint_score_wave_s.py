"""Gated Wave S fitting adapter. Never opens validation data or admits runtime.

All joins are hash-bound; human declarations are attestations, not authentication.
This command cannot supply missing human verdicts or execution authorization.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path

import numpy as np

from joint_score_components import CLASSES, FEATURE_ORDER, digest, duplicate_accounting, fit_numeric, predict, weights
from joint_score_collection import write_once
from prepare_joint_score_protocol import DECISIONS


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def human(record):
    if record.get('reviewer_type') != 'human' or not isinstance(record.get('reviewer_name'), str) or not record['reviewer_name'].strip():
        raise ValueError('explicit named human attestation required')
    if datetime.fromisoformat(record['reviewed_at']).utcoffset() is None:
        raise ValueError('timezone-aware review date required')


def protocol_acceptance(review, protocol_sha, schedule_sha):
    # Conversation record identifies the human through role/name; historical
    # schema did not require reviewer_type. Do not rewrite it to add a signature.
    if review.get('overall_decision') != 'accept' or set(review['decisions']) != set(DECISIONS):
        raise ValueError('complete protocol acceptance required')
    if any(r.get('decision') != 'accept' or not r.get('rationale') for r in review['decisions'].values()):
        raise ValueError('all seven explicit decisions required')
    if not review.get('reviewer_name') or not review.get('reviewer_role') or datetime.fromisoformat(review['reviewed_at']).utcoffset() is None:
        raise ValueError('named dated protocol review required')
    if review.get('protocol_sha256') != protocol_sha or review.get('schedule_sha256') != schedule_sha:
        raise ValueError('protocol/schedule review binding')
    if any(review.get(k) is not False for k in ('grants_execution_by_itself',
            'approves_unseen_labels_or_models', 'authorizes_validation_release_or_protected_access')):
        raise ValueError('protocol approval must not masquerade as broader authority')


def validate_execution(manifest, approval, *, protocol_sha, schedule_sha, verify_files=True):
    if manifest.get('schema_version') != 'research3-jsc-execution/v1' or manifest.get('wave') != 'S':
        raise ValueError('Wave S execution manifest required; C/V not authorized here')
    if manifest.get('protocol_sha256') != protocol_sha or manifest.get('schedule_sha256') != schedule_sha:
        raise ValueError('execution protocol binding')
    if manifest.get('preflight_status') != 'passed' or manifest.get('serial') is not True:
        raise ValueError('preflight and serial execution required')
    required = {'worlds', 'scenes', 'maps', 'expanded_robot', 'camera_bridge',
                'detector_ocr_assets', 'environment', 'collection_scoring_sources',
                'static_clearance_audit', 'transport_preflight_audit'}
    pins = manifest.get('input_sha256', {})
    groups = manifest.get('asset_groups', {})
    if set(groups) != required or not pins or any(not groups[k] for k in required):
        raise ValueError('all execution source/asset groups required')
    if any(path not in pins for paths in groups.values() for path in paths):
        raise ValueError('unpinned execution dependency')
    if verify_files:
        for path, expected in pins.items():
            if sha(path) != expected:
                raise ValueError('execution source/asset changed: '+path)
    human(approval)
    if approval.get('decision') != 'authorize_wave_s_collection' or approval.get('execution_manifest_sha256') != digest(manifest):
        raise PermissionError('explicit manifest-bound Wave S authority required')
    if approval.get('authorizes_validation_or_protected_access') is not False:
        raise PermissionError('no validation/protected authority here')


def reviewed_rows(schedule, ledger, review):
    expected = [r for r in schedule['rows'] if r['wave'] == 'S']
    attempts = ledger['attempts']
    if ledger.get('schema_version') != 'research3-jsc-wave-evidence/v1' or ledger.get('wave') != 'S':
        raise ValueError('Wave S evidence only')
    if len(expected) != 400 or [r['attempt_id'] for r in attempts] != [r['attempt_id'] for r in expected]:
        raise ValueError('complete ordered 400-attempt accounting required')
    if any(r['partition'] != 'development' for r in expected):
        raise ValueError('development only')
    if review.get('schema_version') != 'research3-jsc-human-labels/v1' or review.get('wave') != 'S':
        raise ValueError('new Wave S human labels required; no pilot transfer')
    human(review)
    if review.get('evidence_sha256') != digest(ledger):
        raise ValueError('review/evidence binding')
    review_by_id = {r['emission_id']: r for r in review['rows']}
    if len(review_by_id) != len(review['rows']):
        raise ValueError('duplicate label rows')
    for row in attempts:
        if row.get('wave') != 'S' or row['status'] not in ('completed', 'infrastructure_failure'):
            raise ValueError('explicit attempt status and wave')
        if row['status'] == 'completed' and row.get('processing_status') != 'completed':
            raise ValueError('empty inference requires explicit completion, not a missing process')
        if row['status'] == 'infrastructure_failure' and (not row.get('reason') or row.get('emissions')):
            raise ValueError('infrastructure failures cannot contribute labels')
    accounted = duplicate_accounting(attempts)
    accepted, excluded, expected_ids = [], [], set()
    for slot, attempt in zip(expected, accounted):
        if not attempt['fitting_eligible']:
            excluded.append(dict(attempt_id=slot['attempt_id'], reason=attempt.get('duplicate_scope', attempt['status'])))
            continue
        seen_entities = set()
        for emission in attempt['emissions']:
            e = dict(emission)
            identity = e.pop('emission_id')
            if digest(e) != identity or identity in expected_ids:
                raise ValueError('emission identity/hash binding')
            expected_ids.add(identity)
            if e['category'] != slot['acquisition_class'] or e['entity_id'] in seen_entities:
                raise ValueError('only acquisition-class, nonduplicate-instance emissions')
            seen_entities.add(e['entity_id'])
            if e['feature_order'] != list(FEATURE_ORDER):
                raise ValueError('fixed feature order')
            verdict = review_by_id.get(identity)
            if not verdict or verdict.get('emission_sha256') != digest(emission):
                raise ValueError('missing or mismatched new human verdict')
            dims = verdict['dimensions']
            if set(dims) != {'category', 'instance', 'reference_point'} or any(
                    v not in ('correct', 'incorrect', 'unreviewable') for v in dims.values()):
                raise ValueError('three human rubric dimensions required')
            yaw = verdict.get('yaw_metadata', 'not_applicable')
            if yaw not in ('not_applicable', 'correct', 'incorrect', 'unreviewable'):
                raise ValueError('yaw metadata verdict')
            values = list(dims.values()) + ([] if yaw == 'not_applicable' else [yaw])
            joint = 'incorrect' if 'incorrect' in values else 'correct' if all(v == 'correct' for v in values) else 'unreviewable'
            if verdict.get('joint_verdict') != joint:
                raise ValueError('joint verdict contradicts dimension judgments')
            if joint == 'unreviewable':
                if not verdict.get('reason'):
                    raise ValueError('unreviewable reason required')
                excluded.append(dict(emission_id=identity, reason=verdict['reason']))
            else:
                accepted.append(dict(emission_id=identity, category=e['category'], features=e['features'],
                                     y=int(joint == 'correct'), map_id=slot['map_id'], view_group=slot['view_group']))
    if set(review_by_id) != expected_ids:
        raise ValueError('unmatched/foreign labels cannot enter Wave S')
    return accepted, excluded, accounted


def fit_class(rows, required_maps):
    if {r['map_id'] for r in rows} != set(required_maps):
        raise ValueError('missing map/class binary emission')
    y = np.array([r['y'] for r in rows])
    if sum(y == 0) < 5 or sum(y == 1) < 5:
        raise ValueError('five correct and five incorrect required per class')
    w = weights(rows)
    model = fit_numeric([r['features'] for r in rows], y, w)
    model['weights'] = [dict(emission_id=r['emission_id'], weight=float(v)) for r, v in zip(rows, w)]
    return model


def fit_models(rows):
    maps = {f'r3geo_base_r{i:03}' for i in range(1, 11)}
    models, folds = {}, []
    for category in CLASSES:
        selected = [r for r in rows if r['category'] == category]
        models[category] = fit_class(selected, maps)
        for held in sorted(maps):
            train = [r for r in selected if r['map_id'] != held]
            test = [r for r in selected if r['map_id'] == held]
            try:
                fitted = fit_class(train, maps-{held})
                p = predict(fitted, [r['features'] for r in test])
                folds.append(dict(category=category, held_out_map=held, status='fitted',
                                  model=fitted, held_out_emission_ids=[r['emission_id'] for r in test],
                                  probabilities=p.tolist(),
                                  brier=float(np.sum(weights(test)*(p-np.array([r['y'] for r in test]))**2))))
            except ValueError as exc:
                folds.append(dict(category=category, held_out_map=held, status='unfit', reason=str(exc)))
    return dict(schema_version='research3-jsc-score-model-candidate/v1', wave='S',
                models=models, leave_one_map_out=folds, runtime_admitted=False,
                upstream_freeze_approved=False, calibration_validated=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('protocol', 'schedule', 'protocol-review', 'execution-manifest',
                 'execution-approval', 'evidence', 'human-review', 'output'):
        p.add_argument('--'+name, required=True, type=Path)
    args = p.parse_args()
    paths = vars(args)
    data = {k: json.loads(v.read_text()) for k, v in paths.items() if k not in ('protocol', 'output')}
    ps, ss = sha(args.protocol), sha(args.schedule)
    protocol_acceptance(data['protocol_review'], ps, ss)
    validate_execution(data['execution_manifest'], data['execution_approval'], protocol_sha=ps, schedule_sha=ss)
    ledger = data['evidence']
    if (ledger.get('protocol_sha256') != ps or ledger.get('schedule_sha256') != ss or
            ledger.get('execution_manifest_sha256') != digest(data['execution_manifest'])):
        raise ValueError('evidence source chain does not match approved execution')
    rows, excluded, attempts = reviewed_rows(data['schedule'], ledger, data['human_review'])
    model = fit_models(rows)
    model.update(input_sha256={k: sha(v) for k, v in paths.items() if k != 'output'},
                 excluded=excluded, attempt_accounting=attempts)
    write_once(args.output, model)


if __name__ == '__main__':
    main()
