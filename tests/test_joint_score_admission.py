import json
from pathlib import Path
import pytest

import joint_score_wave_s_admission as admission
from fit_joint_score_wave_s import sha
from joint_score_components import digest


@pytest.fixture
def admitted_args(tmp_path, monkeypatch):
    original = admission.ROOT
    source = tmp_path/admission.SOURCE
    source.parent.mkdir(parents=True)
    source.write_bytes((original/admission.SOURCE).read_bytes())
    packet = original/'reports/joint_score_protocol_20260924_v1'
    schedule = packet/'schedule.json'
    protocol = original/'docs/SCORE_LEARNING_COLLECTION_PROTOCOL_20260924.md'
    slot = json.loads(schedule.read_text())['rows'][0]
    fixture_asset = tmp_path/'test-asset'; fixture_asset.write_text('synthetic test only')
    groups = ('worlds', 'scenes', 'maps', 'expanded_robot', 'camera_bridge', 'detector_ocr_assets',
              'environment', 'collection_scoring_sources', 'static_clearance_audit', 'transport_preflight_audit')
    manifest = dict(schema_version='research3-jsc-execution/v1', wave='S', protocol_sha256=sha(protocol),
        schedule_sha256=sha(schedule), preflight_status='passed', serial=True,
        input_sha256={str(fixture_asset): sha(fixture_asset)}, asset_groups={g: [str(fixture_asset)] for g in groups})
    approval = dict(reviewer_type='human', reviewer_name='SYNTHETIC TEST ATTESTATION',
        reviewed_at='2026-01-01T00:00:00+00:00', decision='authorize_wave_s_collection',
        execution_manifest_sha256=digest(manifest), authorizes_validation_or_protected_access=False)
    mp, ap = tmp_path/'manifest.json', tmp_path/'approval.json'
    mp.write_text(json.dumps(manifest)); ap.write_text(json.dumps(approval))
    monkeypatch.setattr(admission, 'ROOT', tmp_path)
    monkeypatch.setattr(admission.os, 'getpriority', lambda *args: 19)
    monkeypatch.setattr(admission, 'coexistence_headroom', lambda: {'synthetic_test': True})
    return dict(attempt_id=slot['attempt_id'], output_root=tmp_path/'outputs', schedule_path=schedule,
        protocol_path=protocol, protocol_review_path=packet/'review_decision_CONVERSATION_FINAL.json',
        execution_manifest_path=mp, execution_approval_path=ap)


def test_unfinished_context_is_consumed_and_cannot_retry(admitted_args):
    with admission.admitted_attempt(**admitted_args) as (attempt, slot):
        assert slot['wave'] == 'S' and not attempt.closed
    summary = json.loads((attempt.output/'summary.json').read_text())
    assert summary['reason'] == 'interrupted_after_launch' and summary['consumed']
    with pytest.raises(ValueError, match='already started'):
        with admission.admitted_attempt(**admitted_args):
            pytest.fail('cannot retry')


def test_global_serial_lock_across_different_output_roots(admitted_args, tmp_path):
    with admission.admitted_attempt(**admitted_args):
        other = dict(admitted_args, output_root=tmp_path/'different')
        with pytest.raises(BlockingIOError):
            with admission.admitted_attempt(**other):
                pytest.fail('cannot collect concurrently')


def test_low_priority_and_resource_guard_required(admitted_args, monkeypatch):
    monkeypatch.setattr(admission.os, 'getpriority', lambda *args: 0)
    with pytest.raises(PermissionError, match='nice-19'):
        with admission.admitted_attempt(**admitted_args):
            pytest.fail('priority guard bypass')
    monkeypatch.setattr(admission.os, 'getpriority', lambda *args: 19)
    def no_headroom():
        raise RuntimeError('no headroom')
    monkeypatch.setattr(admission, 'coexistence_headroom', no_headroom)
    with pytest.raises(RuntimeError, match='headroom'):
        with admission.admitted_attempt(**admitted_args):
            pytest.fail('resource guard bypass')
    assert not (Path(admitted_args['output_root'])/admitted_args['attempt_id']).exists()


def test_protocol_acceptance_cannot_replace_execution_approval(admitted_args):
    admitted_args['execution_approval_path'] = admitted_args['protocol_review_path']
    with pytest.raises((ValueError, PermissionError)):
        with admission.admitted_attempt(**admitted_args):
            pytest.fail('protocol does not authorize execution')


def test_later_slot_cannot_skip_unstarted_earlier_slots(admitted_args):
    schedule = json.loads(Path(admitted_args['schedule_path']).read_text())
    admitted_args['attempt_id'] = schedule['rows'][1]['attempt_id']
    with pytest.raises(ValueError, match='earlier scheduled'):
        with admission.admitted_attempt(**admitted_args):
            pytest.fail('cannot reorder')
