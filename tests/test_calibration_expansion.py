"""Draft-planning tests; no captures, protected evidence or human approvals."""
import copy
import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('expansion_plan', ROOT / 'scripts/prepare_calibration_expansion.py')
PLAN = importlib.util.module_from_spec(spec); spec.loader.exec_module(PLAN)


@pytest.fixture
def amendment():
    return yaml.safe_load((ROOT / 'configs/physical_calibration_expansion_amendment_v1.yaml').read_bytes())


def test_draft_preserves_coverage_and_fixed_budget(amendment):
    PLAN.validate_amendment(amendment)
    assert amendment['coverage'] == PLAN.EXPECTED_COVERAGE
    assert 14 * 4 * 2 * 5 == amendment['phase_2']['primary_attempts']
    assert 10 * 4 * 2 == amendment['diagnostic_panel']['attempts']
    assert amendment['phase_2']['seed_repeats_count_as_independent_worlds'] is False


@pytest.mark.parametrize('key', ['execution_authorized', 'calibration_freeze_authorized', 'protected_access_authorized'])
def test_draft_cannot_grant_authority(amendment, key):
    amendment[key] = True
    with pytest.raises(ValueError, match='draft-only'): PLAN.validate_amendment(amendment)


def test_no_posthoc_coverage_reduction(amendment):
    amendment['coverage']['minimum_per_class_outcome'] = 1
    with pytest.raises(ValueError, match='unchanged'): PLAN.validate_amendment(amendment)


def test_protected_map_refused_before_any_source_read(amendment, tmp_path):
    amendment['phase_2']['validation_maps'].append(15)
    path = tmp_path / 'amendment.yaml'; path.write_text(yaml.safe_dump(amendment))
    with pytest.raises(ValueError, match='nonprotected'): PLAN.prepare(tmp_path, path)


@pytest.mark.parametrize('key', ['confidence_used_to_select_or_discard_observations', 'correctness_used_to_select_or_discard_observations'])
def test_no_score_or_label_selection(amendment, key):
    amendment['phase_2'][key] = True
    with pytest.raises(ValueError, match='selection'): PLAN.validate_amendment(amendment)


@pytest.mark.parametrize('section,key', [
    ('phase_1', 'existing_pilot_in_final_fit'),
    ('phase_1', 'anonymous_narrative_counts_are_verified_labels'),
    ('diagnostic_panel', 'included_in_calibration_fit_or_primary_validation'),
    ('diagnostic_panel', 'use_to_fill_primary_negative_quota')])
def test_no_promoting_pilot_stress_or_narrative(amendment, section, key):
    amendment[section][key] = True
    with pytest.raises(ValueError, match='labels'): PLAN.validate_amendment(amendment)


def test_schedule_cannot_grow_to_chase_outcomes(amendment):
    amendment['phase_2']['simulator_seeds'].append(3)
    with pytest.raises(ValueError, match='schedule'): PLAN.validate_amendment(amendment)


def test_plan_code_has_no_dispatch_api():
    text = (ROOT / 'scripts/prepare_calibration_expansion.py').read_text()
    assert 'subprocess' not in text
    assert 'no_execution_argv_generated' in text


def test_validation_uses_its_actual_frozen_profile_not_development_draft(tmp_path):
    a = tmp_path / 'reports/fresh_current_capture_20260911_v1/profiles/base-r011.yaml'
    b = tmp_path / 'reports/engineering_camera_settings_v3/profiles/base-r011.yaml'
    for path, raw in ((a, b'draft'), (b, b'frozen validation profile')):
        path.parent.mkdir(parents=True); path.write_bytes(raw)
    request = {'camera_profile_sha256': PLAN.sha(b)}
    assert PLAN.frozen_profile(tmp_path, 'base-r011', 11, request) == b
    b.write_bytes(b'changed')
    with pytest.raises(ValueError, match='changed'): PLAN.frozen_profile(tmp_path, 'base-r011', 11, request)
