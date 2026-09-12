#!/usr/bin/env python3
"""Create-once exhaustive non-protected condition preflight, never launches ROS."""
import argparse
import json
from pathlib import Path

from language_nav.benchmark import CorruptionCondition
from run_physical_episode import prepare, physical_simulation_command

ROOT = Path(__file__).resolve().parents[1]


def check():
    rows = []
    for index in range(1, 15):
        base = f'base-r{index:03}'
        for condition in CorruptionCondition:
            family = 'physical_absence_worlds_v1' if condition.value == 'missing_landmark' else 'physical_worlds_v1'
            request, _, runtime = prepare(ROOT / 'data' / family / base,
                f'{base}-{condition.value}-s0', f'offline-{base}-{condition.value}', 89)
            start = runtime.execution[0].start
            command = physical_simulation_command(request, dict(x=start.x, y=start.y, yaw=start.yaw))
            rows.append({'base_instruction_id': base, 'condition': condition.value,
                         'world_family': family, 'route_count': len(runtime.execution),
                         'asset_sha256': request['asset_sha256'],
                         'simulation_seed': request['simulation_seed'],
                         'launch_argv': command, 'passed': True})
    return {'schema_version': 'research3-offline-readiness/v1',
            'nonprotected_world_count': 14, 'condition_preflights': len(rows),
            'source_sha256': request['source_sha256'], 'rows': rows,
            'simulation_launched': False, 'protected_content_used': False,
            'campaign_authorized': False,
            'remaining_evidence_gates': ['live_inspection_and_point_goal_validation',
                'live_seed_and_absence_intervention_validation',
                'new_world_detector_capture_and_individual_visual_qa',
                'genuine_human_labels_and_calibration_freeze',
                'protocol_approval_and_heldout_authorization'],
            'scope': 'input and command construction checks, not physical or statistical validation'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = check()
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(f"Passed {result['condition_preflights']} non-protected offline preflights; no simulation launched")


if __name__ == '__main__':
    main()
