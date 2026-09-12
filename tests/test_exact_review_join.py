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


def test_relative_run_path_matches_absolute(capture, monkeypatch):
    monkeypatch.chdir(capture.parent)
    assert module.join_capture(Path(capture.name)) == module.join_capture(capture)


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


def write_observation_index(capture, mutate=None):
    media = capture / 'perception_capture'
    frame = json.loads((media / 'frame-000.json').read_text())
    entry = dict(frame='frame-000.json', frame_sha256=module.digest(media / 'frame-000.json'),
                 rgb_stamp_ns=frame['rgb_stamp_ns'], observations=frame['trigger_observations'],
                 conflicting_observation_ids=[])
    index = dict(schema_version='research3-captured-frame-observations/v1', frames=[entry],
                 observation_overflow=0, observation_conflicts=0)
    if mutate:
        mutate(index)
    save(media / 'observation_index.json', index)
    save(media / 'summary.json', dict(frames=['frame-000.json'], observation_index=dict(
        file='observation_index.json', sha256=module.digest(media / 'observation_index.json'))))
    return index


def test_second_observation_from_same_frame_joins_via_sidecar(capture):
    task_path = capture / 'landmark_review_tasks.jsonl'
    task = json.loads(task_path.read_text())
    second = {**task, 'observation_id': 'obs2', 'entity_id': 'chair2', 'region_id': 'region2'}
    task_path.write_text(json.dumps(task) + '\n' + json.dumps(second) + '\n')

    def add_second(index):
        index['frames'][0]['observations'].append({
            **index['frames'][0]['observations'][0], 'observation_id': 'obs2',
            'entity_id': 'chair2', 'region_id': 'region2'})

    write_observation_index(capture, add_second)
    # Immutable initial frame metadata still only carries the first trigger.
    original = json.loads((capture / 'perception_capture/frame-000.json').read_text())
    assert len(original['trigger_observations']) == 1
    result = module.join_capture(capture)
    assert result['joined_for_visual_qa'] == 2 and result['rejected'] == 0
    assert result['status'] == 'not_authorized_for_human_review'
    assert result['human_labels_generated'] is False


def test_observation_index_sha_tampering_fails_closed(capture):
    write_observation_index(capture)
    (capture / 'perception_capture/observation_index.json').write_text('{}')
    with pytest.raises(ValueError, match='index checksum mismatch'):
        module.join_capture(capture)


def test_indexed_frame_metadata_sha_mismatch_fails_closed(capture):
    write_observation_index(capture, lambda index: index['frames'][0].update(frame_sha256='0' * 64))
    with pytest.raises(ValueError, match='stale indexed frame'):
        module.join_capture(capture)


@pytest.mark.parametrize('mutation', [
    lambda index: index['frames'][0].update(rgb_stamp_ns=1000000001),
    lambda index: index.update(frames=[]),
])
def test_indexed_frame_timestamp_or_missing_membership_does_not_fallback(capture, mutation):
    write_observation_index(capture, mutation)
    result = module.join_capture(capture)
    assert result['joined_for_visual_qa'] == 0
    assert 'observation_index_frame_missing_or_mismatched' in result['observations'][0]['reasons']
    assert 'missing_or_ambiguous_trigger_identity' in result['observations'][0]['reasons']


@pytest.mark.parametrize('field', ['observation_overflow', 'observation_conflicts'])
def test_global_index_overflow_or_conflict_rejects_otherwise_valid_join(capture, field):
    write_observation_index(capture, lambda index: index.update({field: 1}))
    result = module.join_capture(capture)
    assert result['rejected'] == 1 and result['joined_for_visual_qa'] == 0
    assert 'observation_index_overflow_or_conflict' in result['observations'][0]['reasons']


def test_frame_conflict_rejects_join_even_without_global_counter(capture):
    write_observation_index(capture, lambda index: index['frames'][0].update(conflicting_observation_ids=['obs1']))
    result = module.join_capture(capture)
    assert result['rejected'] == 1
    assert 'observation_index_frame_conflict' in result['observations'][0]['reasons']


def test_duplicate_indexed_frame_rejected(capture):
    write_observation_index(capture, lambda index: index['frames'].append(dict(index['frames'][0])))
    with pytest.raises(ValueError, match='duplicate'):
        module.join_capture(capture)


def test_old_capture_without_index_uses_only_original_trigger(capture):
    task_path = capture / 'landmark_review_tasks.jsonl'
    task = json.loads(task_path.read_text())
    second = {**task, 'observation_id': 'obs2'}
    task_path.write_text(json.dumps(task) + '\n' + json.dumps(second) + '\n')
    result = module.join_capture(capture)
    assert result['joined_for_visual_qa'] == 1 and result['rejected'] == 1
    assert 'missing_or_ambiguous_trigger_identity' in result['observations'][1]['reasons']
