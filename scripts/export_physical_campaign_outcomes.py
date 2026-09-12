#!/usr/bin/env python3
"""Audit explicit non-protected run assignments into draft scheduled outcomes."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
ANALYZER = runpy.run_path(str(ROOT / 'scripts/analyze_physical_campaign.py'))
audit_summary = runpy.run_path(str(ROOT / 'scripts/analyze_measured_live.py'))['audit_summary']
audit_interruption = runpy.run_path(str(ROOT / 'scripts/audit_physical_interruption.py'))['audit']


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export(manifest, assignments):
    # Reject protected schedules and inconsistent identities before opening runs.
    ANALYZER['analyze'](manifest, [])
    scheduled = {row['episode_id']: row for row in manifest['episodes']}
    assigned, directories = set(), set()
    for assignment in assignments:
        episode_id = assignment.get('episode_id')
        directory = Path(assignment['run_directory']).resolve()
        if episode_id not in scheduled or episode_id in assigned or directory in directories:
            raise ValueError('unknown/duplicate episode assignment or reused run directory')
        assigned.add(episode_id)
        directories.add(directory)
    outcomes, unresolved, sources, run_ids = [], [], [], set()
    for assignment in assignments:
        episode_id = assignment['episode_id']
        row = scheduled[episode_id]
        directory = Path(assignment['run_directory']).resolve()
        try:
            request = read(directory / 'request.json')
            if (request.get('protected_test_routes_used') is not False
                    or request.get('partition') not in {'development', 'validation'}):
                raise ValueError('non-protected request required')
            if any(request.get(key) != row[key] for key in ('system_id', 'variant_id', 'partition')):
                raise ValueError('request/schedule identity mismatch')
            if request.get('map_id') != 'r3geo_' + row['base_instruction_id'].replace('-', '_'):
                raise ValueError('request map/base identity mismatch')
            run_id = request.get('run_id')
            if not isinstance(run_id, str) or not run_id or run_id in run_ids:
                raise ValueError('missing/duplicate run identity')
            run_ids.add(run_id)
            if request.get('capture_only'):
                raise ValueError('stationary capture is not a campaign attempt')
            identity = {key: row[key] for key in ANALYZER['IDENTITY']}
            identity.update({key: row[key] for key in ('condition',) if key in row})
            outcome = {**identity, 'schema_version': 'research3-physical-campaign-outcome/v1',
                       'run_id': run_id, 'attempted': True}
            if (directory / 'summary.json').exists():
                retained = read(directory / 'summary.json')
                interrupted = retained.get('infrastructure_failure') is True
                partial = audit_interruption(directory) if interrupted else None
                summary = retained if interrupted else audit_summary(directory / 'summary.json')
                if summary.get('schema_version') != 'research3-live-summary/v3':
                    raise ValueError('timestamped v3 summary required for scheduled export')
                if not interrupted and summary.get('infrastructure_failure') is not False:
                    raise ValueError('explicit independently audited non-infrastructure outcome required')
                if any(summary.get(key) != request.get(key) for key in ('run_id', 'system_id', 'variant_id', 'partition')):
                    raise ValueError('summary/request identity mismatch')
                measurements = read(directory / 'measurements.json')
                decisions = measurements.get('decisions', [])
                if not decisions or not any(
                    type(d.get('decided_at_ns')) is int
                    and measurements['episode_started_at_ns'] <= d['decided_at_ns'] <= measurements['episode_ended_at_ns']
                    for d in decisions):
                    raise ValueError('instruction dispatch not established by in-window policy decision')
                measured = partial if interrupted else summary
                outcome.update(dispatched=True, infrastructure_failure=interrupted,
                               **{key: measured.get(key) for key in ANALYZER['METRICS']})
                if interrupted:
                    outcome['interruption_audit'] = partial
                names = ['request.json', 'summary.json', 'measurements.json']
            else:
                failure = read(directory / 'failure.json')
                if (failure.get('dispatched') is not False
                        or any((directory / name).exists() for name in ('capture.json', 'measurements.json'))):
                    raise ValueError('failure dispatch/outcome requires independent audit; not imputed')
                outcome.update(dispatched=False, infrastructure_failure=True,
                               **{key: None for key in ANALYZER['METRICS']})
                names = ['request.json', 'failure.json']
            ANALYZER['analyze'](manifest, [outcome])
            outcomes.append(outcome)
            sources.append({'episode_id': episode_id, 'run_id': run_id,
                            'files': {name: {'path': str(directory / name), 'sha256': digest(directory / name)}
                                      for name in names}})
        except (ValueError, KeyError, TypeError, OSError) as exc:
            unresolved.append({'episode_id': episode_id, 'run_directory': str(directory),
                               'reason': str(exc), 'outcome_imputed': False})
    return {'schema_version': 'research3-scheduled-outcome-export/v1',
            'status': 'blocked_unresolved_assignments' if unresolved else 'draft_export_complete',
            'campaign_authorized': False, 'scientific_release_complete': False,
            'scheduled': len(scheduled), 'assigned': len(assignments),
            'unassigned_episode_ids': sorted(set(scheduled) - assigned),
            'outcomes': outcomes, 'unresolved_assignments': unresolved, 'sources': sources,
            'standalone_outcome_list_exportable': not unresolved,
            'dispatch_definition': 'instruction reached policy, demonstrated by an in-window recorded decision; not necessarily navigation goal dispatch',
            'limitations': ['Engineering export does not freeze protocol/calibration or authorize a campaign.',
                'Interrupted measured runs receive a separate partial-evidence audit; unresolved assignments are retained, never silently dropped.',
                'Retained explicit pre-dispatch failures have unknown endpoints; no raw motion success is inferred.',
                'Held-out export requires a separately authorized evaluator and is rejected here.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--assignments', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--outcomes-output', type=Path)
    args = parser.parse_args()
    report = export(read(args.manifest), read(args.assignments))
    report['input_sha256'] = {'manifest': digest(args.manifest), 'assignments': digest(args.assignments)}
    with args.report.open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    if args.outcomes_output:
        if not report['standalone_outcome_list_exportable']:
            raise SystemExit('unresolved assignments retained in report; refusing partial outcome-list export')
        with args.outcomes_output.open('x') as stream:
            json.dump(report['outcomes'], stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write('\n')


if __name__ == '__main__':
    main()
