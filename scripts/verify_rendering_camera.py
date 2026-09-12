#!/usr/bin/env python3
"""Verify the rendering camera model against every control render's depth image.

For each successful control render (unmodified source world at a bound view
pose) this back-projects floor and wall depth samples and compares the implied
camera height and horizontal position with the model. Residuals are reported per
render; the model is considered verified when every render agrees within 3 cm.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from expansion_rendered_checks import decode_frame  # noqa: E402
from expansion_camera_model import verify_against_depth, MODEL_ID, CAMERA_OFFSET_BASE  # noqa: E402


def verify_run(run_dir):
    run_dir = Path(run_dir)
    request = json.loads((run_dir / 'request.json').read_bytes())
    frame = run_dir / 'perception_capture/frame-000.json'
    if not frame.exists():
        frame = run_dir / 'context_capture/frame-000.json'
    image, info = decode_frame(frame)
    depth_info = info['depth']
    depth = np.frombuffer((frame.parent / depth_info['file']).read_bytes(), dtype=np.float32)
    depth = depth.reshape(depth_info['height'], depth_info['width'])
    world = Path(request['world_directory'])
    walls = json.loads((world / 'manifest.json').read_bytes())['layout']['walls']
    result = verify_against_depth(request['capture_pose'], depth, info['camera_info'], image, walls)
    tf = (info.get('camera_to_map') or {}).get('transform')
    if tf:
        result['localization_transform_translation'] = tf['translation']
        result['localization_transform_offset_from_model_m'] = [tf['translation'][k] - c for k, c in zip('xyz', result['model_centre'])]
    return dict(run_id=request['run_id'], map_id=request['map_id'], frame=str(frame.relative_to(ROOT)), **result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--renders', type=Path, required=True, help='render ledger directory')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    rows = []
    for line in (args.renders / 'renders.jsonl').read_text().splitlines():
        record = json.loads(line)
        if record['kind'] == 'control' and record['exit_code'] == 0:
            rows.append(verify_run(record['run_directory']))
    residuals = [r['max_abs_residual_m'] for r in rows if r['max_abs_residual_m'] is not None]
    payload = dict(schema_version='research3-rendering-camera-verification/v1', model_id=MODEL_ID,
                   camera_offset_base_frame_m=list(CAMERA_OFFSET_BASE), renders=len(rows),
                   verified_renders=sum(r['verified'] for r in rows), max_abs_residual_m=max(residuals) if residuals else None,
                   all_verified=bool(rows) and all(r['verified'] for r in rows), rows=rows,
                   scope='depth-derived camera position per control render; evidence for the placement model, not a detector claim')
    with args.output.open('x') as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
    print(json.dumps({k: payload[k] for k in ('renders', 'verified_renders', 'max_abs_residual_m', 'all_verified')}))


if __name__ == '__main__':
    main()
