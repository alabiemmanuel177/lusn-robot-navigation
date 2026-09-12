import hashlib
import json
from pathlib import Path
import runpy

import pytest

MODULE = runpy.run_path(str(Path(__file__).parents[1] / 'scripts/audit_physical_interruption.py'))


def fixture(tmp_path, collision=0, timeout=False, decisions=True):
    evidence = {'schema_version': 'research3-live-measurements/v2', 'run_id': 'synthetic',
                'episode_started_at_ns': 1, 'episode_ended_at_ns': 200000001,
                'ground_truth_positions': [[0, 0], [.1, 0]], 'ground_truth_timestamps_ns': [1, 100000001],
                'collision_count': collision, 'timeout': timeout,
                'terminal_ground_truth': [], 'expected_terminal_region_id': 'room',
                'decisions': [{'decided_at_ns': 100}] if decisions else []}
    raw = json.dumps(evidence).encode()
    (tmp_path / 'measurements.json').write_bytes(raw)
    summary = {'schema_version': 'research3-live-summary/v3', 'run_id': 'synthetic',
               'partition': 'development', 'protected_test_routes_used': False,
               'infrastructure_failure': True, 'measurements_sha256': hashlib.sha256(raw).hexdigest(),
               'episode_started_at_ns': 1, 'episode_ended_at_ns': 200000001, 'timeout': timeout,
               'collision': bool(collision), 'terminal_radius_m': 1.0}
    (tmp_path / 'summary.json').write_text(json.dumps(summary))


@pytest.mark.parametrize('collision,timeout', [(1, False), (0, True)])
def test_known_partial_failure_dominates_unknown_terminal(tmp_path, collision, timeout):
    fixture(tmp_path, collision, timeout)
    result = MODULE['audit'](tmp_path)
    assert result['navigation_success'] is False and result['instruction_completion'] is False
    assert result['terminal_identity_correct'] is None and result['instruction_dispatch_established']


def test_partial_zero_events_do_not_become_completed_trial_negatives(tmp_path):
    fixture(tmp_path)
    result = MODULE['audit'](tmp_path)
    assert result['collision'] is result['timeout'] is result['navigation_success'] is None


def test_no_policy_decision_does_not_establish_dispatch(tmp_path):
    fixture(tmp_path, decisions=False)
    assert not MODULE['audit'](tmp_path)['instruction_dispatch_established']


def test_changed_measurements_rejected(tmp_path):
    fixture(tmp_path)
    (tmp_path / 'measurements.json').write_text('{}')
    with pytest.raises(ValueError, match='checksum'):
        MODULE['audit'](tmp_path)


def test_protected_summary_rejected_before_measurements(tmp_path, monkeypatch):
    fixture(tmp_path)
    path = tmp_path / 'summary.json'
    summary = json.loads(path.read_text())
    summary['partition'] = 'test'
    path.write_text(json.dumps(summary))
    monkeypatch.setattr(Path, 'read_bytes', lambda *a: pytest.fail('protected measurements accessed'))
    with pytest.raises(ValueError, match='non-protected'):
        MODULE['audit'](tmp_path)


def test_interrupted_collision_exports_as_failure_with_partial_audit_retained(tmp_path):
    fixture(tmp_path, collision=1)
    identity = {'episode_id': 'episode-B1', 'system_id': 'B1', 'variant_id': 'base-r001-truthful_original-s0',
                'base_instruction_id': 'base-r001', 'partition': 'development', 'paired_block_index': 0}
    request = {**identity, 'run_id': 'synthetic', 'map_id': 'r3geo_base_r001', 'protected_test_routes_used': False}
    (tmp_path / 'request.json').write_text(json.dumps(request))
    path = tmp_path / 'summary.json'
    summary = json.loads(path.read_text())
    summary.update(system_id='B1', variant_id=identity['variant_id'])
    path.write_text(json.dumps(summary))
    export = runpy.run_path(str(Path(__file__).parents[1] / 'scripts/export_physical_campaign_outcomes.py'))['export']
    report = export({'schema_version': 'research3-physical-comparison-plan/v1', 'episodes': [identity]},
                    [{'episode_id': 'episode-B1', 'run_directory': str(tmp_path)}])
    assert report['standalone_outcome_list_exportable']
    row = report['outcomes'][0]
    assert row['collision'] is True and row['instruction_completion'] is False
    assert row['infrastructure_failure'] and row['interruption_audit']['terminal_evidence_issue']
