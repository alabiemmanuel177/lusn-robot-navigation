#!/usr/bin/env python3
"""Default-deny held-out navigation, not calibration collection or human review.

All runtime choices come from the exact human-approved schedule. There are no
caller-selectable map, camera, condition, seed, capture or coexistence overrides.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import signal

from language_nav.physical_heldout_authorization import ROOT, authorize, pinned, contained
from language_nav.campaign_authorization import exclusive_campaign_runtime
from language_nav.live_resources import require_research2_idle, coexistence_headroom


def prepare_authorized(path, digest, episode_id):
    authorization = authorize(path, digest, episode_id)
    row = authorization.episode
    spec = importlib.util.spec_from_file_location('authorized_physical_runtime', ROOT / 'scripts/run_physical_episode.py')
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    request, variant, catalog = runtime.prepare(authorization.root / row['world_directory'], row['variant_id'],
        row['run_id'], authorization.approval['ros_domain_id'], row['timeout_s'], row['simulation_seed'],
        heldout_authorization=authorization)
    request.update(system_id=row['system_id'], camera_horizontal_fov=row['camera_horizontal_fov'],
        camera_color_tolerance=row['camera_color_tolerance'],
        calibration_sha256=authorization.approval['calibration']['sha256'],
        allow_coexistence_trial=False, capture_only=False, capture_perception=False,
        capture_review=False, capture_context=False, capture_frame_budget=5,
        capture_target_categories=None, context_sampling=None)
    start = catalog.execution[0].start
    request['simulation_launch_argv'] = runtime.physical_simulation_command(request,
        {'x': start.x, 'y': start.y, 'yaw': start.yaw})
    return authorization, runtime, request, variant, catalog


def execute_authorized(path, digest, episode_id):
    with exclusive_campaign_runtime():
        require_research2_idle()
        coexistence_headroom()
        authorization, runtime, request, variant, catalog = prepare_authorized(path, digest, episode_id)
        for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
            os.environ[name] = '2'
        os.nice(max(0, 15 - os.getpriority(os.PRIO_PROCESS, 0)))
        report = contained(ROOT, 'reports/physical_live_episodes/' + request['run_id'])
        report.mkdir(parents=True, exist_ok=False)
        runtime.write_once(report / 'request.json', request)
        def terminate(_signal, _frame):
            raise KeyboardInterrupt('held-out wrapper terminated; retaining interrupted attempt')
        previous = signal.signal(signal.SIGTERM, terminate)
        try:
            runtime.execute(request, variant, catalog, report, request['system_id'],
                            pinned(authorization.root, authorization.approval['calibration']))
        except BaseException as exc:
            if not (report / 'failure.json').exists():
                runtime.write_once(report / 'failure.json', {'error': str(exc), 'error_type': type(exc).__name__,
                    'retry_policy': 'retain failure; no automatic replacement',
                    'execution_or_dispatch_not_inferred': True})
            raise
        finally:
            signal.signal(signal.SIGTERM, previous)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authorization', required=True, type=Path)
    parser.add_argument('--authorization-sha256', required=True)
    parser.add_argument('--episode-id', required=True)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    if args.prepare_only:
        _, _, request, _, _ = prepare_authorized(args.authorization, args.authorization_sha256, args.episode_id)
        print(json.dumps(request, indent=2, sort_keys=True, allow_nan=False))
    else:
        execute_authorized(args.authorization, args.authorization_sha256, args.episode_id)


if __name__ == '__main__':
    main()
