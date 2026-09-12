#!/usr/bin/env python3
"""Audit retained physical-world diagnostics; never generate a human review queue.

Decision candidates are not raw detector records. Even an exact timestamp match
does not establish the detected pixel region, so this tool deliberately reports
not_reviewable until a separate, validated detector-linked exporter exists.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def local_file(directory, relative):
    path = (directory / relative).resolve()
    if not path.is_relative_to(directory.resolve()):
        raise ValueError('media path escapes capture directory')
    return path


def audit_run(directory):
    directory = Path(directory)
    request_path = directory / 'request.json'
    request = read_json(request_path)
    if (request.get('partition') not in {'development', 'validation'}
            or request.get('protected_test_routes_used') is not False):
        raise ValueError('protected or unproven non-protected capture rejected')
    if not request.get('map_id') or not request.get('asset_sha256', {}).get('map.pgm'):
        raise ValueError('map identity and map checksum required')
    capture_path = directory / 'capture.json'
    capture = read_json(capture_path)
    if capture.get('run_id') != request.get('run_id'):
        raise ValueError('run identity mismatch')
    frames = []
    media_directory = directory / 'perception_capture'
    for path in sorted(media_directory.glob('frame-*.json')):
        frame = read_json(path)
        errors = []
        for kind in ('rgb', 'depth'):
            metadata = frame.get(kind, {})
            media = local_file(media_directory, metadata.get('file', 'missing'))
            if not media.is_file():
                errors.append(f'{kind}_missing')
            elif sha256(media) != metadata.get('sha256'):
                errors.append(f'{kind}_checksum_mismatch')
            elif media.stat().st_size != metadata.get('bytes'):
                errors.append(f'{kind}_size_mismatch')
        if not frame.get('camera_to_map') or frame.get('transform_error'):
            errors.append('map_transform_unavailable')
        if not frame.get('camera_info'):
            errors.append('camera_info_missing')
        frames.append({'file': str(path), 'sha256': sha256(path),
                       'rgb_stamp_ns': frame.get('rgb_stamp_ns'),
                       'depth_stamp_ns': frame.get('depth_stamp_ns'),
                       'diagnostic_errors': errors})
    observations = {}
    for decision in capture.get('decisions', []):
        for candidate in json.loads(decision.get('candidates_json', '[]')):
            for role in ('anchor', 'terminal'):
                identifier = candidate.get(f'{role}_observation_id')
                if not identifier:
                    continue
                record = {
                    'observation_id': identifier,
                    'role': role,
                    'claimed_category': candidate.get(f'{role}_category'),
                    'observed_at_ns': candidate.get(f'{role}_observed_at_ns'),
                    'source': candidate.get(f'{role}_observation_source'),
                    'sequence': candidate.get(f'{role}_observation_sequence'),
                }
                key = (role, identifier)
                if key in observations and observations[key] != record:
                    raise ValueError(f'inconsistent repeated observation: {identifier}')
                observations[key] = record
    records = []
    for record in observations.values():
        exact = [frame for frame in frames
                 if frame['rgb_stamp_ns'] == record['observed_at_ns']]
        reasons = ['raw_detector_record_and_pixel_localization_not_retained']
        if not exact:
            reasons.append('exact_source_rgb_frame_not_retained')
        elif len(exact) != 1:
            reasons.append('ambiguous_source_rgb_frame')
        else:
            reasons.extend(exact[0]['diagnostic_errors'])
        records.append({**record, 'status': 'not_reviewable', 'reasons': reasons,
                        'exact_frame_matches': [frame['file'] for frame in exact]})
    counts = Counter(record['claimed_category'] or 'unknown' for record in records)
    return {
        'run_id': request['run_id'], 'partition': request['partition'],
        'map_id': request['map_id'], 'map_sha256': request['asset_sha256']['map.pgm'],
        'runtime_scene_sha256': request.get('runtime_scene_sha256'),
        'camera_profile_sha256': request.get('camera_profile_sha256'),
        'request_sha256': sha256(request_path), 'capture_sha256': sha256(capture_path),
        'status': 'not_reviewable', 'frames': frames, 'observations': records,
        'unique_observation_ids': len({row['observation_id'] for row in records}),
        'claimed_category_counts': dict(sorted(counts.items())),
        'reviewable_observations': 0,
        'classwise_accuracy': None, 'false_negative_coverage': None,
        'natural_incorrect_coverage': None, 'natural_correct_coverage': None,
        'reason': 'diagnostic candidate snapshots cannot support detector accuracy review',
    }


def build_manifest(directories):
    runs = [audit_run(path) for path in directories]
    if not runs or len({run['run_id'] for run in runs}) != len(runs):
        raise ValueError('provide at least one run, without duplicate run IDs')
    return {'schema_version': 'research3-physical-detector-review-preparation/v1',
            'status': 'not_reviewable', 'human_labels_generated': False,
            'protected_data_used': False, 'calibration_frozen': False,
            'old_calibration_transfer_validated': False,
            'detector_performance_validated': False, 'review_queue_created': False,
            'runs': runs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = build_manifest(args.run)
    with args.output.open('x') as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'status': manifest['status'], 'runs': len(manifest['runs']),
                      'output': str(args.output)}))


if __name__ == '__main__':
    main()
