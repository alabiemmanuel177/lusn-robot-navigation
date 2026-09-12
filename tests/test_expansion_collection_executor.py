"""Offline tests for the expansion collection executor; no ROS or simulator."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import run_expansion_collection as executor  # noqa: E402


def test_plan_is_bound_to_the_human_accepted_decision(tmp_path):
    plan, plan_sha, decision = executor.load_plan()
    assert len(plan['rows']) == 560 and decision['overall_decision'] == 'accept'
    altered = tmp_path / 'plan.json'
    altered.write_text(json.dumps(dict(plan, rows=plan['rows'][:-1])))
    with pytest.raises(PermissionError):
        executor.load_plan(altered)


def test_command_pins_exact_target_profile_and_instrumentation():
    plan, _, _ = executor.load_plan()
    row = dict(plan['rows'][0], run_id=plan['rows'][0]['candidate_id'])
    argv = executor.command(row, snapshot='/tmp/snapshot.json', domain=89, timeout=90)
    assert argv[:4] == ['nice', '-n', '15', 'python3']
    assert argv[argv.index('--capture-entity-id') + 1] == row['entity_id']
    assert argv[argv.index('--run-id') + 1] == row['candidate_id']
    assert '--allow-coexistence-trial' not in argv and '--camera-settings-freeze' not in argv
    validation = next(dict(r, run_id=r['candidate_id']) for r in plan['rows'] if r['partition'] == 'validation')
    argv = executor.command(validation, snapshot='/tmp/snapshot.json', domain=89, timeout=90,
                            freeze='/tmp/freeze.json', development_report='/tmp/report.json')
    assert '--camera-settings-freeze' in argv and '--development-complete-report' in argv
    assert executor.profile_for(validation).parent.name == 'profiles'


def test_classification_distinguishes_prearm_failures(tmp_path):
    run = tmp_path / 'run'
    (run / 'perception_capture').mkdir(parents=True)
    (run / 'failure.json').write_text(json.dumps(dict(error='stack exited before arming')))
    outcome = executor.classify(run)
    assert outcome['status'] == 'infrastructure_failure' and outcome['predispatch'] is True
    (run / 'perception_capture/armed.json').write_text('{}')
    assert executor.classify(run)['predispatch'] is False
    (run / 'expansion_attempt.json').write_text(json.dumps(dict(status='nondetection', reasons=[], selected_observation=None)))
    assert executor.classify(run)['status'] == 'nondetection'


def test_development_report_gate_rejects_incomplete_or_foreign_reports(tmp_path):
    _, plan_sha, _ = executor.load_plan()
    report = tmp_path / 'report.json'
    base = dict(schema_version=executor.REPORT_SCHEMA, partition='development', plan_sha256=plan_sha, complete=True,
                scheduled=400, accounted=400, human_labels_generated=False, attempts=[])
    report.write_text(json.dumps(base))
    with pytest.raises(ValueError):
        executor.validate_development_complete_report(report)
    report.write_text(json.dumps(dict(base, partition='validation')))
    with pytest.raises(PermissionError):
        executor.validate_development_complete_report(report)
    report.write_text(json.dumps(dict(base, complete=False)))
    with pytest.raises(PermissionError):
        executor.validate_development_complete_report(report)


def test_per_view_freeze_binds_one_validation_view(tmp_path):
    plan, _, _ = executor.load_plan()
    row = next(r for r in plan['rows'] if r['partition'] == 'validation')
    destination = tmp_path / 'freeze.json'
    executor.per_view_freeze(row, executor.FREEZE_TEMPLATE, destination)
    payload = json.loads(destination.read_text())
    assert len(payload['validation_views']) == 1 and payload['validation_views'][0]['capture_pose'] == row['capture_pose']
    assert payload['expansion_candidate_id'] == row['candidate_id'] and payload['schema_version'] == 'research3-engineering-camera-freeze/v2'
    from language_nav.camera_configuration import validate_camera_freeze, validate_frozen_capture_view
    validate_camera_freeze(destination, map_id=row['map_id'], profile=executor.profile_for(row), horizontal_fov=2.0)
    validate_frozen_capture_view(destination, map_id=row['map_id'], category=row['category'],
                                 pose=dict(row['capture_pose']), world=executor.world_for(row))


def test_feasibility_plan_is_paired_deterministic_and_development_only():
    import run_feasibility_navigation as feasibility
    rows = feasibility.plan_rows(1)
    assert len(rows) == 160 and rows == feasibility.plan_rows(1)
    blocks = {}
    for row in rows:
        blocks.setdefault(row['paired_block_index'], []).append(row['system_id'])
    assert all(sorted(systems) == ['B5', 'B6'] for systems in blocks.values())
    assert {row['base'] for row in rows} == set(feasibility.WORLDS)
    missing = [row for row in rows if row['condition'] == 'missing_landmark']
    assert all('physical_absence_worlds_v1' in row['world_directory'] for row in missing)
    argv = feasibility.command(rows[0], domain=89, timeout=90)
    assert '--capture-only' not in argv and '--system-id' in argv and '--calibration' not in argv
