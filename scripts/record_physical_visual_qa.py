#!/usr/bin/env python3
"""Bind explicit, individual visual-QA decisions to immutable capture evidence.

This does not inspect images or decide correctness. The operator must inspect
each specified image and reported pixel before supplying these arguments.
"""
import argparse
import json
from pathlib import Path
from prepare_consolidated_review import task_digest
from join_physical_review_capture import join_capture


def attest(run, identifiers, note, attested_by):
    run=Path(run)
    joined=join_capture(run)
    tasks=[json.loads(line) for line in (run/'landmark_review_tasks.jsonl').read_text().splitlines() if line.strip()]
    identifiers=list(identifiers)
    if not identifiers or len(identifiers)!=len(set(identifiers)) or not note.strip() or not attested_by.strip():
        raise ValueError('explicit unique observation IDs, inspection note and operator required')
    selected=[]
    for task,row in zip(tasks,joined['observations'],strict=True):
        if task['observation_id'] not in identifiers:
            continue
        if row['reasons'] or row['status']!='awaiting_individual_visual_qa':
            raise ValueError('specified observation does not have a valid exact frame join')
        selected.append(dict(schema_version='research3-machine-visual-qa/v1',
            run_id=joined['run_id'], observation_id=task['observation_id'],
            task_sha256=task_digest(task), frame_sha256=row['frame_sha256'],
            request_sha256=joined['request_sha256'],provider_tasks_sha256=joined['provider_tasks_sha256'],
            attested_by=attested_by, inspection_note=note,
            full_frame_visible=True,context_sufficient=True,pixel_marker_verified=True,
            identity_decidable=True,correct=None,human_labels_generated=False))
    if len(selected)!=len(identifiers):
        raise ValueError('every explicitly selected ID must be present exactly once')
    return selected


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    selection=parser.add_mutually_exclusive_group(required=True)
    selection.add_argument('--observation-id',action='append')
    selection.add_argument('--entity-id',action='append')
    parser.add_argument('--frame',default='perception_capture/frame-000.json')
    parser.add_argument('--note',required=True)
    parser.add_argument('--attested-by',required=True)
    parser.add_argument('--each-image-and-pixel-inspected',action='store_true',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    identifiers=args.observation_id
    if args.entity_id:
        joined=join_capture(args.run)
        tasks=[json.loads(line) for line in (args.run/'landmark_review_tasks.jsonl').read_text().splitlines() if line.strip()]
        identifiers=[]
        for entity in args.entity_id:
            matches=[task['observation_id'] for task,row in zip(tasks,joined['observations'],strict=True)
                     if task.get('entity_id')==entity and row.get('frame')==args.frame]
            if len(matches)!=1:
                raise ValueError('each explicit entity must have exactly one observation in the inspected frame')
            identifiers.extend(matches)
    rows=attest(args.run,identifiers,args.note,args.attested_by)
    with args.output.open('x') as stream:
        for row in rows: stream.write(json.dumps(row,sort_keys=True)+'\n')


if __name__=='__main__': main()
