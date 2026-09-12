import json
from pathlib import Path
import runpy

import pytest

MODULE = runpy.run_path(str(Path(__file__).parents[1] / 'scripts/export_physical_campaign_outcomes.py'))


@pytest.fixture
def setup(tmp_path, monkeypatch):
    scheduled = [{'episode_id': f'episode-{s}', 'system_id': s, 'variant_id': 'base-r001-truthful_original-s0',
                  'base_instruction_id': 'base-r001', 'partition': 'development', 'paired_block_index': 0,
                  'condition': 'truthful_original'} for s in ('B1', 'B6')]
    manifest = {'schema_version': 'research3-physical-comparison-plan/v1', 'episodes': scheduled}
    request = {**scheduled[0], 'run_id': 'fixture-run', 'map_id': 'r3geo_base_r001', 'protected_test_routes_used': False}
    (tmp_path / 'request.json').write_text(json.dumps(request))
    summary = {**request, 'schema_version': 'research3-live-summary/v3', 'navigation_success': False,
               'instruction_completion': False, 'terminal_identity_correct': None,
               'collision': True, 'timeout': False, 'infrastructure_failure': False}
    (tmp_path / 'summary.json').write_text(json.dumps(summary))
    (tmp_path / 'measurements.json').write_text(json.dumps({'episode_started_at_ns': 1, 'episode_ended_at_ns': 3,
                                                          'decisions': [{'decided_at_ns': 2}]}))
    # Synthetic callback verifies exporter integration; raw auditor has separate
    # trajectory/checksum regression tests. No actual experiment files are read.
    monkeypatch.setitem(MODULE['export'].__globals__, 'audit_summary', lambda path: json.loads(path.read_text()))
    return manifest, [{'episode_id': 'episode-B1', 'run_directory': str(tmp_path)}], tmp_path


def test_exports_audited_failure_and_preserves_unassigned_denominator(setup):
    manifest, assignments, _ = setup
    report = MODULE['export'](manifest, assignments)
    assert report['standalone_outcome_list_exportable']
    assert report['outcomes'][0]['collision'] is True
    assert report['outcomes'][0]['instruction_completion'] is False
    assert report['unassigned_episode_ids'] == ['episode-B6']
    assert not report['campaign_authorized']


def test_auditor_failure_is_unresolved_not_silently_dropped(setup, monkeypatch):
    manifest, assignments, _ = setup
    def fail(path):
        raise ValueError('retained infrastructure requires audit')
    monkeypatch.setitem(MODULE['export'].__globals__, 'audit_summary', fail)
    report = MODULE['export'](manifest, assignments)
    assert not report['standalone_outcome_list_exportable'] and report['outcomes'] == []
    assert len(report['unresolved_assignments']) == 1


def test_explicit_predispatch_failure_has_unknown_endpoints(setup):
    manifest, assignments, directory = setup
    (directory / 'summary.json').unlink()
    (directory / 'measurements.json').unlink()
    (directory / 'failure.json').write_text(json.dumps({'dispatched': False, 'error': 'setup failed'}))
    row = MODULE['export'](manifest, assignments)['outcomes'][0]
    assert row['attempted'] and not row['dispatched'] and row['infrastructure_failure']
    assert row['collision'] is row['instruction_completion'] is None


def test_ambiguous_failure_cannot_be_exported_as_predispatch(setup):
    manifest, assignments, directory = setup
    (directory / 'summary.json').unlink()
    (directory / 'failure.json').write_text(json.dumps({'raw_capture_retained': False}))
    assert not MODULE['export'](manifest, assignments)['standalone_outcome_list_exportable']


@pytest.mark.parametrize('field,value', [('run_id', 'different'), ('system_id', 'B6'), ('partition', 'test')])
def test_summary_identity_mismatch_retained_as_unresolved(setup, field, value):
    manifest, assignments, directory = setup
    path = directory / 'summary.json'
    row = json.loads(path.read_text())
    row[field] = value
    path.write_text(json.dumps(row))
    assert not MODULE['export'](manifest, assignments)['standalone_outcome_list_exportable']


def test_policy_dispatch_needs_positive_in_window_evidence(setup):
    manifest, assignments, directory = setup
    path = directory / 'measurements.json'
    row = json.loads(path.read_text())
    row['decisions'] = []
    path.write_text(json.dumps(row))
    assert not MODULE['export'](manifest, assignments)['standalone_outcome_list_exportable']


def test_duplicate_assignment_rejected(setup):
    manifest, assignments, _ = setup
    with pytest.raises(ValueError, match='duplicate'):
        MODULE['export'](manifest, assignments * 2)


def test_protected_schedule_rejected_before_run_file_access(setup, monkeypatch):
    manifest, assignments, _ = setup
    manifest['episodes'][0]['partition'] = 'test'
    monkeypatch.setattr(Path, 'read_text', lambda *a, **k: pytest.fail('protected run accessed'))
    with pytest.raises(ValueError, match='held-out'):
        MODULE['export'](manifest, assignments)
