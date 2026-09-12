import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/prepare_consolidated_review.py'
SPEC = importlib.util.spec_from_file_location('consolidated_review', SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def save(path, value):
    path.write_text(json.dumps(value))


@pytest.fixture
def capture(tmp_path):
    save(tmp_path / 'request.json', dict(run_id='synthetic', map_id='r3geo_base_r010',
         partition='development', protected_test_routes_used=False,
         asset_sha256={'map.pgm': '1' * 64}, source_revision='fixture-only',
         source_sha256={'fixture.py': '2' * 64}))
    media = tmp_path / 'perception_capture'
    media.mkdir()
    task = dict(schema_version='landmark-review-task/v1', observation_id='obs1',
                entity_id='chair1', region_id='region1', category='chair', source='rgbd',
                partition='development', observed_at_ns=1000000000, probability=.8,
                pixel=dict(u=1, v=1), depth_m=2., review_status='pending_human_review',
                reviewer_id='', correct=None)
    save(tmp_path / 'landmark_review_tasks.jsonl', task)
    trigger = {key: task[key] for key in ('observation_id', 'entity_id', 'region_id',
                                         'category', 'source', 'observed_at_ns')}
    trigger['confidence'] = .8
    frame = dict(rgb_stamp_ns=1000000000, depth_stamp_ns=1000000000,
                 trigger_observations=[trigger], camera_info={'k': [1.]},
                 camera_to_map={'transform': 'synthetic'}, transform_error=None)
    for kind, encoding, step in (('rgb', 'rgb8', 6), ('depth', '32FC1', 8)):
        raw = bytes(step * 2)
        (media / (kind + '.bin')).write_bytes(raw)
        frame[kind] = dict(file=kind + '.bin', sha256=hashlib.sha256(raw).hexdigest(),
                           bytes=len(raw), encoding=encoding, width=2, height=2, step=step)
    save(media / 'frame-000.json', frame)
    save(media / 'summary.json', {'frames': ['frame-000.json']})
    return tmp_path


def synthetic_qa(capture):
    row = MODULE.consolidate([capture])['items'][0]
    binding = {key: row[key] for key in ('run_id', 'observation_id', 'task_sha256',
               'frame_sha256', 'request_sha256', 'provider_tasks_sha256')}
    return dict(binding, schema_version='research3-machine-visual-qa/v1',
                attested_by='synthetic-unit-test-not-a-live-attestation',
                **{key: True for key in MODULE.QA_CHECKS})


def test_empty_is_blocked_with_explicit_coverage():
    result = MODULE.consolidate([])
    assert result['status'] == 'blocked'
    assert len(result['coverage']) == 56
    assert not result['coverage_complete']
    assert not result['study_complete']


def test_missing_live_inputs_blocked(tmp_path):
    result = MODULE.consolidate([tmp_path])
    assert result['runs'][0]['status'] == 'blocked'
    assert result['ready_items'] == 0


def test_exact_join_without_individual_qa_is_not_ready(capture):
    result = MODULE.consolidate([capture])
    assert result['items'][0]['status'] == 'awaiting_visual_qa'
    assert result['items'][0]['correct'] is None
    assert result['status'] == 'blocked'


def test_attested_item_is_unlabelled_and_coverage_still_partial(capture):
    result = MODULE.consolidate([capture], [synthetic_qa(capture)])
    assert result['ready_items'] == 1
    assert result['status'] == 'partial_human_review_handoff'
    assert result['items'][0]['correct'] is None
    assert result['items'][0]['human_reviewer_id'] == ''
    assert result['runs'][0]['source_sha256'] == {'fixture.py': '2' * 64}
    assert not result['detector_performance_validated']


@pytest.mark.parametrize('field', ['task_sha256', 'frame_sha256', 'request_sha256',
                                  'provider_tasks_sha256'])
def test_stale_attestation_rejected_retained(capture, field):
    qa = synthetic_qa(capture)
    qa[field] = 'stale'
    result = MODULE.consolidate([capture], [qa])
    assert result['rejected_items'] == 1
    assert 'stale_or_mismatched_visual_qa' in result['items'][0]['reasons']


def test_duplicate_qa_and_duplicate_provider_rows_rejected(capture):
    qa = synthetic_qa(capture)
    result = MODULE.consolidate([capture], [qa, qa])
    assert 'duplicate_visual_qa' in result['items'][0]['reasons']
    task_path = capture / 'landmark_review_tasks.jsonl'
    raw = task_path.read_text()
    task_path.write_text(raw + '\n' + raw)
    result = MODULE.consolidate([capture])
    assert result['rejected_items'] == 2


@pytest.mark.parametrize('change', [{'identity_decidable': False}, {'correct': True},
                                   {'attested_by': ''}])
def test_visual_qa_is_not_human_correctness(capture, change):
    qa = {**synthetic_qa(capture), **change}
    result = MODULE.consolidate([capture], [qa])
    assert result['ready_items'] == 0
    assert result['items'][0]['correct'] is None


def test_protected_rejected_before_missing_capture_access(tmp_path):
    save(tmp_path / 'request.json', dict(map_id='r3geo_base_r015', partition='development',
                                        protected_test_routes_used=False))
    with pytest.raises(ValueError, match='protected'):
        MODULE.consolidate([tmp_path])


def test_duplicate_run_rejected(capture):
    with pytest.raises(ValueError, match='duplicate'):
        MODULE.consolidate([capture, capture])


def test_missing_source_provenance_prevents_readiness(capture):
    path = capture / 'request.json'
    request = json.loads(path.read_text())
    del request['source_sha256']
    save(path, request)
    result = MODULE.consolidate([capture], [synthetic_qa(capture)])
    assert 'missing_map_or_source_provenance' in result['items'][0]['reasons']


def test_missing_other_run_prevents_full_handoff(capture):
    result = MODULE.consolidate([capture, capture / 'absent'], [synthetic_qa(capture)],
                               required_maps=['r3geo_base_r010'], required_classes=['chair'])
    assert result['coverage_complete']
    assert result['status'] == 'partial_human_review_handoff'


def test_create_once_cli_with_no_live_inputs(tmp_path):
    output = tmp_path / 'inventory.json'
    command = [sys.executable, str(SCRIPT), '--output', str(output)]
    assert subprocess.run(command, capture_output=True).returncode == 0
    before = output.read_bytes()
    assert json.loads(before)['status'] == 'blocked'
    assert subprocess.run(command, capture_output=True).returncode != 0
    assert output.read_bytes() == before
