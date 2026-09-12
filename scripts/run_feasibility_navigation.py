#!/usr/bin/env python3
"""Nonprotected paired B5/B6 navigation feasibility runs on development worlds.

Purpose: supply the empirical nuisance estimates the accepted P1 method decision
requires before any sample-size or confirmatory designation: baseline ordered
completion, paired discordance and between-world dependence. Ten development
worlds x eight instruction conditions x two systems, one simulator seed, in a
seeded block order with alternating within-block system order. Plan-only unless
--execute. Every attempt is retained under its own run ID; no retries; halts on
consecutive infrastructure failures. Engineering evidence only: no protected
world, no calibration transfer claim, no confirmatory inference.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import random
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
RUNNER = ROOT / 'scripts/run_physical_episode.py'
RUNS = ROOT / 'reports/physical_live_episodes'
PROFILES = ROOT / 'reports/fresh_current_capture_20260911_v1/profiles'
CONDITIONS = ('truthful_original', 'truthful_paraphrase', 'ambiguous_reference', 'missing_landmark',
              'attribute_corruption', 'relation_corruption', 'topology_corruption', 'false_inserted_clause')
SYSTEMS = ('B5', 'B6')
WORLDS = tuple(f'base-r{i:03d}' for i in range(1, 11))
PREFIX = 'r3-feas-nav-v1'
SCHEMA = 'research3-feasibility-navigation-plan/v1'
MAX_CONSECUTIVE_INFRASTRUCTURE_FAILURES = 3


def sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_once(path, payload):
    with Path(path).open('x') as stream:
        json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def world_for(base, condition):
    family = 'physical_absence_worlds_v1' if condition == 'missing_landmark' else 'physical_worlds_readable_v1'
    return ROOT / 'data' / family / base


def plan_rows(order_seed=1):
    blocks = [dict(base=base, condition=condition) for base in WORLDS for condition in CONDITIONS]
    rng = random.Random(order_seed)
    rng.shuffle(blocks)
    rows = []
    for index, block in enumerate(blocks):
        systems = SYSTEMS if index % 2 == 0 else tuple(reversed(SYSTEMS))
        for position, system in enumerate(systems):
            rows.append(dict(block, system_id=system, paired_block_index=index, within_block_position=position,
                             run_id=f'{PREFIX}-{block["base"][-4:]}-{block["condition"]}-{system.lower()}-s1',
                             variant_id=f'{block["base"]}-{block["condition"]}-s0', simulation_seed=1,
                             world_directory=str(world_for(block['base'], block['condition']).relative_to(ROOT))))
    return rows


def command(row, *, domain, timeout):
    return ['nice', '-n', '15', 'python3', str(RUNNER), '--world', str(ROOT / row['world_directory']),
            '--variant-id', row['variant_id'], '--run-id', row['run_id'], '--system-id', row['system_id'],
            '--ros-domain-id', str(domain), '--timeout', str(timeout), '--simulation-seed', str(row['simulation_seed']),
            '--camera-profile', str(PROFILES / f'{row["base"]}.yaml'), '--camera-horizontal-fov', '2.0',
            '--capture-perception']


def run_owned(argv, log):
    process = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT, start_new_session=True)
    try:
        return process.wait(timeout=900)
    except BaseException:
        for sig, grace in ((signal.SIGINT, 30), (signal.SIGTERM, 15), (signal.SIGKILL, 5)):
            if process.poll() is not None:
                break
            os.killpg(process.pid, sig)
            try:
                process.wait(timeout=grace)
                break
            except subprocess.TimeoutExpired:
                continue
        raise


def outcome(run_dir):
    run_dir = Path(run_dir)
    summary = run_dir / 'summary.json'
    if summary.exists():
        record = json.loads(summary.read_bytes())
        return dict(status='infrastructure_failure' if record.get('infrastructure_failure') else 'measured',
                    instruction_completion=record.get('instruction_completion'),
                    navigation_success=record.get('navigation_success'), collision=record.get('collision'),
                    timeout=record.get('timeout'), terminal_identity_correct=record.get('terminal_identity_correct'),
                    route_id=record.get('route_id'), reason=record.get('reason'), summary_sha256=sha_file(summary),
                    dispatched=True)
    failure = run_dir / 'failure.json'
    record = json.loads(failure.read_bytes()) if failure.exists() else {}
    return dict(status='infrastructure_failure', instruction_completion=None, navigation_success=None, collision=None,
                timeout=None, terminal_identity_correct=None, route_id=None, reason=record.get('error', 'no summary'),
                summary_sha256=None, dispatched=bool(record.get('dispatched')))


def existing(directory):
    path = Path(directory) / 'attempts.jsonl'
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def execute(args):
    from language_nav.live_resources import require_research2_idle, coexistence_headroom
    from language_nav.campaign_authorization import exclusive_campaign_runtime
    rows = plan_rows(args.order_seed)
    directory = Path(args.lifecycle_directory).resolve()
    if args.resume:
        planned = json.loads((directory / 'planned.json').read_bytes())
        if [r['run_id'] for r in planned['rows']] != [r['run_id'] for r in rows]:
            raise ValueError('resume must continue the identical plan')
        done = {r['run_id'] for r in existing(directory)}
    else:
        directory.mkdir(parents=True, exist_ok=False)
        done = set()
        write_once(directory / 'planned.json', dict(
            schema_version=SCHEMA, order_seed=args.order_seed, ros_domain_id=args.ros_domain_id, timeout_s=args.timeout,
            systems=list(SYSTEMS), conditions=list(CONDITIONS), worlds=list(WORLDS), simulation_seed=1,
            runner_sha256=sha_file(RUNNER), calibration=None,
            calibration_note='no calibration artifact passed, matching the retained engineering smoke configuration',
            rows=[dict(r, argv=command(r, domain=args.ros_domain_id, timeout=args.timeout)) for r in rows],
            evidence_scope='nonprotected development feasibility for nuisance estimation; not confirmatory',
            execute=bool(args.execute), protected_content_read=False))
    if not args.execute:
        print(json.dumps(dict(planned=len(rows), executed=False)))
        return
    consecutive = 0
    with exclusive_campaign_runtime(), (directory / 'attempts.jsonl').open('a') as ledger:
        for row in rows:
            if row['run_id'] in done:
                continue
            if args.limit is not None and len(existing(directory)) >= args.limit:
                break
            if (RUNS / row['run_id']).exists():
                raise FileExistsError('run directory exists: ' + row['run_id'])
            require_research2_idle()
            headroom = coexistence_headroom()
            argv = command(row, domain=args.ros_domain_id, timeout=args.timeout)
            started = dt.datetime.now(dt.timezone.utc).isoformat()
            with (directory / f'{row["run_id"]}.log').open('x') as log:
                code = run_owned(argv, log)
            result = outcome(RUNS / row['run_id'])
            record = dict(row, exit_code=code, started_at_utc=started, finished_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                          headroom_before=headroom, run_directory=str(RUNS / row['run_id']),
                          request_sha256=sha_file(RUNS / row['run_id'] / 'request.json') if (RUNS / row['run_id'] / 'request.json').exists() else None,
                          **result)
            ledger.write(json.dumps(record, sort_keys=True) + '\n')
            ledger.flush()
            os.fsync(ledger.fileno())
            print(json.dumps({k: record[k] for k in ('run_id', 'status', 'instruction_completion', 'exit_code')}), flush=True)
            consecutive = consecutive + 1 if record['status'] == 'infrastructure_failure' else 0
            if consecutive >= MAX_CONSECUTIVE_INFRASTRUCTURE_FAILURES:
                print(json.dumps(dict(halted='consecutive infrastructure failures')), flush=True)
                break
    write_report(directory, rows)


def nuisance_estimates(records):
    """World-paired nuisance estimates from measured B5/B6 completion outcomes."""
    by_key = {}
    for record in records:
        if record['status'] != 'measured' or record['instruction_completion'] is None:
            continue
        by_key[(record['base'], record['condition'], record['system_id'])] = bool(record['instruction_completion'])
    pairs = [(by_key[(b, c, 'B5')], by_key[(b, c, 'B6')], b) for b in WORLDS for c in CONDITIONS
             if (b, c, 'B5') in by_key and (b, c, 'B6') in by_key]
    if not pairs:
        return dict(complete_pairs=0, baseline_completion=None, paired_discordance=None, world_icc=None)
    baseline = sum(p[0] for p in pairs) / len(pairs)
    b6 = sum(p[1] for p in pairs) / len(pairs)
    discordance = sum(p[0] != p[1] for p in pairs) / len(pairs)
    worlds = {}
    for y5, y6, base in pairs:
        worlds.setdefault(base, []).append(float(y6) - float(y5))
    # One-way ANOVA ICC on paired differences: between-world variance share.
    groups = [v for v in worlds.values() if len(v) > 1]
    icc = None
    if len(groups) >= 2:
        n = [len(g) for g in groups]
        means = [sum(g) / len(g) for g in groups]
        grand = sum(sum(g) for g in groups) / sum(n)
        ms_between = sum(k * (m - grand) ** 2 for k, m in zip(n, means)) / (len(groups) - 1)
        ms_within = sum((x - m) ** 2 for g, m in zip(groups, means) for x in g) / (sum(n) - len(groups))
        n0 = (sum(n) - sum(k * k for k in n) / sum(n)) / (len(groups) - 1)
        icc = (ms_between - ms_within) / (ms_between + (n0 - 1) * ms_within) if (ms_between + (n0 - 1) * ms_within) > 0 else 0.
        icc = max(-1., min(1., icc))
    return dict(complete_pairs=len(pairs), baseline_completion=baseline, b6_completion=b6,
                mean_paired_difference=b6 - baseline, paired_discordance=discordance, world_icc=icc,
                worlds_with_pairs=len(worlds), per_world_mean_difference={b: sum(v) / len(v) for b, v in worlds.items()},
                estimator='world one-way ANOVA ICC on paired differences; proportions over complete pairs')


def write_report(directory, rows):
    records = existing(directory)
    counts = {}
    for record in records:
        counts[record['status']] = counts.get(record['status'], 0) + 1
    report = dict(schema_version='research3-feasibility-navigation-report/v1', scheduled=len(rows), attempted=len(records),
                  status_counts=counts, complete=len(records) == len(rows),
                  nuisance_estimates=nuisance_estimates(records),
                  attempts=[{k: r.get(k) for k in ('run_id', 'base', 'condition', 'system_id', 'status', 'instruction_completion',
                                                    'navigation_success', 'collision', 'timeout', 'terminal_identity_correct',
                                                    'request_sha256', 'summary_sha256', 'reason')} for r in records],
                  evidence_scope='nonprotected development feasibility; engineering nuisance estimates, not confirmatory results',
                  protected_content_read=False, written_at_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    path = Path(directory) / 'report.json'
    if path.exists():
        path.rename(Path(directory) / f'report.superseded.{int(dt.datetime.now().timestamp())}.json')
    write_once(path, report)
    print(json.dumps({k: report[k] for k in ('scheduled', 'attempted', 'status_counts', 'complete', 'nuisance_estimates')}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lifecycle-directory', type=Path, required=True)
    parser.add_argument('--order-seed', type=int, default=1)
    parser.add_argument('--ros-domain-id', type=int, default=89)
    parser.add_argument('--timeout', type=int, default=90)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--report-only', action='store_true')
    args = parser.parse_args()
    if args.report_only:
        write_report(args.lifecycle_directory, plan_rows(args.order_seed))
        return
    execute(args)


if __name__ == '__main__':
    main()
