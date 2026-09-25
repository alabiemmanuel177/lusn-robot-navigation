"""Fixed development replay; predicted surfaces and geometric candidates, not truth."""
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
import yaml

from candidate_depth_support import estimate
from candidate_instance_association import associate
from expansion_camera_model import rendering_camera

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'reports/object_localization_candidate_20260923_v1'
OUTPUT = ROOT / 'reports/object_depth_integration_20260923_v1'
CLASSES = ('chair', 'doorway', 'laboratory_entrance', 'office_entrance')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def decode_depth(raw, meta):
    if meta['encoding'] != '32FC1' or meta['is_bigendian'] not in (0, 1):
        raise ValueError('unsupported depth encoding')
    h, w, step = meta['height'], meta['width'], meta['step']
    if h <= 0 or w <= 0 or step < w * 4 or step % 4:
        raise ValueError('invalid depth dimensions/stride')
    if len(raw) != h * step or len(raw) != meta['bytes']:
        raise ValueError('depth byte length')
    if hashlib.sha256(raw).hexdigest() != meta['sha256']:
        raise ValueError('depth checksum')
    return np.frombuffer(raw, dtype='>f4' if meta['is_bigendian'] else '<f4').reshape(h, step // 4)[:, :w]


def integrate_box(box, depth, k, transform, catalogue):
    result = dict(prediction=box, human_verdict=None, entity_id=None,
                  joint_correctness_probability=None, calibration_eligible=False,
                  runtime_admitted=False, association=None)
    if box['query'] not in CLASSES:
        return dict(result, status='non_navigation_visual_hypothesis', depth=None)
    surface = estimate(depth, box['xyxy'], k, transform)
    result['depth'] = surface
    if surface['map_pose'] is None:
        return dict(result, status=surface['status'])
    if surface['multiple_surfaces_possible']:
        return dict(result, status='unresolved_multiple_surfaces')
    # object_localized is an interface flag for a predicted box with depth,
    # never evidence of verified object identity or reference-point correctness.
    result['association'] = associate(dict(object_localized=True,
        map_pose=surface['map_pose'], visual_category=box['query'], entity_id=None), catalogue)
    return dict(result, status=result['association']['status'])


def checked_child(parent, name):
    path = (parent / name).resolve()
    if path.parent != parent.resolve():
        raise ValueError('capture child path escapes directory')
    return path


def main():
    plan = json.loads((SOURCE / 'plan.json').read_bytes())
    rows = [json.loads(line) for line in (SOURCE / 'results.jsonl').read_text().splitlines()]
    report = json.loads((SOURCE / 'report.json').read_bytes())
    if report['plan_sha256'] != sha(SOURCE / 'plan.json') or report['journal_sha256'] != sha(SOURCE / 'results.jsonl'):
        raise ValueError('upstream binding changed')
    if len(rows) != 24 or len(plan['slots']) != 24:
        raise ValueError('fixed 24-slot panel required')
    pins = {}
    def pin(path, expected=None):
        digest = sha(path)
        if expected is not None and digest != expected:
            raise ValueError(f'input changed: {path}')
        pins[str(Path(path).resolve())] = digest
    for name in ('plan.json', 'results.jsonl', 'report.json', 'audit.json'):
        pin(SOURCE / name)
    for name in ('integrate_object_depth_candidate.py', 'candidate_depth_support.py',
                 'candidate_instance_association.py', 'expansion_camera_model.py'):
        pin(ROOT / 'scripts' / name)
    pin(ROOT / 'docs/OBJECT_DEPTH_INTEGRATION_20260923.md')
    prepared = []
    for slot, row in zip(plan['slots'], rows, strict=True):
        if slot['source_index'] != row['source_index']:
            raise ValueError('source order changed')
        if slot['status'] != 'ready':
            if row != dict(slot, boxes=[], human_verdict=None):
                raise ValueError('historical failure changed')
            prepared.append((slot, row, None))
            continue
        # Allow only the original development feasibility capture namespace.
        frame = (ROOT / slot['frame']).resolve()
        base = ROOT / 'reports/physical_live_episodes'
        if frame.parent.parent.parent != base or not frame.parent.parent.name.startswith('r3-redesign-v2-design_feasibility-'):
            raise ValueError('outside development replay scope')
        request_path = frame.parent.parent / 'request.json'
        pin(request_path, plan['input_sha256'][str(request_path)])
        request = json.loads(request_path.read_bytes())
        if request['partition'] != 'development' or request['protected_test_routes_used'] or not request['capture_only']:
            raise ValueError('development stationary scope required')
        pin(frame, plan['input_sha256'][str(frame)])
        meta = json.loads(frame.read_bytes())
        for channel in ('rgb', 'depth'):
            pin(checked_child(frame.parent, meta[channel]['file']), meta[channel]['sha256'])
        if meta['rgb_stamp_ns'] != meta['depth_stamp_ns'] or meta['sync_difference_ns'] != 0:
            raise ValueError('exact synchronized pair required')
        kmeta = meta['camera_info']
        if any((meta[c]['width'], meta[c]['height']) != (kmeta['width'], kmeta['height']) for c in ('rgb', 'depth')):
            raise ValueError('unaligned image sizes')
        if any(kmeta['d']) or kmeta['binning_x'] or kmeta['binning_y'] or any(kmeta['roi'][x] for x in ('height','width','x_offset','y_offset')):
            raise ValueError('unsupported distorted/binned/cropped camera')
        scene_path = checked_child(frame.parent.parent, 'runtime_scene.yaml')
        if Path(request['runtime_scene']).resolve() != scene_path:
            raise ValueError('scene path mismatch')
        pin(scene_path, request['runtime_scene_sha256'])
        scene = yaml.safe_load(scene_path.read_bytes())
        if scene['partition'] != 'development' or scene['map_id'] != request['map_id']:
            raise ValueError('catalogue partition/map mismatch')
        catalogue = [dict(entity_id=e['entity_id'], category=e['category'], x=e['pose']['x'], y=e['pose']['y']) for e in scene['entities']]
        prepared.append((slot, row, (frame, meta, request, catalogue)))
    OUTPUT.mkdir(exist_ok=False)
    write(OUTPUT / 'plan.json', dict(schema_version='research3-object-depth-replay-plan/v1',
        input_sha256=pins, slots=plan['slots'], association_radius_m=.9,
        multiple_surface_policy='retain_surface_but_abstain_from_association',
        transform_provenance='commanded_stationary_pose_plus_rendering_camera_model_not_measured_tf',
        runtime_admitted=False, calibration_eligible=False))
    outputs = []
    for slot, row, inputs in prepared:
        if inputs is None:
            outputs.append(dict(source_index=slot['source_index'], status='retained_source_failure', boxes=[]))
            continue
        frame, meta, request, catalogue = inputs
        depth = decode_depth(checked_child(frame.parent, meta['depth']['file']).read_bytes(), meta['depth'])
        centre, rotation = rendering_camera(request['capture_pose'])
        transform = np.eye(4); transform[:3, :3] = rotation; transform[:3, 3] = centre
        boxes = [integrate_box(b, depth, np.asarray(meta['camera_info']['k']).reshape(3, 3), transform, catalogue) for b in row['boxes']]
        outputs.append(dict(source_index=slot['source_index'], status='completed',
            optical_to_map_assumed=transform.tolist(), boxes=boxes))
    # Verify no input changed while replay was running.
    for path, expected in pins.items():
        if sha(path) != expected:
            raise ValueError(f'input changed during replay: {path}')
    write(OUTPUT / 'results.json', outputs)
    counts = Counter(b['status'] for row in outputs for b in row['boxes'])
    result = dict(plan_sha256=sha(OUTPUT / 'plan.json'), results_sha256=sha(OUTPUT / 'results.json'),
        scheduled_slots=len(outputs), completed_frames=sum(r['status']=='completed' for r in outputs),
        retained_source_failures=1, boxes_retained=sum(counts.values()), status_counts=counts,
        human_labels_generated=False, calibration_eligible=False, runtime_admitted=False,
        measured_transform_validated=False, validation_or_protected_data_used=False)
    write(OUTPUT / 'report.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
