import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('exact_join', Path(__file__).resolve().parents[1]
                                             / 'scripts/join_physical_review_capture.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def save(path, value):
    path.write_text(json.dumps(value))


@pytest.fixture
def capture(tmp_path):
    save(tmp_path / 'request.json', dict(run_id='fixture', map_id='r3geo_base_r010',
         partition='development', protected_test_routes_used=False))
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
                 camera_to_map={'transform': 'fixture'}, transform_error=None)
    for kind, encoding, step in (('rgb', 'rgb8', 6), ('depth', '32FC1', 8)):
        raw = bytes(step * 2)
        (media / (kind + '.bin')).write_bytes(raw)
        frame[kind] = dict(file=kind + '.bin', sha256=hashlib.sha256(raw).hexdigest(),
                           bytes=len(raw), encoding=encoding, width=2, height=2, step=step)
    save(media / 'frame-000.json', frame)
    save(media / 'summary.json', {'frames': ['frame-000.json']})
    return tmp_path


def test_exact_join_is_only_visual_qa_candidate(capture):
    result = module.join_capture(capture)
    assert result['joined_for_visual_qa'] == 1
    assert result['status'] == 'not_authorized_for_human_review'
    assert result['human_labels_generated'] is False


@pytest.mark.parametrize('field,value,reason', [
    ('observed_at_ns', 1000000001, 'missing_or_ambiguous_exact_frame'),
    ('pixel', {'u': 2, 'v': 1}, 'invalid_detector_pixel'),
    ('entity_id', 'different', 'provider_trigger_mismatch'),
    ('correct', True, 'invalid_pending_provider_task'),
    ('depth_m', -1, 'invalid_detector_depth'),
    ('probability', 2, 'invalid_probability'),
])
def test_invalid_task_rejected(capture, field, value, reason):
    path = capture / 'landmark_review_tasks.jsonl'
    task = json.loads(path.read_text())
    task[field] = value
    save(path, task)
    result = module.join_capture(capture)
    assert result['joined_for_visual_qa'] == 0
    assert reason in result['observations'][0]['reasons']


def test_duplicate_tasks_rejected(capture):
    path = capture / 'landmark_review_tasks.jsonl'
    raw = path.read_text()
    path.write_text(raw + '\n' + raw)
    assert module.join_capture(capture)['rejected'] == 2


def test_corrupt_media_rejected(capture):
    (capture / 'perception_capture/rgb.bin').write_bytes(bytes(5))
    assert module.join_capture(capture)['rejected'] == 1


def test_protected_map_rejected_before_capture_access(tmp_path):
    save(tmp_path / 'request.json', dict(map_id='r3geo_base_r015',
         partition='development', protected_test_routes_used=False))
    with pytest.raises(ValueError, match='non-protected'):
        module.join_capture(tmp_path)


def test_media_escape_rejected(capture):
    path = capture / 'perception_capture/frame-000.json'
    frame = json.loads(path.read_text())
    frame['rgb']['file'] = '../request.json'
    save(path, frame)
    with pytest.raises(ValueError, match='escapes'):
        module.join_capture(capture)
