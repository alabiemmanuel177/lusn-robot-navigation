#!/usr/bin/env python3
"""Validate exact detector/media joins; output is for visual QA, never human labels."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re


def read_json(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_file(directory, name):
    path = (directory / name).resolve()
    if not path.is_relative_to(directory.resolve()):
        raise ValueError('capture path escapes directory')
    return path


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def join_capture(directory):
    directory = Path(directory).resolve()
    request_path = directory / 'request.json'
    request = read_json(request_path)
    match = re.fullmatch(r'r3geo_base_r(\d{3})', request.get('map_id', ''))
    index = int(match[1]) if match else 0
    expected = 'development' if 1 <= index <= 10 else 'validation' if 11 <= index <= 14 else None
    if (expected is None or request.get('partition') != expected
            or request.get('protected_test_routes_used') is not False):
        raise ValueError('non-protected map identity required before reading capture')
    media = directory / 'perception_capture'
    summary_path = media / 'summary.json'
    summary = read_json(summary_path)
    frame_paths = [local_file(media, name) for name in summary['frames']]
    frames = [(path, read_json(path)) for path in frame_paths]
    index_ref=summary.get('observation_index')
    indexed={}
    index_errors=[]
    if index_ref:
        index_path=local_file(media,index_ref['file'])
        if digest(index_path) != index_ref['sha256']:
            raise ValueError('observation index checksum mismatch')
        index=read_json(index_path)
        if index.get('schema_version') != 'research3-captured-frame-observations/v1':
            raise ValueError('invalid observation index schema')
        if index.get('observation_overflow',0) or index.get('observation_conflicts',0):
            index_errors.append('observation_index_overflow_or_conflict')
        for entry in index['frames']:
            path=local_file(media,entry['frame'])
            if path in indexed or digest(path) != entry['frame_sha256']:
                raise ValueError('duplicate or stale indexed frame')
            indexed[path]=entry
    tasks_path = directory / 'landmark_review_tasks.jsonl'
    tasks = [json.loads(line) for line in tasks_path.read_text().splitlines() if line.strip()]
    counts = Counter(task.get('observation_id') for task in tasks)
    rows = []
    for task in tasks:
        reasons = []
        identifier = task.get('observation_id')
        if not identifier or counts[identifier] != 1:
            reasons.append('missing_or_duplicate_observation_id')
        if (task.get('schema_version') != 'landmark-review-task/v1'
                or task.get('partition') != expected
                or task.get('review_status') != 'pending_human_review'
                or task.get('correct') is not None or task.get('reviewer_id') != ''):
            reasons.append('invalid_pending_provider_task')
        stamp = task.get('observed_at_ns')
        exact = [(path, frame) for path, frame in frames
                 if type(stamp) is int and stamp > 0 and frame.get('rgb_stamp_ns') == stamp]
        row = {'observation_id': identifier, 'reasons': reasons}
        if len(exact) != 1:
            reasons.append('missing_or_ambiguous_exact_frame')
        else:
            path, frame = exact[0]
            observations=frame.get('trigger_observations', [])
            if index_ref:
                entry=indexed.get(path)
                if entry is None or entry['rgb_stamp_ns'] != stamp:
                    reasons.append('observation_index_frame_missing_or_mismatched')
                    observations=[]
                else:
                    observations=entry['observations']
                    if entry.get('conflicting_observation_ids'):
                        reasons.append('observation_index_frame_conflict')
                reasons.extend(index_errors)
            triggers = [item for item in observations
                        if item.get('observation_id') == identifier]
            if len(triggers) != 1:
                reasons.append('missing_or_ambiguous_trigger_identity')
            elif any(triggers[0].get(key) != task.get(key) for key in
                     ('entity_id', 'region_id', 'category', 'observed_at_ns', 'source')) or (
                         triggers[0].get('confidence') != task.get('probability')):
                reasons.append('provider_trigger_mismatch')
            for kind in ('rgb', 'depth'):
                info = frame[kind]
                raw_path = local_file(media, info['file'])
                raw = raw_path.read_bytes()
                if hashlib.sha256(raw).hexdigest() != info['sha256'] or len(raw) != info['bytes']:
                    reasons.append(kind + '_integrity_mismatch')
                channels = {'rgb8': 3, 'bgr8': 3, '32FC1': 4, '16UC1': 2}
                stride = channels.get(info['encoding'])
                if (stride is None or any(type(info.get(k)) is not int or info[k] <= 0
                                          for k in ('width', 'height', 'step'))
                        or info['step'] < info['width'] * (stride or 0)
                        or len(raw) != info['height'] * info['step']):
                    reasons.append(kind + '_invalid_layout')
            pixel = task.get('pixel', {})
            if not all(finite(pixel.get(k)) and 0 <= pixel[k] < frame['rgb'][dimension]
                       for k, dimension in (('u', 'width'), ('v', 'height'))):
                reasons.append('invalid_detector_pixel')
            if not finite(task.get('depth_m')) or task['depth_m'] <= 0:
                reasons.append('invalid_detector_depth')
            if not finite(task.get('probability')) or not 0 <= task['probability'] <= 1:
                reasons.append('invalid_probability')
            if (type(frame.get('depth_stamp_ns')) is not int
                    or abs(frame['depth_stamp_ns'] - stamp) > 3_000_000):
                reasons.append('unsynchronized_depth')
            if not frame.get('camera_info') or not frame.get('camera_to_map') or frame.get('transform_error'):
                reasons.append('camera_geometry_unavailable')
            row.update(frame=str(path.relative_to(directory)), frame_sha256=digest(path),
                       pixel=task.get('pixel'), category=task.get('category'))
        row['status'] = 'rejected' if reasons else 'awaiting_individual_visual_qa'
        rows.append(row)
    return {'schema_version': 'research3-exact-review-join/v1',
            'run_id': request['run_id'], 'map_id': request['map_id'],
            'request_sha256': digest(request_path), 'provider_tasks_sha256': digest(tasks_path),
            'capture_summary_sha256': digest(summary_path),
            'status': 'not_authorized_for_human_review', 'human_labels_generated': False,
            'protected_data_used': False, 'calibration_validated': False,
            'joined_for_visual_qa': sum(row['status'] != 'rejected' for row in rows),
            'rejected': sum(row['status'] == 'rejected' for row in rows), 'observations': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = join_capture(args.run)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
