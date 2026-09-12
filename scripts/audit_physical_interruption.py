#!/usr/bin/env python3
"""Audit partial interrupted measurements without rewriting historical outcomes."""
import argparse
import hashlib
import json
from pathlib import Path

from language_nav.live import terminal_identity_outcome, validate_trajectory_evidence


def audit(directory):
    directory = Path(directory)
    summary = json.loads((directory / 'summary.json').read_text())
    if (summary.get('schema_version') != 'research3-live-summary/v3'
            or summary.get('infrastructure_failure') is not True
            or summary.get('partition') not in {'development', 'validation'}
            or summary.get('protected_test_routes_used') is not False):
        raise ValueError('explicit non-protected v3 infrastructure interruption required')
    raw = (directory / 'measurements.json').read_bytes()
    checksum = hashlib.sha256(raw).hexdigest()
    if checksum != summary.get('measurements_sha256'):
        raise ValueError('interruption measurements checksum mismatch')
    evidence = json.loads(raw)
    if evidence.get('schema_version') != 'research3-live-measurements/v2' or evidence.get('run_id') != summary.get('run_id'):
        raise ValueError('interruption evidence identity/schema mismatch')
    for key in ('episode_started_at_ns', 'episode_ended_at_ns', 'timeout'):
        if evidence.get(key) != summary.get(key) or type(evidence.get(key)) is not type(summary.get(key)):
            raise ValueError('interruption episode window mismatch')
    count = evidence.get('collision_count')
    if type(count) is not int or count < 0 or type(evidence.get('timeout')) is not bool:
        raise ValueError('invalid partial collision/timeout measurement')
    if summary.get('collision') is not bool(count):
        raise ValueError('interruption collision evidence mismatch')
    quality = validate_trajectory_evidence(evidence['ground_truth_positions'], evidence['ground_truth_timestamps_ns'],
                                           evidence['episode_started_at_ns'], evidence['episode_ended_at_ns'])
    dispatch = any(type(row.get('decided_at_ns')) is int
                   and evidence['episode_started_at_ns'] <= row['decided_at_ns'] <= evidence['episode_ended_at_ns']
                   for row in evidence.get('decisions', []))
    terminal, terminal_issue = None, None
    if quality['valid']:
        try:
            terminal = terminal_identity_outcome(evidence['ground_truth_positions'], evidence['terminal_ground_truth'],
                                                 evidence['expected_terminal_region_id'], summary['terminal_radius_m'])['terminal_identity_correct']
        except (KeyError, TypeError, ValueError) as exc:
            terminal_issue = str(exc)  # Missing terminal truth cannot erase a known collision.
    known_failure = count > 0 or evidence['timeout']
    return {'schema_version': 'research3-interrupted-outcome-audit/v1', 'run_id': summary['run_id'],
            'measurements_sha256': checksum, 'infrastructure_failure': True,
            'instruction_dispatch_established': dispatch,
            'trajectory_quality': quality, 'collision': True if count else None,
            'timeout': True if evidence['timeout'] else None,
            'navigation_success': False if known_failure else None,
            'instruction_completion': False if known_failure else None,
            'terminal_identity_correct': terminal,
            'terminal_evidence_issue': terminal_issue,
            'scientific_release_complete': False,
            'limitations': ['Zero partial-window collisions or timeout false do not prove a completed trial was event-free.',
                           'Known failure dominates unknown terminal outcome; no success is imputed.',
                           'Dispatch means an in-window policy decision, not necessarily a navigation goal.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.run)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
