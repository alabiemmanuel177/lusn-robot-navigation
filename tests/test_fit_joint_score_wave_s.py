from copy import deepcopy
import json
from pathlib import Path
import pytest

from fit_joint_score_wave_s import (protocol_acceptance, reviewed_rows, fit_models,
                                  validate_execution, sha)
from joint_score_components import digest, FEATURE_ORDER, CLASSES
from prepare_joint_score_protocol import ROOT


def test_actual_protocol_review_is_accepted_but_not_execution():
    root = ROOT/'reports/joint_score_protocol_20260924_v1'
    review = json.loads((root/'review_decision_CONVERSATION_FINAL.json').read_text())
    protocol_acceptance(review, sha(ROOT/'docs/SCORE_LEARNING_COLLECTION_PROTOCOL_20260924.md'), sha(root/'schedule.json'))
    assert review['grants_execution_by_itself'] is False
    with pytest.raises(ValueError):
        validate_execution({}, review, protocol_sha='a', schedule_sha='b')


@pytest.fixture
def fixture():
    schedule = json.loads((ROOT/'reports/joint_score_protocol_20260924_v1/schedule.json').read_text())
    attempts, labels = [], []
    for i, slot in enumerate(s for s in schedule['rows'] if s['wave'] == 'S'):
        # Entirely invented observations/verdicts, never exported as human data.
        positive = slot['seed'] == 101
        e = dict(frame_id='invented-'+str(i), observed_at_ns=i, category=slot['acquisition_class'],
                 entity_id='invented', source='synthetic', source_index=0, box=[0, 0, 100, 100],
                 map_pose=[0., 0.], raw_score=.8 if positive else .2, feature_order=list(FEATURE_ORDER),
                 features=[1., .5 if positive else -.5, 1., 0., .1], support={}, reference_distance_m=.09)
        e['emission_id'] = digest(e)
        attempts.append(dict(attempt_id=slot['attempt_id'], wave='S', status='completed',
            capture_uuid='invented-'+str(i), content_sha256=digest(i), processing_status='completed', emissions=[e]))
        verdict = 'correct' if positive else 'incorrect'
        labels.append(dict(emission_id=e['emission_id'], emission_sha256=digest(e),
            dimensions=dict(category=verdict, instance='correct', reference_point='correct'),
            joint_verdict=verdict, yaw_metadata='not_applicable'))
    ledger = dict(schema_version='research3-jsc-wave-evidence/v1', wave='S', attempts=attempts)
    review = dict(schema_version='research3-jsc-human-labels/v1', wave='S', reviewer_type='human',
        reviewer_name='SYNTHETIC TEST ATTESTATION — NOT A REAL REVIEW', reviewed_at='2026-01-01T00:00:00+00:00',
        evidence_sha256=digest(ledger), rows=labels)
    return schedule, ledger, review


def test_synthetic_full_wave_join_fit_and_40_folds(fixture):
    rows, excluded, attempts = reviewed_rows(*fixture)
    result = fit_models(rows)
    assert len(rows) == 400 and not excluded and len(attempts) == 400
    assert set(result['models']) == set(CLASSES)
    assert len(result['leave_one_map_out']) == 40
    assert all(f['status'] == 'fitted' for f in result['leave_one_map_out'])
    assert not result['runtime_admitted'] and not result['upstream_freeze_approved']


@pytest.mark.parametrize('mode', ['wrong_wave', 'missing_attempt', 'duplicate_label', 'wrong_evidence',
    'not_human', 'joint_inconsistent', 'missing_dimension', 'foreign_label', 'wrong_emission',
    'processing_failed', 'borrowed_class', 'reused_capture'])
def test_fail_closed_review_joins(fixture, mode):
    schedule, ledger, review = deepcopy(fixture)
    if mode == 'wrong_wave': ledger['wave'] = 'V'
    elif mode == 'missing_attempt': ledger['attempts'].pop()
    elif mode == 'duplicate_label': review['rows'].append(deepcopy(review['rows'][0]))
    elif mode == 'wrong_evidence': review['evidence_sha256'] = 'bad'
    elif mode == 'not_human': review['reviewer_type'] = 'agent'
    elif mode == 'joint_inconsistent': review['rows'][0]['joint_verdict'] = 'incorrect'
    elif mode == 'missing_dimension': review['rows'][0]['dimensions'].pop('instance')
    elif mode == 'foreign_label': review['rows'][0]['emission_id'] = 'old-pilot'
    elif mode == 'wrong_emission': review['rows'][0]['emission_sha256'] = 'bad'
    elif mode == 'processing_failed': ledger['attempts'][0]['processing_status'] = 'error'
    elif mode == 'borrowed_class': ledger['attempts'][0]['emissions'][0]['category'] = 'doorway'
    elif mode == 'reused_capture': ledger['attempts'][1]['capture_uuid'] = ledger['attempts'][0]['capture_uuid']
    if mode != 'wrong_evidence': review['evidence_sha256'] = digest(ledger)
    with pytest.raises((ValueError, PermissionError)):
        reviewed_rows(schedule, ledger, review)


def test_outcome_floors_and_unfit_folds_remain_visible(fixture):
    rows, _, _ = reviewed_rows(*fixture)
    fewer = []
    for c in CLASSES:
        for m in sorted({r['map_id'] for r in rows}):
            options = [r for r in rows if r['category'] == c and r['map_id'] == m]
            desired = int(int(m[-3:]) <= 5)
            fewer.append(next(r for r in options if r['y'] == desired))
    result = fit_models(fewer)
    assert all(f['status'] == 'unfit' for f in result['leave_one_map_out'])
    with pytest.raises(ValueError, match='five correct'):
        fit_models([dict(r, y=1) for r in rows])


def test_unreviewable_not_converted_to_negative(fixture):
    schedule, ledger, review = deepcopy(fixture)
    v = review['rows'][0]
    v.update(dimensions=dict(category='unreviewable', instance='correct', reference_point='correct'),
             joint_verdict='unreviewable', reason='synthetic ambiguous image')
    rows, excluded, _ = reviewed_rows(schedule, ledger, review)
    assert len(rows) == 399 and len(excluded) == 1


def test_execution_manifest_checks_actual_files(tmp_path):
    file = tmp_path/'asset'; file.write_text('synthetic fixture')
    groups = ('worlds', 'scenes', 'maps', 'expanded_robot', 'camera_bridge', 'detector_ocr_assets',
              'environment', 'collection_scoring_sources', 'static_clearance_audit', 'transport_preflight_audit')
    m = dict(schema_version='research3-jsc-execution/v1', wave='S', protocol_sha256='p', schedule_sha256='s',
             preflight_status='passed', serial=True, input_sha256={str(file): sha(file)},
             asset_groups={g: [str(file)] for g in groups})
    a = dict(reviewer_type='human', reviewer_name='SYNTHETIC TEST', reviewed_at='2026-01-01T00:00:00+00:00',
             decision='authorize_wave_s_collection', execution_manifest_sha256=digest(m),
             authorizes_validation_or_protected_access=False)
    validate_execution(m, a, protocol_sha='p', schedule_sha='s')
    file.write_text('changed')
    with pytest.raises(ValueError, match='changed'):
        validate_execution(m, a, protocol_sha='p', schedule_sha='s')
