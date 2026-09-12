#!/usr/bin/env python3
"""Offline laser/SDF residuals at retained ground truth; never feeds navigation."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np


def world_boxes(path, height):
    boxes = []
    for model in ET.parse(path).findall('./world/model'):
        pose = list(map(float, model.findtext('pose').split()))
        if any(abs(v) > 1e-9 for v in pose[3:]):
            raise ValueError('audit requires axis-aligned generated world models')
        for visual in model.findall('./link/visual'):
            size = list(map(float, visual.findtext('./geometry/box/size').split()))
            if pose[2] - size[2]/2 <= height <= pose[2] + size[2]/2:
                boxes.append((pose[0]-size[0]/2, pose[0]+size[0]/2,
                              pose[1]-size[1]/2, pose[1]+size[1]/2))
    return boxes


def ranges_to_boxes(origin, angles, boxes, maximum):
    direction = np.array([np.cos(angles), np.sin(angles)])
    result = np.full(len(angles), maximum, dtype=float)
    for xmin, xmax, ymin, ymax in boxes:
        near, far = np.full(len(angles), -np.inf), np.full(len(angles), np.inf)
        for axis, (lo, hi) in enumerate(((xmin, xmax), (ymin, ymax))):
            d = direction[axis]
            parallel = abs(d) < 1e-12
            a = np.divide(lo-origin[axis], d, out=np.full(len(d), -np.inf), where=~parallel)
            b = np.divide(hi-origin[axis], d, out=np.full(len(d), np.inf), where=~parallel)
            near = np.maximum(near, np.minimum(a,b))
            far = np.minimum(far, np.maximum(a,b))
            if not lo <= origin[axis] <= hi:
                far[parallel] = -np.inf
        hit = (far >= np.maximum(near, 0)) & (far > 0)
        result = np.minimum(result, np.where(hit, np.maximum(near, 0), maximum))
    return result


def audit(directory):
    directory = Path(directory)
    request = json.loads((directory/'request.json').read_text())
    if request['partition'] not in {'development', 'validation'} or request['protected_test_routes_used'] is not False:
        raise ValueError('non-protected evidence required')
    world = Path(request['world_directory'])/'world.sdf'
    if hashlib.sha256(world.read_bytes()).hexdigest() != request['asset_sha256']['world.sdf']:
        raise ValueError('world hash mismatch')
    path = directory/'measurements.json'
    samples = json.loads(path.read_text())['scan_diagnostics']
    boxes = world_boxes(world, .16)
    rows = []
    for sample in samples:
        _, x, y, yaw = sample['ground_truth_pose']
        origin = (x - .064*math.cos(yaw), y - .064*math.sin(yaw))
        values = np.array([float('nan') if r is None else r for r in sample['ranges']])
        valid = np.isfinite(values) & (values > sample['range_min']) & (values < sample['range_max'])
        if not valid.any():
            continue
        angles = yaw + sample['angle_min'] + np.arange(len(values))*sample['angle_increment']
        expected = ranges_to_boxes(origin, angles, boxes, sample['range_max'])
        errors = abs(expected[valid] - values[valid])
        rows.append(dict(stamp_s=sample['stamp_s'], rays=int(valid.sum()),
            mean_abs_error_m=float(errors.mean()), median_abs_error_m=float(np.median(errors)),
            p95_abs_error_m=float(np.quantile(errors,.95)), fraction_within_10cm=float((errors <= .1).mean())))
    return dict(schema_version='research3-laser-geometry-diagnostic/v1', run_id=request['run_id'],
        measurements_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), world_sha256=request['asset_sha256']['world.sdf'],
        rows=rows, assumptions=['SDF visual boxes, horizontal laser plane z=0.16 m',
        'Ground-truth robot yaw; planar sensor offset [-0.064,0] from provider xacro',
        'No robot self-occlusion, roll/pitch or motion distortion modeled; residuals are diagnostic not a calibration'],
        runtime_modified=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args=parser.parse_args()
    result=audit(args.run)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
