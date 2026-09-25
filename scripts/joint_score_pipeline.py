"""Join a captured frame with explicit model completion records, before labeling.

This adapter consumes outputs from the pinned detector/OCR engines, not commands
or a target oracle. Missing/error results cannot be interpreted as nondetections.
"""
import json
from pathlib import Path
import numpy as np

from candidate_rendering_transform import correction
from bound_pose_observer import matrix
from integrate_object_depth_candidate import checked_child, decode_depth, sha
from joint_score_components import fingerprint, process_development_frame


def decode_rgb(raw, meta):
    channels = {'rgb8': 3, 'bgr8': 3, 'rgba8': 4, 'bgra8': 4}.get(meta['encoding'])
    if channels is None or meta['step'] < meta['width']*channels:
        raise ValueError('unsupported RGB encoding/stride')
    if len(raw) != meta['height']*meta['step'] or len(raw) != meta['bytes']:
        raise ValueError('RGB byte count')
    rgb = np.frombuffer(raw, np.uint8).reshape(meta['height'], meta['step'])
    rgb = rgb[:, :meta['width']*channels].reshape(meta['height'], meta['width'], channels)[:, :, :3]
    if meta['encoding'] in ('bgr8', 'bgra8'):
        rgb = rgb[:, :, ::-1]
    return rgb


def process_capture(directory, slot, detector, ocr, *, nominal_mount, rendered_mount, catalogue):
    if slot['wave'] != 'S' or slot['partition'] != 'development':
        raise PermissionError('Wave S development adapter only')
    root = Path(directory)
    summary = json.loads((root/'summary.json').read_text())
    if summary['attempt_id'] != slot['attempt_id'] or not summary['consumed']:
        raise ValueError('attempt identity mismatch')
    base = dict(attempt_id=slot['attempt_id'], wave='S', capture_uuid=summary['capture_uuid'], emissions=[])
    if summary['status'] == 'infrastructure_failure':
        return dict(base, status='infrastructure_failure', reason=summary['reason'])
    if summary['status'] != 'captured':
        raise ValueError('unclosed/unrecognized capture state')
    frame_path = root/'frame-000.json'
    frame_sha = sha(frame_path)
    frame = json.loads(frame_path.read_text())
    for name, result in [('detector', detector), ('ocr', ocr)]:
        if result is None or result.get('status') != 'completed' or result.get('frame_sha256') != frame_sha:
            return dict(base, status='infrastructure_failure', reason=name+'_completion_missing_or_mismatched')
        if not result.get('input_sha256') or result.get('audit_passed') is not True:
            raise ValueError(name+' raw output/source audit required')
        for path, digest in result['input_sha256'].items():
            if sha(path) != digest:
                raise ValueError(name+' source/raw bytes changed')
    stamp = frame['rgb_stamp_ns']
    if stamp != frame['depth_stamp_ns'] or frame['capture_uuid'] != summary['capture_uuid']:
        raise ValueError('exact capture binding')
    tf = frame['camera_to_map']
    s = tf['header']['stamp']
    if (s['sec']*10**9+s['nanosec'] != stamp or tf['header']['frame_id'] != 'map'
            or tf['child_frame_id'] != frame['rgb']['frame_id']):
        raise ValueError('exact map TF required')
    p, q = tf['transform']['translation'], tf['transform']['rotation']
    transform = correction(matrix([p[k] for k in ('x', 'y', 'z')], [q[k] for k in ('x', 'y', 'z', 'w')]),
                           nominal_mount, rendered_mount)
    for name in ('rgb', 'depth'):
        path = checked_child(root, frame[name]['file'])
        if sha(path) != frame[name]['sha256']:
            raise ValueError('capture bytes changed')
    rgb = decode_rgb(checked_child(root, frame['rgb']['file']).read_bytes(), frame['rgb'])
    depth = decode_depth(checked_child(root, frame['depth']['file']).read_bytes(), frame['depth'])
    info = frame['camera_info']
    calibration = {k: info[k] for k in ('k', 'd', 'r', 'p', 'distortion_model')}
    content = fingerprint(rgb, depth, calibration)
    result = process_development_frame(acquisition_class=slot['acquisition_class'], frame_id=frame_sha,
        rgb_stamp_ns=stamp, depth_stamp_ns=stamp, depth=depth, k=np.array(info['k']).reshape(3, 3),
        optical_to_map=transform, detector_boxes=detector['boxes'], ocr_texts=ocr['texts'],
        catalogue=catalogue, camera_xy=transform[:2, 3].tolist(),
        template='research3-readable-corridor-sign-v1', partition='development')
    return dict(base, status='completed', processing_status='completed', content_sha256=content,
                frame_sha256=frame_sha, emissions=result['emissions'],
                hypotheses=result['hypotheses'], perception_status=result['status'],
                human_labels_generated=False)


def ordered_ledger(schedule, attempt_results, *, protocol_sha256, schedule_sha256, execution_manifest_sha256):
    ids = [s['attempt_id'] for s in schedule['rows'] if s['wave'] == 'S']
    keyed = {r['attempt_id']: r for r in attempt_results}
    if len(ids) != 400 or len(keyed) != len(attempt_results) or set(keyed) != set(ids):
        raise ValueError('all 400 scheduled attempts must be accounted for exactly once')
    if any(r.get('wave') != 'S' or r.get('status') not in ('completed', 'infrastructure_failure') for r in keyed.values()):
        raise ValueError('Wave S closed attempts only')
    return dict(schema_version='research3-jsc-wave-evidence/v1', wave='S',
                protocol_sha256=protocol_sha256, schedule_sha256=schedule_sha256,
                execution_manifest_sha256=execution_manifest_sha256,
                attempts=[keyed[k] for k in ids], human_labels_generated=False)
