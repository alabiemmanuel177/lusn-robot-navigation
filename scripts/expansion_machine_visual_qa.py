#!/usr/bin/env python3
"""Automated per-observation image checks for expansion captures; never a verdict.

For every pending provider task in a run this decodes the exact joined frame,
verifies the image is a complete non-degenerate render, that the reported pixel
lies inside the frame, and that a palette-coloured blob of the task's category
surrounds that pixel. Observations passing every check receive a machine
visual-QA attestation (schema research3-machine-visual-qa/v1) through the
existing binding helper, with the checks named in the note. Failures are listed
with reasons and receive no attestation. `correct` is always null.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from expansion_rendered_checks import decode_frame, colour_mask, palette_key  # noqa: E402
from record_physical_visual_qa import attest  # noqa: E402
from join_physical_review_capture import join_capture  # noqa: E402

ATTESTED_BY = 'Claude Fable 5.1 automated pixel checks (expansion_machine_visual_qa v1)'
NOTE = ('machine checks: frame decoded with verified checksum; image non-degenerate (channel std > 8, '
        'no >60% saturated rows); reported pixel inside frame; category palette blob (tolerance 12) '
        'contains the pixel within a 7px window with >= 25 blob pixels within 25px; correctness not judged')
WINDOW, NEIGHBOURHOOD, MIN_BLOB = 7, 25, 25


def palette_rgb(run, task):
    profile_sha = json.loads((run / 'request.json').read_bytes()).get('camera_profile_sha256')
    scene = yaml.safe_load((run / 'runtime_scene.yaml').read_text())
    entity = next((e for e in scene['entities'] if e['entity_id'] == task['entity_id']), None)
    if entity is None:
        return None, 'entity_not_in_runtime_scene'
    return entity['marker_rgb'], None


def check_run(run):
    run = Path(run)
    joined = join_capture(run)
    tasks = [json.loads(line) for line in (run / 'landmark_review_tasks.jsonl').read_text().splitlines() if line.strip()]
    results, passing = [], []
    frames = {}
    for task, row in zip(tasks, joined['observations'], strict=True):
        reasons = list(row['reasons'])
        if row['status'] != 'awaiting_individual_visual_qa':
            reasons.append('join_status_' + row['status'])
        if not reasons:
            frame_path = run / row['frame']
            if frame_path not in frames:
                frames[frame_path] = decode_frame(frame_path)[0]
            image = frames[frame_path]
            height, width = image.shape[:2]
            if image.std() <= 8 or np.mean(np.all(image >= 250, axis=2).mean(1) > .6) > 0:
                reasons.append('degenerate_image')
            u, v = task['pixel']['u'], task['pixel']['v']
            if not (0 <= u < width and 0 <= v < height):
                reasons.append('pixel_outside_frame')
            else:
                rgb, problem = palette_rgb(run, task)
                if problem:
                    reasons.append(problem)
                else:
                    mask = colour_mask(image, rgb)
                    ui, vi = int(round(u)), int(round(v))
                    window = mask[max(0, vi - WINDOW):vi + WINDOW + 1, max(0, ui - WINDOW):ui + WINDOW + 1]
                    neighbourhood = mask[max(0, vi - NEIGHBOURHOOD):vi + NEIGHBOURHOOD + 1,
                                         max(0, ui - NEIGHBOURHOOD):ui + NEIGHBOURHOOD + 1]
                    if not window.any():
                        reasons.append('pixel_not_on_category_palette_blob')
                    if int(neighbourhood.sum()) < MIN_BLOB:
                        reasons.append('category_blob_too_small')
        results.append(dict(run_id=joined['run_id'], observation_id=task['observation_id'], entity_id=task['entity_id'],
                            category=task['category'], passed=not reasons, reasons=reasons))
        if not reasons:
            passing.append(task['observation_id'])
    rows = attest(run, passing, NOTE, ATTESTED_BY) if passing else []
    return results, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True, help='create-once QA JSONL')
    parser.add_argument('--report', type=Path, required=True, help='create-once per-observation check report')
    args = parser.parse_args()
    all_results, all_rows = [], []
    for run in args.run:
        results, rows = check_run(run)
        all_results.extend(results)
        all_rows.extend(rows)
    with args.output.open('x') as stream:
        for row in all_rows:
            stream.write(json.dumps(row, sort_keys=True) + '\n')
    with args.report.open('x') as stream:
        json.dump(dict(schema_version='research3-expansion-machine-visual-qa-report/v1', attested_by=ATTESTED_BY,
                       checks=NOTE, observations=len(all_results), passed=sum(r['passed'] for r in all_results),
                       failed=[r for r in all_results if not r['passed']], human_labels_generated=False,
                       correctness_judged=False, rows=all_results), stream, indent=2, sort_keys=True)
    print(json.dumps(dict(observations=len(all_results), passed=sum(r['passed'] for r in all_results),
                          failed=sum(not r['passed'] for r in all_results))))


if __name__ == '__main__':
    main()
