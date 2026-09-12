import importlib.util
import json
from pathlib import Path

import pytest


SPEC = importlib.util.spec_from_file_location(
    'prepare_physical_detector_review',
    Path(__file__).parents[1] / 'scripts/prepare_physical_detector_review.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def fixture(tmp_path, partition='development'):
    request = {'run_id': 'pilot', 'partition': partition,
               'protected_test_routes_used': False, 'map_id': 'r3geo_dev',
               'asset_sha256': {'map.pgm': 'abc'}}
    candidate = {'anchor_observation_id': 'obs1', 'anchor_category': 'chair',
                 'anchor_observed_at_ns': 100, 'anchor_observation_sequence': 1,
                 'anchor_observation_source': 'camera'}
    capture = {'run_id': 'pilot', 'decisions': [
        {'candidates_json': json.dumps([candidate, candidate])}]}
    (tmp_path / 'request.json').write_text(json.dumps(request))
    (tmp_path / 'capture.json').write_text(json.dumps(capture))
    return candidate, capture


def test_deduplicates_routes_and_refuses_unlinked_review(tmp_path):
    fixture(tmp_path)
    report = MODULE.build_manifest([tmp_path])
    run = report['runs'][0]
    assert run['unique_observation_ids'] == 1
    assert run['claimed_category_counts'] == {'chair': 1}
    assert run['reviewable_observations'] == 0
    assert 'exact_source_rgb_frame_not_retained' in run['observations'][0]['reasons']
    assert run['natural_incorrect_coverage'] is None
    assert report['calibration_frozen'] is False
    assert report['review_queue_created'] is False


@pytest.mark.parametrize('partition', ['test', 'held_out', '', None])
def test_rejects_protected_or_unknown_partition(tmp_path, partition):
    fixture(tmp_path, partition)
    with pytest.raises(ValueError, match='protected'):
        MODULE.audit_run(tmp_path)


def test_exact_frame_does_not_invent_pixel_localization(tmp_path):
    fixture(tmp_path)
    media = tmp_path / 'perception_capture'
    media.mkdir()
    frame = {'rgb_stamp_ns': 100, 'depth_stamp_ns': 100, 'camera_info': {},
             'camera_to_map': None, 'transform_error': 'missing'}
    for kind in ('rgb', 'depth'):
        path = media / f'{kind}.bin'
        path.write_bytes(b'123')
        frame[kind] = {'file': path.name, 'sha256': MODULE.sha256(path), 'bytes': 3}
    (media / 'frame-000.json').write_text(json.dumps(frame))
    row = MODULE.audit_run(tmp_path)['observations'][0]
    assert row['status'] == 'not_reviewable'
    assert len(row['exact_frame_matches']) == 1
    assert 'map_transform_unavailable' in row['reasons']
    assert 'raw_detector_record_and_pixel_localization_not_retained' in row['reasons']
    assert 'exact_source_rgb_frame_not_retained' not in row['reasons']


def test_rejects_inconsistent_duplicate_and_duplicate_runs(tmp_path):
    candidate, capture = fixture(tmp_path)
    with pytest.raises(ValueError, match='duplicate run'):
        MODULE.build_manifest([tmp_path, tmp_path])
    changed = {**candidate, 'anchor_observed_at_ns': 999}
    capture['decisions'].append({'candidates_json': json.dumps([changed])})
    (tmp_path / 'capture.json').write_text(json.dumps(capture))
    with pytest.raises(ValueError, match='inconsistent'):
        MODULE.audit_run(tmp_path)


def test_media_path_cannot_escape(tmp_path):
    with pytest.raises(ValueError, match='escapes'):
        MODULE.local_file(tmp_path, '../outside.bin')
