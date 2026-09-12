#!/usr/bin/env python3
"""Check existing executed paths against the declared doorway marker aperture.

This audit does not certify a marker as a physical architectural doorway.
"""
import json
import math
from pathlib import Path

from language_nav.evaluation.ordered import crossing_events

ROOT = Path(__file__).resolve().parents[1]


def main():
    rows = []
    for run in ('r3-inspection-dev00-v1', 'r3-variant-B1-v1', 'r3-variant-B2-v1',
                'r3-variant-B4-v1', 'r3-variant-B5-v1'):
        path = ROOT / 'reports/live_episodes' / run / 'measurements.json'
        evidence = json.loads(path.read_text())
        doorway = next(e for e in evidence['terminal_ground_truth'] if e['entity_id'].endswith('doorway-2'))
        pose = doorway['pose']
        # Provider doorway posts have centre +/-0.43, width0.12: clear aperture0.74m.
        dx, dy = -math.sin(pose['yaw']) * 0.37, math.cos(pose['yaw']) * 0.37
        gate = {'gate_id': doorway['entity_id'], 'a': [pose['x'] - dx, pose['y'] - dy],
                'b': [pose['x'] + dx, pose['y'] + dy], 'direction': 1}
        forward = crossing_events(evidence['ground_truth_positions'], [gate])
        reverse = crossing_events(evidence['ground_truth_positions'], [{**gate, 'direction': -1}])
        rows.append({'run_id': run, 'doorway_entity_id': doorway['entity_id'],
                     'crossed_marker_aperture_either_direction': bool(forward or reverse)})
    report = {'schema_version': 'research3-doorway-geometry-audit/v1', 'rows': rows,
              'physical_doorway_topology_certified': False,
              'campaign_blocker': 'Existing catalogue supplies side-of-route visual markers, not independently verified passage choices.',
              'required_resolution': 'Author and verify a physically faithful doorway/route benchmark, or explicitly change the claim to ordered marker navigation.'}
    output = ROOT / 'reports/doorway_geometry_audit_v1.json'
    with output.open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
