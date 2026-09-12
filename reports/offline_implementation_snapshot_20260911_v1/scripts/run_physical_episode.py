#!/usr/bin/env python3
"""Create-once development/validation language-policy episode in a physical world.

Source the three ROS overlays before live use. This is an engineering runner,
not a frozen campaign protocol or a claim of transferred detector calibration.
--prepare-only validates inputs without importing ROS or launching anything.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import threading
import time

from language_nav.benchmark.physical_catalog import validate_physical_launch_inputs
from language_nav.evaluation.ordered import score_ordered_instruction
from language_nav.live import (measured_live_outcome, path_length,
                               terminal_identity_outcome, validate_trajectory_evidence)

ROOT = Path(__file__).resolve().parents[1]
R1 = Path('/home/eao/risk-calibrated-nav')


def write_once(path, payload):
    with Path(path).open('x') as stream:
        json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def prepare(world, variant_id, run_id, domain_id, timeout=180.0, simulation_seed=1):
    """Validate deployable inputs; never select an evaluator's expected route."""
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,95}', run_id):
        raise ValueError('run ID must be a safe single directory name')
    if type(domain_id) is not int or not 1 <= domain_id <= 101:
        raise ValueError('explicit isolated ROS domain must be between 1 and 101')
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('timeout must be finite and positive')
    if type(simulation_seed) is not int or not 1 <= simulation_seed <= 2**32 - 1:
        raise ValueError('simulation_seed must be an integer in [1, 4294967295]')
    world = Path(world).resolve()
    catalog = validate_physical_launch_inputs(
        world / 'execution_catalog.json', world / 'landmark_scene.yaml', world / 'map.yaml')
    variants = json.loads((ROOT / 'data/manifests/instruction_benchmark_v0.1.json').read_text())
    variant = next((row for row in variants['deployed_variants'] if row['variant_id'] == variant_id), None)
    if variant is None or any(route.base_instruction_id != variant['base_instruction_id']
                              for route in catalog.semantic.routes):
        raise ValueError('instruction does not belong to physical world')
    absence_path = world / 'absence_intervention.json'
    missing_condition = variant_id == variant['base_instruction_id'] + '-missing_landmark-s0'
    if missing_condition and not absence_path.exists():
        raise ValueError('missing-landmark execution requires a validated physical absence intervention; unchanged worlds are not eligible')
    if absence_path.exists() and not missing_condition:
        raise ValueError('absent-chair world requires missing-landmark instruction condition')
    if catalog.semantic.partition not in {'development', 'validation'}:
        raise PermissionError('held-out execution is not permitted by this engineering runner')
    request = {
        'schema_version': 'research3-physical-live-request/v1', 'run_id': run_id,
        'world_directory': str(world), 'map_id': catalog.semantic.map_id,
        'partition': catalog.semantic.partition, 'variant_id': variant_id,
        'ros_domain_id': domain_id, 'worker_id': 'research3-' + run_id,
        'protected_test_routes_used': False, 'timeout_s': timeout,
        'simulation_seed': simulation_seed, 'runtime_seed_acceptance_validated': False,
        'evidence_scope': 'physical_world_engineering_not_comparative_campaign',
        'detector_calibration_transfer_validated': False,
        'asset_sha256': {name: hashlib.sha256((world / name).read_bytes()).hexdigest()
                         for name in ('world.sdf', 'map.pgm', 'map.yaml',
                                      'execution_catalog.json', 'landmark_scene.yaml',
                                      'manifest.json', 'verified_ordered_geometry.json')},
    }
    request['source_revision'] = subprocess.check_output(
        ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    request['environment_intervention'] = 'missing_landmark' if missing_condition else 'none'
    if missing_condition:
        request['asset_sha256']['absence_intervention.json'] = hashlib.sha256(absence_path.read_bytes()).hexdigest()
    request['source_sha256'] = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (Path(__file__).resolve(), ROOT / 'src/language_nav/live.py',
                     ROOT / 'src/language_nav/evaluation/ordered.py',
                     ROOT / 'src/language_nav/benchmark/physical_catalog.py',
                     ROOT / 'src/language_nav/systems/variants.py',
                     ROOT / 'src/language_nav/planning/policy.py',
                     ROOT / 'src/language_nav/grounding/routes.py',
                     ROOT / 'scripts/physical_perception_capture.py',
                     ROOT / 'src/language_nav/live_resources.py',
                     ROOT / 'ros_ws/src/language_nav_bringup/launch/live_adapters.launch.py',
                     ROOT / 'ros_ws/src/language_nav_bringup/launch/physical_sim.launch.py',
                     ROOT / 'ros_ws/src/language_nav_runtime/language_nav_runtime/nav2_adapter.py',
                     ROOT / 'ros_ws/src/language_nav_planner/language_nav_planner/node.py')}
    start = catalog.execution[0].start
    request['simulation_launch_argv'] = physical_simulation_command(request, dict(x=start.x, y=start.y, yaw=start.yaw))
    return request, variant, catalog


def overlay_command(request, report_dir, system_id, calibration=None):
    """No evaluator manifest, expected route, or gate annotations enter runtime."""
    world = Path(request['world_directory'])
    command = ['ros2', 'launch', 'language_nav_bringup', 'live_adapters.launch.py',
               f'scene:={request.get("runtime_scene", str(world / "landmark_scene.yaml"))}',
               f'physical_catalog:={world / "execution_catalog.json"}',
               f'partition:={request["partition"]}', f'run_id:={request["run_id"]}',
               f'system_id:={system_id}',
               f'research2_output_dir:={report_dir / "research2"}',
               f'research3_output_dir:={report_dir / "research3"}']
    if request.get('camera_color_tolerance') is not None:
        command.append(f'color_tolerance:={request["camera_color_tolerance"]}')
    if calibration:
        command.append(f'calibration:={Path(calibration).resolve()}')
    if request.get('capture_review'):
        command.append(f'review_log:={report_dir / "landmark_review_tasks.jsonl"}')
    return command


def physical_simulation_command(request, start):
    """R3-owned launch passes an actual Gazebo seed; no provider launch mutation."""
    seed = request['simulation_seed']
    if type(seed) is not int or not 1 <= seed <= 2**32 - 1:
        raise ValueError('invalid simulator seed')
    return ['ros2', 'launch', 'language_nav_bringup', 'physical_sim.launch.py',
            f'world_path:={Path(request["world_directory"]) / "world.sdf"}',
            f'simulation_seed:={seed}', f'x_pose:={start["x"]}',
            f'y_pose:={start["y"]}', f'yaw:={start["yaw"]}']


def evaluate(request, evidence):
    """Evaluate retained measurements only after policy execution has finished."""
    world = Path(request['world_directory'])
    for name, digest in request['asset_sha256'].items():
        if hashlib.sha256((world / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'input changed during episode: {name}')
    manifest = json.loads((world / 'manifest.json').read_text())
    geometry = json.loads((world / 'verified_ordered_geometry.json').read_text())
    if (manifest['partition'] != request['partition'] or manifest['map_id'] != request['map_id']
            or geometry['map_sha256'] != manifest['map_sha256']
            or geometry['base_instruction_id'] != manifest['base_instruction_id']
            or not geometry.get('geometry_verified')):
        raise ValueError('evaluator geometry identity/verification mismatch')
    target = next(row for row in manifest['candidates'] if row['route_id'] == manifest['expected_route_id'])
    # Navigation accuracy is against the policy-selected endpoint, not the hidden
    # semantic target. Terminal and ordered scores independently use the latter.
    selected = next((row for row in manifest['candidates']
                     if row['route_id'] == evidence.get('selected_route_id')), None)
    goal = selected['goal'] if selected else None
    evidence.update(commanded_goal=[goal['x'], goal['y']] if goal else None, goal_tolerance_m=.35,
                    terminal_ground_truth=manifest['terminal_entities'],
                    expected_terminal_region_id=target['terminal_entity_id'] + '_region',
                    ordered_geometry=geometry)
    positions = evidence['ground_truth_positions']
    summary = measured_live_outcome(
        positions=positions, distance_m=path_length(positions), goal=evidence['commanded_goal'] or (0., 0.),
        goal_tolerance_m=.35, collision=bool(evidence['collision_count']),
        timeout=evidence['timeout'], nav2_success=evidence['nav2_reported_success'])
    summary.update(terminal_identity_outcome(positions, manifest['terminal_entities'],
                   evidence['expected_terminal_region_id'], radius_m=1.0))
    score = score_ordered_instruction(positions, geometry,
        terminal_identity_correct=summary['terminal_identity_correct'],
        collision=summary['collision'], timeout=summary['timeout'])
    quality = validate_trajectory_evidence(positions, evidence['ground_truth_timestamps_ns'],
        evidence['episode_started_at_ns'], evidence['episode_ended_at_ns'])
    completion = score['instruction_completion'] if quality['valid'] else None
    summary.update(ordered_instruction_score=score, instruction_completion=completion,
                   semantic_outcome_measured=completion is not None, trajectory_quality=quality,
                   valid_terminal_outcome=quality['valid'])
    summary['navigation_success'] &= quality['valid'] and selected is not None
    if selected is None:
        if evidence['nav2_reported_success']:
            raise ValueError('navigation success requires a confirmed dispatched route')
        summary.update(goal_error_m=None, goal_reached=None)
    return summary


def confirmed_execution(path, request, instruction_id, wait_s=0.0):
    """Do not confuse a speculative planner decision with an executed route."""
    deadline = time.monotonic() + wait_s
    while True:
        try:
            raw = Path(path).read_bytes()
            record = json.loads(raw)
            break
        except (FileNotFoundError, json.JSONDecodeError):
            if time.monotonic() >= deadline:
                return None
            time.sleep(.05)
    if (record.get('schema_version') != 'research3-live-episode/v1'
            or record.get('run_id') != request['run_id']
            or record.get('instruction_id') != instruction_id):
        raise ValueError('adapter execution identity mismatch')
    # A stop decision after inspection may have an empty route and started=0;
    # retain that as abstention, not a commanded navigation endpoint.
    if record.get('started_at_ns', 0) <= 0 or not record.get('route_id'):
        return None
    return {'record': record, 'sha256': hashlib.sha256(raw).hexdigest()}


def retain_capture_then_confirm(report_dir, request, instruction_id, evidence, wait_s=0.0):
    """Raw independent telemetry must survive invalid adapter identity/records."""
    write_once(report_dir / 'capture.json', evidence)
    execution = confirmed_execution(report_dir / 'research3' / (request['run_id'] + '.json'),
                                    request, instruction_id, wait_s)
    evidence.update(selected_route_id=execution['record']['route_id'] if execution else None,
                    confirmed_adapter_execution=execution,
                    nav2_reported_success=evidence['raw_outcome_navigation_success'])


def execute(request, variant, catalog, report_dir, system_id, calibration=None):
    from language_nav.live_resources import require_research2_idle
    require_research2_idle()
    # Import ROS only for live execution, after offline checks and create-once setup.
    from run_live_episode import (TimestampedEpisodeMonitor, LiveController, HAVE_CONTACTS,
        Stack, preflight, load_system_config, nav2_bringup_ready,
        simulation_launch_command, write_episode_params)
    import rclpy
    from geometry_msgs.msg import PoseWithCovarianceStamped
    from nav2_msgs.action import NavigateToPose
    from rclpy.action import ActionClient
    from rclpy.executors import MultiThreadedExecutor
    from tf2_ros import Buffer, TransformListener

    if not HAVE_CONTACTS:
        raise RuntimeError('contact measurement is unavailable')
    os.environ['RCN_WORKER_ID'] = request['worker_id']
    os.environ['ROS_DOMAIN_ID'] = str(request['ros_domain_id'])
    # Gazebo transport is independent of DDS; isolate it as well.
    os.environ['GZ_PARTITION'] = request['worker_id']
    os.environ['IGN_PARTITION'] = request['worker_id']
    world = Path(request['world_directory'])
    start_pose = catalog.execution[0].start
    start = dict(x=start_pose.x, y=start_pose.y, yaw=start_pose.yaw)
    stack = Stack(report_dir / 'logs')
    monitor = controller = executor = spin = recorder = context_recorder = None
    started = False
    error = None
    try:
        rclpy.init()
        # A nonempty isolated domain is not safe to reuse: never attach to or
        # clean up another experiment. Discovery needs a brief bounded window.
        from rclpy.node import Node
        probe = Node('research3_domain_probe')
        try:
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline:
                rclpy.spin_once(probe, timeout_sec=.1)
            if any(name != probe.get_name() for name in probe.get_node_names()):
                raise RuntimeError('selected ROS domain is occupied; no simulator launched')
        finally:
            probe.destroy_node()
        require_research2_idle()
        stack.launch('sim', physical_simulation_command(request, start))
        ready = preflight.wait_until_ready({**preflight.MANDATORY, **preflight.EVALUATION_ONLY}, timeout_s=90)
        if not ready.ok:
            raise RuntimeError(ready.summary())
        params = write_episode_params(R1 / 'configs/nav2/nav2_common.yaml', report_dir / 'nav2_params.yaml',
            start['x'], start['y'], start['yaw'], load_system_config(R1 / 'configs/systems/s0.yaml'))
        stack.launch('nav2', ['ros2', 'launch', 'simulation_worlds', 'nav2.launch.py',
                             f'map:={world / "map.yaml"}', f'params_file:={params}'])
        monitor, controller = TimestampedEpisodeMonitor(perception_enabled=False), LiveController()
        transforms = Buffer()
        listener = TransformListener(transforms, monitor)
        executor = MultiThreadedExecutor(num_threads=4)
        executor.add_node(monitor)
        executor.add_node(controller)
        if request.get('capture_perception'):
            from physical_perception_capture import PhysicalPerceptionCapture
            recorder = PhysicalPerceptionCapture(report_dir / 'perception_capture',
                observation_triggered=request.get('capture_review', False))
            executor.add_node(recorder)
        spin = threading.Thread(target=executor.spin, daemon=True)
        spin.start()
        problem = nav2_bringup_ready(ActionClient(monitor, NavigateToPose, 'navigate_to_pose'), monitor, 90)
        if problem:
            raise RuntimeError(problem)
        initial = PoseWithCovarianceStamped()
        initial.header.frame_id = 'map'
        initial.pose.pose.position.x, initial.pose.pose.position.y = start['x'], start['y']
        initial.pose.pose.orientation.z = math.sin(start['yaw'] / 2)
        initial.pose.pose.orientation.w = math.cos(start['yaw'] / 2)
        initial.pose.covariance[0] = initial.pose.covariance[7] = .25
        initial.pose.covariance[35] = .068
        publisher = monitor.create_publisher(PoseWithCovarianceStamped, '/initialpose', 10)
        deadline = time.monotonic() + 60
        while not monitor.amcl_converged() and time.monotonic() < deadline:
            initial.header.stamp = monitor.get_clock().now().to_msg()
            publisher.publish(initial)
            time.sleep(.5)
        if not monitor.amcl_converged() or monitor.spawned_in_collision():
            raise RuntimeError('invalid initial localization/contact state')
        deadline, settled_ns = time.monotonic() + 15, monitor.get_clock().now().nanoseconds + 3_000_000_000
        while (monitor.get_clock().now().nanoseconds < settled_ns
               or not transforms.can_transform('map', 'base_link', monitor.get_clock().now())):
            if time.monotonic() > deadline:
                raise RuntimeError('map/base transform did not settle after clock switch')
            time.sleep(.1)
        (report_dir / 'research2').mkdir()
        (report_dir / 'research3').mkdir()
        stack.launch('research3', overlay_command(request, report_dir, system_id, calibration))
        deadline = time.monotonic() + 45
        while not controller.monitors and time.monotonic() < deadline:
            time.sleep(.1)
        if not controller.monitors:
            raise RuntimeError('Research 2 monitor readiness not observed')
        monitor.start()
        started = True
        if request.get('capture_context'):
            from physical_perception_capture import PhysicalPerceptionCapture
            # Start only after localization and provider readiness. No semantic
            # subscription: frame selection must not depend on detector output.
            context_recorder = PhysicalPerceptionCapture(report_dir / 'context_capture',
                max_frames=20, interval_s=2.0, observation_triggered=False,
                node_name='research3_independent_context_capture')
            executor.add_node(context_recorder)
        controller.publish_instruction(variant)
        deadline = time.monotonic() + request['timeout_s']
        last_count, last_progress = 0, time.monotonic()
        next_resource_check = 0.0
        while time.monotonic() < deadline and not controller.outcomes:
            if time.monotonic() >= next_resource_check:
                require_research2_idle()
                next_resource_check = time.monotonic() + 1.0
            sample = monitor.snapshot()
            if sample.collision:
                break
            if sample.gt_count != last_count:
                last_count, last_progress = sample.gt_count, time.monotonic()
            elif time.monotonic() - last_progress > 10:
                raise RuntimeError('simulator ground-truth heartbeat lost')
            if any(proc.poll() is not None for _, proc in stack.procs):
                raise RuntimeError('an episode stack process exited early')
            time.sleep(.1)
    except BaseException as exc:
        error = exc
    finally:
        # Persist even interruption/failed execution BEFORE possibly slow teardown.
        try:
            if started:
                monitor.stop()
                measurement = monitor.snapshot()
                outcomes = [o for o in controller.outcomes if o.instruction_id == variant['variant_id']]
                outcome = outcomes[-1] if outcomes else None
                decisions = [d for d in controller.decisions if d.instruction_id == variant['variant_id']]
                predictions = [p for p in controller.monitors if 'no_prediction_yet' not in p.reason_codes
                    and monitor.started_ns <= p.observed_at_ns <= monitor.ended_ns]
                evidence = {
                    'schema_version': 'research3-live-measurements/v2', 'run_id': request['run_id'],
                    'episode_started_at_ns': monitor.started_ns, 'episode_ended_at_ns': monitor.ended_ns,
                    'ground_truth_positions': list(measurement.gt_positions),
                    'ground_truth_timestamps_ns': list(monitor.position_stamps),
                    'collision_count': measurement.collision_count,
                    'timeout': outcome is None and not measurement.collision and error is None,
                    'raw_outcome_navigation_success': bool(outcome and outcome.navigation_success),
                    'nav2_reported_success': False,
                    'selected_route_id': None,
                    'confirmed_adapter_execution': None,
                    'predictions': [dict(observed_at_ns=p.observed_at_ns,
                        failure_probability=p.failure_probability, reason_codes=list(p.reason_codes)) for p in predictions],
                    'route_assessments': [dict(route_id=e.request_id, eligible=e.eligible,
                        reason=e.reason, risk=e.risk, assessed_at_ns=e.assessed_at_ns)
                        for e in controller.eligibility],
                    'decisions': [dict(action=d.action, route_id=d.route_id, reason=d.reason,
                                       decided_at_ns=d.decided_at_ns,
                                       candidates_json=d.candidates_json) for d in decisions],
                }
                # Retain telemetry before checking adapter identity or evaluating.
                retain_capture_then_confirm(report_dir, request, variant['variant_id'], evidence,
                                            2.0 if outcome else 0.0)
                summary = evaluate(request, evidence)
                if error is not None:
                    summary.update(navigation_success=False, instruction_completion=None,
                                   semantic_outcome_measured=False, valid_terminal_outcome=False)
                write_once(report_dir / 'measurements.json', evidence)
                summary.update(schema_version='research3-live-summary/v3', run_id=request['run_id'],
                    system_id=system_id, variant_id=variant['variant_id'], partition=request['partition'],
                    protected_test_routes_used=False, route_id=evidence['selected_route_id'],
                    detector_calibration_transfer_validated=False,
                    evidence_scope=request['evidence_scope'],
                    measurements_sha256=hashlib.sha256((report_dir / 'measurements.json').read_bytes()).hexdigest(),
                    episode_started_at_ns=monitor.started_ns, episode_ended_at_ns=monitor.ended_ns,
                    episode_prediction_count=len(predictions), collision_count=measurement.collision_count,
                    infrastructure_failure=error is not None,
                    reason=str(error) if error else (outcome.reason if outcome else 'collision or timeout'))
                write_once(report_dir / 'summary.json', summary)
            if error is not None:
                write_once(report_dir / 'failure.json', dict(error=str(error), error_type=type(error).__name__,
                           dispatched=started, retry_policy='retain failure; no automatic replacement'))
        finally:
            # Stack owns only descendants launched by this run; never broad pkill.
            try:
                stack.shutdown()
            finally:
                if executor:
                    executor.shutdown(timeout_sec=5)
                if controller:
                    controller.destroy_node()
                if recorder:
                    recorder.finish()
                    recorder.destroy_node()
                if context_recorder:
                    context_recorder.finish()
                    context_recorder.destroy_node()
                if monitor:
                    monitor.destroy_node()
                if rclpy.ok():
                    rclpy.shutdown()
                if spin:
                    spin.join(timeout=2)
    if error is not None:
        raise error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--world', type=Path, required=True)
    parser.add_argument('--variant-id', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--ros-domain-id', type=int, required=True)
    parser.add_argument('--timeout', type=float, default=180)
    parser.add_argument('--simulation-seed', type=int, default=1,
                        help='explicit Gazebo seed; does not claim bitwise determinism')
    parser.add_argument('--system-id', choices=('B1', 'B2', 'B4', 'B5', 'B6'), default='B6')
    parser.add_argument('--calibration', type=Path, help='optional engineering-only calibration; no transfer claim')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--capture-perception', action='store_true', help='retain bounded RGB-D diagnostics, not labels')
    parser.add_argument('--capture-review', action='store_true',
                        help='retain exact observation frames and pending provider review tasks; never labels')
    parser.add_argument('--capture-context', action='store_true',
                        help='retain up to 20 detector-independent full frames after readiness, every 2 simulated seconds')
    parser.add_argument('--camera-profile', type=Path, help='explicit development camera palette, not calibration')
    args = parser.parse_args()
    request, variant, catalog = prepare(args.world, args.variant_id, args.run_id, args.ros_domain_id,
                                        args.timeout, args.simulation_seed)
    request['system_id'] = args.system_id
    request['capture_perception'] = args.capture_perception or args.capture_review
    request['capture_review'] = args.capture_review
    request['capture_context'] = args.capture_context
    request['context_sampling'] = ({'max_frames': 20, 'interval_sim_s': 2.0,
        'start': 'after_localization_and_provider_readiness_before_instruction_dispatch',
        'selection': 'independent_of_detector_output',
        'scope': 'engineering_sample_not_a_frozen_recall_protocol'} if args.capture_context else None)
    if args.camera_profile:
        import yaml
        profile = yaml.safe_load(args.camera_profile.read_text())
        if (request['partition'] not in profile.get('partition_scope', [])
                or request['map_id'] not in profile.get('map_scope', [])):
            raise ValueError('camera profile does not cover this map/partition')
        tolerance = float(profile['color_tolerance'])
        if not math.isfinite(tolerance) or tolerance <= 0:
            raise ValueError('camera tolerance must be finite and positive')
        request['camera_color_tolerance'] = tolerance
        request['camera_profile_sha256'] = hashlib.sha256(args.camera_profile.read_bytes()).hexdigest()
    request['calibration_sha256'] = hashlib.sha256(args.calibration.read_bytes()).hexdigest() if args.calibration else None
    if args.prepare_only:
        print(json.dumps(request, indent=2, sort_keys=True))
        return
    report_dir = ROOT / 'reports/physical_live_episodes' / args.run_id
    report_dir.mkdir(parents=True, exist_ok=False)
    if args.camera_profile:
        from language_nav.adapters.landmark_palette import adapt_scene_palette
        runtime_scene = report_dir / 'runtime_scene.yaml'
        adapt_scene_palette(Path(request['world_directory']) / 'landmark_scene.yaml', runtime_scene, args.camera_profile)
        validate_physical_launch_inputs(Path(request['world_directory']) / 'execution_catalog.json', runtime_scene)
        request['runtime_scene'] = str(runtime_scene)
        request['runtime_scene_sha256'] = hashlib.sha256(runtime_scene.read_bytes()).hexdigest()
    write_once(report_dir / 'request.json', request)
    try:
        execute(request, variant, catalog, report_dir, args.system_id, args.calibration)
    except BaseException as exc:
        if not (report_dir / 'failure.json').exists():
            write_once(report_dir / 'failure.json', dict(error=str(exc), error_type=type(exc).__name__,
                raw_capture_retained=(report_dir / 'capture.json').exists(),
                retry_policy='retain failure; no automatic replacement'))
        raise


if __name__ == '__main__':
    main()
