"""Source-bound stationary Wave S capture driver; no route or motion dispatch.

The production entry accepts only the approved S schedule and separately bound
execution authority. The explicit preflight entry uses four fixed r001 poses,
seed 29, and cannot produce primary-wave evidence.
"""
import argparse
import json
import math
import os
from pathlib import Path
import threading
import time

from joint_score_collection import OneFrameAttempt, write_once
from joint_score_wave_s_admission import admitted_attempt
from language_nav.live_resources import coexistence_headroom
from prepare_joint_score_protocol import ROOT, sha


def remaining(attempt):
    attempt.advance(time.monotonic())
    if attempt.closed:
        raise TimeoutError('launch-inclusive 90-second capture deadline')
    return max(.001, attempt.deadline-time.monotonic())


def verify_inputs(config):
    for path, expected in config['input_sha256'].items():
        if sha(path) != expected:
            raise ValueError('changed execution input: '+path)


def capture(attempt, slot, config, *, preflight=False):
    """Same capture implementation for preflight and primary; only identity/seed differ."""
    verify_inputs(config)
    if slot['partition'] != 'development' or slot['wave'] != 'S':
        raise PermissionError('only development Wave S')
    world = (ROOT/slot['world_directory']).resolve()
    if str(world/'world.sdf') not in config['input_sha256']:
        raise ValueError('world not in execution snapshot')
    worker = 'r3-jsc-'+attempt.capture_uuid
    os.environ.update(ROS_DOMAIN_ID=str(config['ros_domain_id']), RCN_WORKER_ID=worker,
                      GZ_PARTITION=worker, IGN_PARTITION=worker,
                      ROS_AUTOMATIC_DISCOVERY_RANGE='LOCALHOST',
                      ROS_LOG_DIR=str(attempt.output/'ros_logs'),
                      R3_POSE_BOUND_RUN=str(attempt.output.resolve()))
    for name in ('robot.sdf', 'robot.urdf', 'bridge.yaml'):
        with (attempt.output/name).open('xb') as stream:
            stream.write(Path(config['assets'][name]).read_bytes())
    pins = dict(config['input_sha256'])
    pins.update({str((attempt.output/n).resolve()): sha(attempt.output/n)
                 for n in ('robot.sdf', 'robot.urdf', 'bridge.yaml')})
    write_once(attempt.output/'plan.json', dict(partition='development', capture_pose=slot['capture_pose'],
        seed=29 if preflight else slot['seed'], world=str(world/'world.sdf'), input_sha256=pins,
        nominal_mount=config['nominal_mount'], rendered_mount=config['rendered_mount'],
        preflight_only=preflight, primary_eligible=not preflight))
    import rclpy
    from rclpy.node import Node
    from rclpy.action import ActionClient
    from rclpy.executors import SingleThreadedExecutor
    from geometry_msgs.msg import PoseWithCovarianceStamped
    from nav2_msgs.action import NavigateToPose
    from run_live_episode import (Stack, TimestampedEpisodeMonitor, HAVE_CONTACTS,
        preflight as sensor_preflight, nav2_bringup_ready, write_episode_params, load_system_config)
    from joint_score_ros_capture import JointScoreCapture
    if not HAVE_CONTACTS:
        raise RuntimeError('contact transport unavailable')
    stack = Stack(attempt.output/'logs')
    monitor = recorder = executor = thread = None
    stop = threading.Event()
    failure = None
    rclpy.init(args=[])
    try:
        probe = Node('research3_jsc_domain_probe')
        try:
            end = time.monotonic()+min(2., remaining(attempt))
            while time.monotonic() < end:
                rclpy.spin_once(probe, timeout_sec=.05)
            if any(n != probe.get_name() for n in probe.get_node_names()):
                raise RuntimeError('DDS domain occupied; no simulator launched')
        finally:
            probe.destroy_node()
        coexistence_headroom(); remaining(attempt)
        stack.launch('sim', ['ros2', 'launch', str(ROOT/'scripts/bound_pose_sim.launch.py')])
        attempt.event('simulator_started', time.monotonic(), worker_id=worker)
        ready = sensor_preflight.wait_until_ready(
            {**sensor_preflight.MANDATORY, **sensor_preflight.EVALUATION_ONLY},
            timeout_s=min(25., remaining(attempt)))
        if not ready.ok:
            raise RuntimeError(ready.summary())
        pose = slot['capture_pose']
        r1 = Path('/home/eao/risk-calibrated-nav')
        params = write_episode_params(r1/'configs/nav2/nav2_common.yaml', attempt.output/'nav2_params.yaml',
            pose['x'], pose['y'], pose['yaw'], load_system_config(r1/'configs/systems/s0.yaml'))
        stack.launch('nav2', ['ros2', 'launch', 'simulation_worlds', 'nav2.launch.py',
            f'map:={world/"map.yaml"}', f'params_file:={params}'])
        monitor = TimestampedEpisodeMonitor(perception_enabled=False)
        executor = SingleThreadedExecutor(); executor.add_node(monitor)
        def spin_setup():
            while not stop.is_set():
                executor.spin_once(timeout_sec=.05)
        thread = threading.Thread(target=spin_setup, daemon=True); thread.start()
        # The helper has three sequential bounded stages. Their sum cannot extend
        # the capture budget; there is no Nav2 restart/retry.
        client = ActionClient(monitor, NavigateToPose, 'navigate_to_pose')
        problem = nav2_bringup_ready(client, monitor, remaining(attempt)/3.)
        if problem:
            raise RuntimeError(problem)
        initial = PoseWithCovarianceStamped(); initial.header.frame_id = 'map'
        initial.pose.pose.position.x, initial.pose.pose.position.y = pose['x'], pose['y']
        initial.pose.pose.orientation.z = math.sin(pose['yaw']/2)
        initial.pose.pose.orientation.w = math.cos(pose['yaw']/2)
        initial.pose.covariance[0] = initial.pose.covariance[7] = .25
        initial.pose.covariance[35] = .068
        pub = monitor.create_publisher(PoseWithCovarianceStamped, '/initialpose', 10)
        while not monitor.amcl_converged():
            remaining(attempt); coexistence_headroom()
            initial.header.stamp = monitor.get_clock().now().to_msg(); pub.publish(initial)
            time.sleep(.1)
        if monitor.spawned_in_collision():
            raise RuntimeError('contact at stationary spawn')
        settled = monitor.get_clock().now().nanoseconds+3_000_000_000
        while monitor.get_clock().now().nanoseconds < settled:
            remaining(attempt); time.sleep(.05)
        attempt.event('localization_ready', time.monotonic(),
                      ground_truth_use='readiness check only; never measurement input',
                      amcl_converged=monitor.amcl_converged(), no_spawn_contact=True)
        stop.set(); thread.join(timeout=2.)
        if thread.is_alive():
            raise RuntimeError('setup executor did not stop')
        executor.remove_node(monitor); executor.shutdown(); executor = SingleThreadedExecutor()
        executor.add_node(monitor)
        remaining(attempt)
        recorder = JointScoreCapture(attempt); executor.add_node(recorder)
        monitor.start()
        while not attempt.closed:
            executor.spin_once(timeout_sec=.05)
            if monitor.snapshot().collision:
                attempt.close(time.monotonic(), 'infrastructure_failure', 'contact_during_capture')
            if any(p.poll() is not None for _, p in stack.procs):
                attempt.close(time.monotonic(), 'infrastructure_failure', 'stack_exited_during_capture')
        verify_inputs(config)
    except Exception as exc:
        failure = repr(exc)
        if not attempt.closed:
            attempt.close(time.monotonic(), 'infrastructure_failure', failure)
    finally:
        stop.set()
        if thread:
            thread.join(timeout=2.)
        if recorder:
            recorder.finish()
        if executor:
            executor.shutdown()
        if recorder:
            recorder.destroy_node()
        if monitor:
            monitor.destroy_node()
        cleanup = stack.shutdown()
        rclpy.shutdown()
        write_once(attempt.output/'execution.json', dict(preflight_only=preflight,
            failure=failure, cleanup=cleanup, owned_launch_pids=[p.pid for _, p in stack.procs],
            owned_launches_exited=all(p.poll() is not None for _, p in stack.procs),
            motion_dispatched=False, source_checked_after_capture=failure is None))
    return json.loads((attempt.output/'summary.json').read_text())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=('preflight', 'attempt'))
    p.add_argument('--config', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--attempt-id')
    p.add_argument('--execution-manifest', type=Path)
    p.add_argument('--execution-approval', type=Path)
    args = p.parse_args()
    os.nice(19)
    config = json.loads(args.config.read_text()); verify_inputs(config)
    packet = ROOT/'reports/joint_score_protocol_20260924_v1'
    schedule = json.loads((packet/'schedule.json').read_text())
    if args.mode == 'preflight':
        # Exactly four fixed frontal views; selected before this driver sees pixels.
        slots = [r for r in schedule['rows'] if r['wave'] == 'S' and r['map_id'] == 'r3geo_base_r001'
                 and r['seed'] == 101 and r['view'] == 0]
        if len(slots) != 4:
            raise ValueError('fixed four-view preflight schedule')
        args.output.mkdir(exist_ok=False)
        write_once(args.output/'schedule.json', dict(slots=slots, seed=29, primary_eligible=False))
        results = []
        for i, original in enumerate(slots):
            slot = dict(original, attempt_id='preflight-'+original['acquisition_class'])
            coexistence_headroom()
            attempt = OneFrameAttempt(args.output/f'view-{i:02}', slot['attempt_id'], time.monotonic())
            results.append(capture(attempt, slot, config, preflight=True))
            print(slot['attempt_id'], results[-1]['status'], flush=True)
        write_once(args.output/'capture_audit.json', dict(rows=results, primary_eligible=False,
            transport_passed=all(r['status'] == 'captured' for r in results),
            config_sha256=sha(args.config), no_model_outcomes_used_for_capture=True))
    else:
        if not all((args.attempt_id, args.execution_manifest, args.execution_approval)):
            p.error('attempt mode requires exact attempt and manifest-bound execution approval')
        manifest = json.loads(args.execution_manifest.read_text())
        if manifest['input_sha256'].get(str(args.config.resolve())) != sha(args.config):
            raise ValueError('driver config must be pinned by execution manifest')
        with admitted_attempt(attempt_id=args.attempt_id, output_root=args.output,
            schedule_path=packet/'schedule.json', protocol_path=ROOT/'docs/SCORE_LEARNING_COLLECTION_PROTOCOL_20260924.md',
            protocol_review_path=packet/'review_decision_CONVERSATION_FINAL.json',
            execution_manifest_path=args.execution_manifest, execution_approval_path=args.execution_approval) as (attempt, slot):
            print(json.dumps(capture(attempt, slot, config), indent=2))


if __name__ == '__main__':
    main()
