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
from language_nav.camera_configuration import (capture_source_snapshot, capture_provider_snapshot,
                                               validate_capture_source_freeze)
from language_nav.live import (measured_live_outcome, path_length,
                               terminal_identity_outcome, validate_trajectory_evidence)

ROOT = Path(__file__).resolve().parents[1]
R1 = Path('/home/eao/risk-calibrated-nav')


def write_once(path, payload):
    with Path(path).open('x') as stream:
        json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def prepare(world, variant_id, run_id, domain_id, timeout=180.0, simulation_seed=1, *, heldout_authorization=None):
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
    if heldout_authorization is not None:
        from language_nav.physical_heldout_authorization import authorize
        # Re-admit, rather than trusting a forged or stale in-memory request.
        heldout_authorization = authorize(heldout_authorization.path, heldout_authorization.digest,
                                          heldout_authorization.episode_id)
        row = heldout_authorization.episode
        if (world != (heldout_authorization.root / row['world_directory']).resolve()
                or (variant_id, run_id, domain_id, timeout, simulation_seed) !=
                (row['variant_id'], row['run_id'], heldout_authorization.approval['ros_domain_id'],
                 row['timeout_s'], row['simulation_seed'])):
            raise PermissionError('held-out runtime options differ from authorized episode')
    catalog = validate_physical_launch_inputs(
        world / 'execution_catalog.json', world / 'landmark_scene.yaml', world / 'map.yaml',
        heldout_authorization=heldout_authorization)
    if heldout_authorization is None:
        variants = json.loads((ROOT / 'data/manifests/instruction_benchmark_v0.1.json').read_text())
        variant = next((row for row in variants['deployed_variants'] if row['variant_id'] == variant_id), None)
    else:
        variant = heldout_authorization.episode['instruction']
    if variant is None or any(route.base_instruction_id != variant['base_instruction_id']
                              for route in catalog.semantic.routes):
        raise ValueError('instruction does not belong to physical world')
    absence_path = world / 'absence_intervention.json'
    missing_condition = variant_id == variant['base_instruction_id'] + '-missing_landmark-s0'
    if missing_condition and not absence_path.exists():
        raise ValueError('missing-landmark execution requires a validated physical absence intervention; unchanged worlds are not eligible')
    if absence_path.exists() and not missing_condition:
        raise ValueError('absent-chair world requires missing-landmark instruction condition')
    if catalog.semantic.partition not in {'development', 'validation'} and heldout_authorization is None:
        raise PermissionError('held-out execution is not permitted by this engineering runner')
    request = {
        'schema_version': 'research3-physical-live-request/v1', 'run_id': run_id,
        'world_directory': str(world), 'map_id': catalog.semantic.map_id,
        'partition': 'held_out' if heldout_authorization is not None else catalog.semantic.partition, 'variant_id': variant_id,
        'ros_domain_id': domain_id, 'worker_id': 'research3-' + run_id,
        'protected_test_routes_used': heldout_authorization is not None, 'timeout_s': timeout,
        'simulation_seed': simulation_seed, 'runtime_seed_acceptance_validated': False,
        'evidence_scope': 'physical_world_engineering_not_comparative_campaign',
        'detector_calibration_transfer_validated': False,
        'asset_sha256': (dict(heldout_authorization.episode['asset_sha256']) if heldout_authorization is not None else
                        {name: hashlib.sha256((world / name).read_bytes()).hexdigest()
                         for name in ('world.sdf', 'map.pgm', 'map.yaml',
                                      'execution_catalog.json', 'landmark_scene.yaml',
                                      'manifest.json', 'verified_ordered_geometry.json')}),
    }
    request['source_revision'] = subprocess.check_output(
        ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    request['environment_intervention'] = 'missing_landmark' if missing_condition else 'none'
    if missing_condition:
        request['asset_sha256']['absence_intervention.json'] = hashlib.sha256(absence_path.read_bytes()).hexdigest()
    request['source_sha256'] = capture_source_snapshot()
    request['provider_source_snapshot'] = capture_provider_snapshot()
    if heldout_authorization is not None:
        request.update(heldout_authorization=heldout_authorization.binding(), runtime_partition='test',
                       catalog_partition='held_out',
                       evidence_scope='physical_world_heldout',
                       source_sha256=dict(heldout_authorization.approval['execution_source_sha256']),
                       provider_source_sha256=dict(heldout_authorization.approval['provider_source_sha256']))
    start = catalog.execution[0].start
    request['simulation_launch_argv'] = physical_simulation_command(request, dict(x=start.x, y=start.y, yaw=start.yaw))
    return request, variant, catalog


def overlay_command(request, report_dir, system_id, calibration=None):
    """No evaluator manifest, expected route, or gate annotations enter runtime."""
    world = Path(request['world_directory'])
    command = ['ros2', 'launch', 'language_nav_bringup', 'live_adapters.launch.py',
               f'scene:={request.get("runtime_scene", str(world / "landmark_scene.yaml"))}',
               f'physical_catalog:={world / "execution_catalog.json"}',
               f'partition:={request.get("runtime_partition", request["partition"])}', f'run_id:={request["run_id"]}',
               f'system_id:={system_id}',
               f'research2_output_dir:={report_dir / "research2"}',
               f'research3_output_dir:={report_dir / "research3"}']
    if request.get('heldout_authorization'):
        command[3] = 'heldout_adapters.launch.py'
        binding = request['heldout_authorization']
        command.extend([f'heldout_authorization:={binding["path"]}',
                        f'heldout_authorization_sha256:={binding["sha256"]}',
                        f'heldout_episode_id:={binding["episode_id"]}'])
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
    # A pinned diagnostic derivative replaces only the rendered world file; the
    # deployable catalogue, scene, map and evaluator assets stay the source copies.
    world_sdf = request.get('diagnostic_world_sdf') or str(Path(request["world_directory"]) / "world.sdf")
    command = ['ros2', 'launch', 'language_nav_bringup', 'physical_sim.launch.py',
            f'world_path:={world_sdf}',
            f'simulation_seed:={seed}', f'x_pose:={start["x"]}',
            f'y_pose:={start["y"]}', f'yaw:={start["yaw"]}']
    if request.get('camera_horizontal_fov') is not None:
        command.append(f'camera_horizontal_fov:={request["camera_horizontal_fov"]}')
    return command


def evaluate(request, evidence, *, heldout_context=None):
    """Evaluate retained measurements only after policy execution has finished."""
    world = Path(request['world_directory'])
    protected = request.get('partition') in {'test', 'held_out'} or request.get('protected_test_routes_used') is True
    if protected:
        from language_nav.physical_heldout_authorization import HeldoutEvaluationContext
        if not isinstance(heldout_context, HeldoutEvaluationContext):
            raise PermissionError('protected evaluation requires independently authorized sealed measurements')
        heldout_context.validate(request, evidence)
    for name, digest in request['asset_sha256'].items():
        if hashlib.sha256((world / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'input changed during episode: {name}')
    manifest = json.loads((world / 'manifest.json').read_text())
    geometry = json.loads((world / 'verified_ordered_geometry.json').read_text())
    catalog_partition = request.get('catalog_partition', request['partition']) if protected else request['partition']
    if (manifest['partition'] != catalog_partition or manifest['map_id'] != request['map_id']
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
    if request.get('capture_source_freeze'):
        if request.get('capture_only') is not True:
            raise ValueError('capture source freeze cannot authorize navigation')
        if validate_capture_source_freeze(request['capture_source_freeze'], check_import_resolution=True) != request.get('capture_source_freeze_sha256'):
            raise ValueError('capture source freeze changed before launch')
    heldout = None
    if request.get('partition') in {'test', 'held_out'} or request.get('protected_test_routes_used') is True:
        from language_nav.physical_heldout_authorization import authorize, HeldoutEvaluationContext
        binding = request.get('heldout_authorization', {})
        heldout = authorize(binding['path'], binding['sha256'], binding['episode_id'])
        row = heldout.episode
        if (any(request.get(key) != row.get(key) for key in
                ('run_id', 'map_id', 'variant_id', 'system_id', 'simulation_seed', 'timeout_s', 'asset_sha256',
                 'camera_horizontal_fov', 'camera_color_tolerance'))
                or Path(request['world_directory']).resolve() != (heldout.root / row['world_directory']).resolve()
                or request.get('allow_coexistence_trial') is not False
                or any(request.get(key) for key in ('capture_only', 'capture_perception', 'capture_review',
                                                   'capture_context', 'capture_pose', 'capture_target_categories'))
                or variant != row['instruction']
                or request.get('ros_domain_id') != heldout.approval['ros_domain_id']
                or request.get('worker_id') != 'research3-' + row['run_id']
                or request.get('source_sha256') != heldout.approval['execution_source_sha256']
                or request.get('calibration_sha256') != heldout.approval['calibration']['sha256']
                or Path(calibration).resolve() != (heldout.root / heldout.approval['calibration']['path']).resolve()):
            raise PermissionError('held-out execution differs from authorized navigation-only episode')
        validate_physical_launch_inputs(Path(request['world_directory']) / 'execution_catalog.json',
            Path(request['world_directory']) / 'landmark_scene.yaml', heldout_authorization=heldout)
    from language_nav.live_resources import require_research2_idle, coexistence_headroom
    resource_samples = []
    capture_source_checks = []
    def check_resources():
        if request.get('expansion_instrumentation_snapshot'):
            from snapshot_expansion_instrumentation import validate
            if validate(request['expansion_instrumentation_snapshot']) != request['expansion_instrumentation_sha256']:
                raise ValueError('expansion instrumentation changed during capture')
        if request.get('diagnostic_derivative'):
            if (hashlib.sha256(Path(request['diagnostic_world_sdf']).read_bytes()).hexdigest()
                    != request['diagnostic_derivative']['world_sdf_sha256']):
                raise ValueError('diagnostic derivative world changed during capture')
        if request.get('capture_source_freeze'):
            actual = validate_capture_source_freeze(request['capture_source_freeze'])
            if actual != request.get('capture_source_freeze_sha256'):
                raise ValueError('capture source freeze changed during capture')
            capture_source_checks.append({'monotonic_s': time.monotonic(), 'snapshot_sha256': actual})
        if request.get('allow_coexistence_trial'):
            resource_samples.append(coexistence_headroom())
        else:
            require_research2_idle()
            if heldout is not None:
                resource_samples.append(coexistence_headroom())
    check_resources()
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
    start = request.get('capture_pose') or dict(x=start_pose.x, y=start_pose.y, yaw=start_pose.yaw)
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
        check_resources()
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
            if request.get('expansion_instrumentation_snapshot'):
                from physical_expansion_capture_candidate import ExpansionCaptureCandidate
                recorder = ExpansionCaptureCandidate(report_dir / 'perception_capture', max_frames=1)
            else:
                recorder = PhysicalPerceptionCapture(report_dir / 'perception_capture',
                    observation_triggered=request.get('capture_review', False),
                    capture_categories=request.get('capture_target_categories'),
                    max_frames=request.get('capture_frame_budget', 5))
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
        if request.get('capture_only'):
            check_resources()
            # No instruction, route dispatch or failure-monitor inference. AMCL
            # supplies the ordinary map frame; evaluator truth never replaces it.
            scene=request.get('runtime_scene', str(world/'landmark_scene.yaml'))
            command=['ros2','run','language_nav_bringup','landmark_bridge_runner','--ros-args',
                '-p','use_sim_time:=true','-p',f'scene:={scene}',
                '-p',f'review_log:={report_dir / "landmark_review_tasks.jsonl"}',
                '-p',f'color_tolerance:={request.get("camera_color_tolerance",38.0)}']
            if request.get('expansion_instrumentation_snapshot'):
                command=['python3',str(ROOT/'scripts/physical_expansion_capture_candidate.py'),
                         '--exact-frame-provider',str(report_dir)]+command[4:]
                command+=['-p','rgb_topic:=/r3_expansion_unused/rgb',
                          '-p','depth_topic:=/r3_expansion_unused/depth',
                          '-p','camera_info_topic:=/r3_expansion_unused/info']
            stack.launch('capture_provider',command)
            if request.get('expansion_instrumentation_snapshot'):
                # Readiness uses discovered endpoints, not a successful detection.
                ready_deadline=time.monotonic()+40
                while True:
                    check_resources()
                    ready_topics=all(any(endpoint.node_name=='research3_landmark_bridge'
                        for endpoint in recorder.get_subscriptions_info_by_topic(topic))
                        for topic in ('/r3_expansion_unused/rgb','/r3_expansion_unused/depth','/r3_expansion_unused/info'))
                    provider_pub=any(endpoint.node_name=='research3_landmark_bridge'
                        for endpoint in recorder.get_publishers_info_by_topic('/semantic_observations'))
                    tf_ready=transforms.can_transform('map','base_link',monitor.get_clock().now())
                    provider_tf_ready=(report_dir/'provider_tf_ready.json').exists()
                    if ready_topics and provider_pub and tf_ready and provider_tf_ready and monitor.amcl_converged():break
                    if time.monotonic()>ready_deadline:raise RuntimeError('expansion provider/readiness preflight timed out')
                    if any(proc.poll() is not None for _,proc in stack.procs):raise RuntimeError('stack exited before arming')
                    time.sleep(.1)
                recorder.arm(dict(localization_converged=True,provider_ready=True,transforms_ready=True,
                                  provider_transform_ready=True,
                                  isolated_domain_verified=True,source_snapshot_sha256=request['expansion_instrumentation_sha256']))
            context_recorder = PhysicalPerceptionCapture(report_dir/'context_capture',
                max_frames=request.get('capture_frame_budget',5), interval_s=1.,
                node_name='research3_stationary_context')
            executor.add_node(context_recorder)
            monitor.start()
            deadline=time.monotonic()+request['timeout_s']
            completed_at=None
            while time.monotonic()<deadline:
                check_resources()
                if monitor.snapshot().collision:
                    raise RuntimeError('contact detected during stationary capture')
                processing_done=(not request.get('expansion_instrumentation_snapshot')
                                 or (report_dir/'provider_frame_done.json').exists())
                if recorder.done and context_recorder.done and processing_done:
                    completed_at=completed_at or time.monotonic()
                    if time.monotonic()-completed_at >= 1.:
                        break
                if any(proc.poll() is not None for _,proc in stack.procs):
                    raise RuntimeError('stationary capture stack process exited')
                time.sleep(.25)
            monitor.stop()
            check_resources()
            measurement=monitor.snapshot()
            expansion_result=None
            if request.get('expansion_instrumentation_snapshot'):
                from expansion_sampling import classify_attempt
                recorder.finish()
                frame=recorder.frames[0] if recorder.frames else None
                stamp=frame['rgb_stamp_ns'] if frame else 0
                emitted=recorder.observation_index.get(stamp,{}).get('observations',[])
                normalized=[dict(row,frame_stamp_ns=int(row['observed_at_ns'])) for row in emitted]
                expansion_result=classify_attempt(normalized,frame_stamp_ns=stamp,
                    entity_id=request['capture_target_entity_id'],category=request['capture_target_categories'][0],
                    armed=recorder.armed,frame_present=frame is not None,
                    synchronization_valid=frame is not None and abs(frame['sync_difference_ns'])<=recorder.tolerance_ns,
                    transform_valid=frame is not None and frame['transform_error'] is None,
                    observation_window_complete=completed_at is not None and time.monotonic()-completed_at>=1.,
                    interrupted=False,overflow_count=recorder.observation_overflow,conflict_count=recorder.observation_conflicts,
                    processing_evidence=(json.loads((report_dir/'provider_frame_completion.json').read_bytes())
                        if (report_dir/'provider_frame_done.json').exists() else {'status':'missing'}),
                    frame_sha256=hashlib.sha256((report_dir/'perception_capture/frame-000.json').read_bytes()).hexdigest()
                        if frame else None)
                write_once(report_dir/'expansion_attempt.json',expansion_result)
            write_once(report_dir/'capture_summary.json',dict(
                schema_version='research3-stationary-capture/v1',run_id=request['run_id'],
                motion_commands_sent=False, navigation_episode=False,
                frames_captured=len(recorder.frames), context_frames=len(context_recorder.frames),
                collision_count=measurement.collision_count,
                complete=recorder.done and context_recorder.done,
                human_labels_generated=False, protected_test_routes_used=False,
                capture_source_freeze_sha256=request.get('capture_source_freeze_sha256'),
                capture_source_checks=capture_source_checks,
                capture_source_check_scope='no source change observed at prelaunch and capture-loop checks; not continuous attestation'))
            if expansion_result and expansion_result['status']=='infrastructure_failure':
                raise RuntimeError('expansion evidence incomplete: '+','.join(expansion_result['reasons']))
            return
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
                check_resources()
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
                    'localization_diagnostics': list(monitor.localization_diagnostics),
                    'scan_diagnostics': list(monitor.scan_diagnostics),
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
                if heldout is not None:
                    sealed = report_dir / 'measurements.pre_evaluation.json'
                    write_once(sealed, evidence)
                    heldout_context = HeldoutEvaluationContext(request['run_id'], request['map_id'],
                        dict(request['asset_sha256']), sealed,
                        hashlib.sha256(sealed.read_bytes()).hexdigest(), heldout.digest)
                    summary = evaluate(request, evidence, heldout_context=heldout_context)
                else:
                    summary = evaluate(request, evidence)
                if error is not None:
                    summary.update(navigation_success=False, instruction_completion=None,
                                   semantic_outcome_measured=False, valid_terminal_outcome=False)
                write_once(report_dir / 'measurements.json', evidence)
                summary.update(schema_version='research3-live-summary/v3', run_id=request['run_id'],
                    system_id=system_id, variant_id=variant['variant_id'], partition=request['partition'],
                    protected_test_routes_used=heldout is not None, route_id=evidence['selected_route_id'],
                    detector_calibration_transfer_validated=False,
                    evidence_scope=request['evidence_scope'],
                    measurements_sha256=hashlib.sha256((report_dir / 'measurements.json').read_bytes()).hexdigest(),
                    episode_started_at_ns=monitor.started_ns, episode_ended_at_ns=monitor.ended_ns,
                    episode_prediction_count=len(predictions), collision_count=measurement.collision_count,
                    infrastructure_failure=error is not None,
                    reason=str(error) if error else (outcome.reason if outcome else 'collision or timeout'))
                if heldout is not None:
                    summary.update(map_id=request['map_id'], runtime_partition='test', catalog_partition='held_out',
                        pre_evaluation_measurements_sha256=heldout_context.sealed_measurements_sha256)
                write_once(report_dir / 'summary.json', summary)
            if error is not None:
                write_once(report_dir / 'failure.json', dict(error=str(error), error_type=type(error).__name__,
                           dispatched=started, retry_policy='retain failure; no automatic replacement'))
        finally:
            # Stack owns only descendants launched by this run; never broad pkill.
            write_once(report_dir / 'resource_guard.json', dict(samples=resource_samples,
                coexistence_trial=request.get('allow_coexistence_trial', False),
                gpu_headroom_verified=False, research2_performance_unchanged_proven=False))
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
    parser.add_argument('--allow-coexistence-trial', action='store_true',
                        help='explicit user-authorized development trial, <=120 seconds, resource guarded')
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
    parser.add_argument('--capture-only', action='store_true', help='stationary image collection; no instruction or navigation dispatch')
    parser.add_argument('--capture-source-freeze', type=Path,
                        help='optional exact current R3/provider source binding for new stationary captures')
    parser.add_argument('--expansion-instrumentation-snapshot',type=Path,
                        help='explicit approved-scope source pin for development expansion preflight')
    parser.add_argument('--capture-entity-id',help='exact prespecified stable entity for expansion capture')
    parser.add_argument('--development-complete-report',type=Path,
                        help='complete development expansion collection report; required before validation expansion capture')
    parser.add_argument('--diagnostic-derivative',type=Path,
                        help='pinned diagnostic candidate world directory; renders its world.sdf over unchanged source assets')
    parser.add_argument('--diagnostic-asset-decision',type=Path,
                        help='human rendered-asset decision; required for diagnostic expansion collection, not for rendering')
    parser.add_argument('--capture-pose', type=float, nargs=3, metavar=('X','Y','YAW'))
    parser.add_argument('--capture-frame-budget', type=int, default=5)
    parser.add_argument('--capture-target-category', action='append',
                        choices=('chair','doorway','laboratory_entrance','office_entrance'),
                        help='stationary capture frame trigger only; retains all observations in selected frames')
    parser.add_argument('--camera-profile', type=Path, help='explicit development camera palette, not calibration')
    parser.add_argument('--camera-settings-freeze', type=Path,
                        help='hash-bound engineering settings required for validation stationary capture')
    parser.add_argument('--camera-horizontal-fov', type=float,
                        help='development-only matched RGB/depth wider-context capture, radians')
    args = parser.parse_args()
    request, variant, catalog = prepare(args.world, args.variant_id, args.run_id, args.ros_domain_id,
                                        args.timeout, args.simulation_seed)
    request['system_id'] = args.system_id
    if not 1 <= args.capture_frame_budget <= 20:
        parser.error('capture frame budget must be 1..20')
    request['capture_frame_budget']=args.capture_frame_budget
    request['capture_only']=args.capture_only
    if args.diagnostic_derivative:
        derivative=args.diagnostic_derivative.resolve()
        if (not args.capture_only or request['partition']!='development' or args.capture_pose is None
                or len(args.capture_target_category or [])!=1 or args.capture_source_freeze
                or not args.run_id.startswith('expansion-diag-')):
            parser.error('diagnostic derivative capture requires development stationary one-target capture and an expansion-diag- run ID')
        assets=re.fullmatch(r'calibration_expansion_(occluder|distractor)_assets_\d{8}_v\d+',derivative.parent.name)
        family={'occluder':'occluder','distractor':'sphere'}[assets[1]] if assets else None
        if family is None or derivative.parent.parent!=(ROOT/'reports').resolve():
            parser.error('diagnostic derivative must be a pinned candidate asset directory')
        if assets.group(0).endswith('_v1'):
            from audit_expansion_diagnostics import check as check_diagnostic_candidate
            audit_name='occluder_candidate_audit.json' if family=='occluder' else 'diagnostic_asset_audit.json'
        else:
            from audit_expansion_diagnostics_v2 import check as check_diagnostic_candidate
            audit_name='diagnostic_candidate_audit_v2.json'
        audit_row=check_diagnostic_candidate(derivative,family=='occluder')
        if audit_row['static_issues']:
            parser.error('diagnostic derivative has unresolved static issues')
        match=re.fullmatch(r'expansion-v1-r(0\d\d)-(chair|doorway|laboratory_entrance|office_entrance)-s1-view0',derivative.name)
        if (args.world.resolve()!=(ROOT/'data/physical_worlds_readable_v1'/('base-r'+match[1])).resolve()
                or args.capture_target_category[0]!=match[2]):
            parser.error('diagnostic derivative source world/category mismatch')
        audit=json.loads((derivative/audit_name).read_bytes())
        if (any(not math.isclose(audit['capture_pose'][key],value,abs_tol=1e-12) for key,value in zip(('x','y','yaw'),args.capture_pose))
                or (args.capture_entity_id and audit['entity_id']!=args.capture_entity_id)):
            parser.error('diagnostic derivative pose/entity differs from bound candidate')
        request['diagnostic_world_sdf']=str(derivative/'world.sdf')
        request['diagnostic_derivative']=dict(candidate_id=derivative.name,treatment=family,directory=str(derivative),
            world_sdf_sha256=audit['derivative_sha256']['world.sdf'],audit_sha256=audit_row['audit_sha256'],
            entity_id=audit['entity_id'],panel='diagnostic_only',included_in_primary_calibration=False)
        if args.expansion_instrumentation_snapshot:
            if not args.diagnostic_asset_decision:
                parser.error('diagnostic expansion collection requires the human rendered-asset decision')
            from render_expansion_diagnostics import validate_asset_decision
            request['diagnostic_asset_decision']=str(args.diagnostic_asset_decision.resolve())
            request['diagnostic_asset_decision_sha256']=validate_asset_decision(
                args.diagnostic_asset_decision,candidate_id=derivative.name,treatment=family)
    elif args.diagnostic_asset_decision:
        parser.error('asset decision applies only to diagnostic derivative capture')
    if args.expansion_instrumentation_snapshot:
        from snapshot_expansion_instrumentation import validate
        if (not args.capture_only or request['partition'] not in ('development','validation') or args.capture_source_freeze
                or args.capture_frame_budget!=1 or len(args.capture_target_category or [])!=1
                or not args.capture_entity_id or args.capture_pose is None):
            parser.error('expansion capture requires non-protected one-frame exact-target capture and its own source pin')
        if request['partition']=='validation':
            if args.development_complete_report is None or args.camera_settings_freeze is None or args.diagnostic_derivative:
                parser.error('validation expansion capture requires the complete development collection report and a bound per-view camera freeze')
            from run_expansion_collection import validate_development_complete_report
            request['development_complete_report']=str(args.development_complete_report.resolve())
            request['development_complete_report_sha256']=validate_development_complete_report(args.development_complete_report)
        elif args.development_complete_report is not None:
            parser.error('development collection report applies only to validation expansion capture')
        import yaml
        entities=yaml.safe_load((args.world/'landmark_scene.yaml').read_bytes())['entities']
        if len([e for e in entities if e['entity_id']==args.capture_entity_id and e['category']==args.capture_target_category[0]])!=1:
            parser.error('expansion target must match an exact scene entity/category')
        request['expansion_instrumentation_snapshot']=str(args.expansion_instrumentation_snapshot.resolve())
        request['expansion_instrumentation_sha256']=validate(args.expansion_instrumentation_snapshot)
        request['capture_target_entity_id']=args.capture_entity_id
    elif args.capture_entity_id or args.development_complete_report:
        parser.error('capture entity selection and development completion evidence require explicit expansion instrumentation')
    if args.capture_source_freeze:
        if not args.capture_only:
            parser.error('capture source freeze requires stationary capture-only mode')
        request['capture_source_freeze_sha256'] = validate_capture_source_freeze(args.capture_source_freeze)
        request['capture_source_freeze'] = str(args.capture_source_freeze.resolve())
        frozen_source = json.loads(args.capture_source_freeze.read_text())
        if (request['source_sha256'] != frozen_source['source_sha256']
                or request['provider_source_snapshot'] != frozen_source['provider_source_snapshot']):
            raise ValueError('request sources differ from capture source freeze')
    if args.capture_target_category and not args.capture_only:
        parser.error('target category filtering requires stationary capture-only mode')
    request['capture_target_categories']=args.capture_target_category
    if args.capture_pose is not None:
        if not args.capture_only:
            parser.error('capture pose override cannot change a navigation episode')
        from language_nav.capture_view import validate_capture_pose
        request['capture_pose']=validate_capture_pose(args.world,*args.capture_pose)
    if args.capture_only:
        request['evidence_scope']='stationary_development_validation_detector_capture_not_navigation'
    frozen_stationary = False
    if args.camera_settings_freeze:
        if not args.capture_only or not args.camera_profile:
            parser.error('engineering camera freeze requires stationary capture and explicit profile')
        from language_nav.camera_configuration import validate_camera_freeze
        request['camera_settings_freeze_sha256'] = validate_camera_freeze(
            args.camera_settings_freeze, map_id=request['map_id'],
            profile=args.camera_profile, horizontal_fov=args.camera_horizontal_fov)
        frozen_stationary = True
    if request['partition'] == 'validation' and args.capture_only and not frozen_stationary:
        parser.error('validation stationary capture requires frozen engineering camera settings')
    if request['partition'] == 'validation' and args.capture_only:
        from language_nav.camera_configuration import validate_frozen_capture_view
        if not request.get('capture_pose') or len(args.capture_target_category or []) != 1:
            parser.error('validation stationary capture requires one frozen target category and explicit pose')
        validate_frozen_capture_view(args.camera_settings_freeze, map_id=request['map_id'],
            category=args.capture_target_category[0], pose=request['capture_pose'], world=args.world)
    if args.camera_horizontal_fov is not None:
        if ((request['partition'] != 'development' and not frozen_stationary) or not math.isfinite(args.camera_horizontal_fov)
                or not .5 <= args.camera_horizontal_fov <= 2.0):
            parser.error('camera FOV override requires development or frozen stationary settings and 0.5..2.0 radians')
        request['camera_horizontal_fov'] = args.camera_horizontal_fov
        start = catalog.execution[0].start
        request['simulation_launch_argv'] = physical_simulation_command(request, dict(x=start.x,y=start.y,yaw=start.yaw))
    if args.allow_coexistence_trial and ((request['partition'] != 'development' and not frozen_stationary) or args.timeout > 120):
        parser.error('coexistence trial requires development or frozen stationary capture and timeout <=120 seconds')
    request['allow_coexistence_trial'] = args.allow_coexistence_trial
    request['capture_perception'] = args.capture_perception or args.capture_review or args.capture_only
    request['capture_review'] = args.capture_review or args.capture_only
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
    if args.capture_only:
        start=request.get('capture_pose') or dict(x=catalog.execution[0].start.x,y=catalog.execution[0].start.y,yaw=catalog.execution[0].start.yaw)
        request['simulation_launch_argv']=physical_simulation_command(request,start)
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
