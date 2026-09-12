#!/usr/bin/env python3
"""Validate a new world with an evaluator-selected Nav2 goal, not language policy."""
import argparse
import json
import math
import os
from pathlib import Path
import threading
import time

import rclpy
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
from tf2_ros import Buffer, TransformListener

from episode_logger.monitor import EpisodeMonitor
from experiment_controller import preflight
from experiment_controller.run_episode import (Stack, simulation_launch_command, load_system_config,
    write_episode_params, nav2_bringup_ready, shutdown_nav2_lifecycle)
from language_nav.evaluation.ordered import score_ordered_instruction
from language_nav.live import terminal_identity_outcome

ROOT=Path(__file__).resolve().parents[1]
R1=Path('/home/eao/risk-calibrated-nav')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--world',type=Path,required=True)
    p.add_argument('--run-id',required=True)
    p.add_argument('--candidate',default='expected')
    p.add_argument('--timeout',type=float,default=180)
    args=p.parse_args()
    manifest=json.loads((args.world/'manifest.json').read_text())
    if manifest['partition']=='held_out':
        raise SystemExit('this engineering validator does not execute held-out routes')
    annotation=json.loads((args.world/'verified_ordered_geometry.json').read_text())
    selected=manifest['expected_route_id'] if args.candidate=='expected' else args.candidate
    candidate=next(c for c in manifest['candidates'] if c['route_id']==selected)
    target=next(c for c in manifest['candidates'] if c['route_id']==manifest['expected_route_id'])
    report_dir=ROOT/'reports/physical_navigation'/args.run_id
    report_dir.mkdir(parents=True,exist_ok=False)
    os.environ['RCN_WORKER_ID']=args.run_id
    stack=Stack(report_dir/'logs')
    monitor=executor=thread=None
    report={'schema_version':'research3-physical-navigation-validation/v1','passed':False,
            'evidence_scope':'reference_navigation_geometry_validation_not_language_policy',
            'protected_test_routes_used':False,'world_sha256':manifest['world_sha256'],
            'map_sha256':manifest['map_sha256'],'candidate_route_id':selected}
    try:
        rclpy.init()
        stack.launch('sim',simulation_launch_command('dev_00',manifest['start'],args.world/'world.sdf'))
        ready=preflight.wait_until_ready({**preflight.MANDATORY,**preflight.EVALUATION_ONLY},timeout_s=90)
        if not ready.ok:
            raise RuntimeError(ready.summary())
        params=write_episode_params(R1/'configs/nav2/nav2_common.yaml',report_dir/'nav2_params.yaml',
             float(manifest['start']['x']),float(manifest['start']['y']),float(manifest['start']['yaw']),
             load_system_config(R1/'configs/systems/s0.yaml'))
        stack.launch('nav2',['ros2','launch','simulation_worlds','nav2.launch.py',
                            f'map:={(args.world / "map.yaml").resolve()}',f'params_file:={params}'])
        monitor=EpisodeMonitor()
        transforms=Buffer()
        listener=TransformListener(transforms,monitor)
        executor=MultiThreadedExecutor(num_threads=3)
        executor.add_node(monitor)
        thread=threading.Thread(target=executor.spin,daemon=True)
        thread.start()
        client=ActionClient(monitor,NavigateToPose,'navigate_to_pose')
        problem=nav2_bringup_ready(client,monitor,90)
        if problem:
            raise RuntimeError(problem)
        initial=PoseWithCovarianceStamped()
        initial.header.frame_id='map'
        initial.pose.pose.position.x=float(manifest['start']['x'])
        initial.pose.pose.position.y=float(manifest['start']['y'])
        initial.pose.pose.orientation.w=1.
        initial.pose.covariance[0]=initial.pose.covariance[7]=.25
        initial.pose.covariance[35]=.068
        pub=monitor.create_publisher(PoseWithCovarianceStamped,'/initialpose',10)
        deadline=time.monotonic()+60
        while not monitor.amcl_converged() and time.monotonic()<deadline:
            initial.header.stamp=monitor.get_clock().now().to_msg()
            pub.publish(initial)
            time.sleep(.5)
        if not monitor.amcl_converged() or monitor.spawned_in_collision():
            raise RuntimeError('invalid initial localization/contact state')
        # The provider switches Nav2 from wall time to simulation time at activation.
        # AMCL's future-dated first transform is not yet a usable history window.
        deadline=time.monotonic()+15
        settled_after_ns=monitor.get_clock().now().nanoseconds+3_000_000_000
        while (monitor.get_clock().now().nanoseconds<settled_after_ns
               or not transforms.can_transform('map','base_link',monitor.get_clock().now())):
            if time.monotonic()>deadline:
                raise RuntimeError('map/base transform did not settle after clock switch')
            time.sleep(.1)
        goal=NavigateToPose.Goal()
        goal.pose.header.frame_id='map'
        goal.pose.header.stamp=monitor.get_clock().now().to_msg()
        goal.pose.pose.position.x=candidate['goal']['x']
        goal.pose.pose.position.y=candidate['goal']['y']
        goal.pose.pose.orientation.z=math.sin(candidate['goal']['yaw']/2)
        goal.pose.pose.orientation.w=math.cos(candidate['goal']['yaw']/2)
        monitor.start()
        future=client.send_goal_async(goal)
        deadline=time.monotonic()+args.timeout
        while not future.done() and time.monotonic()<deadline:
            time.sleep(.05)
        if not future.done() or not future.result().accepted:
            raise RuntimeError('reference goal not accepted')
        handle=future.result()
        result=handle.get_result_async()
        last_count=monitor.snapshot().gt_count
        last_progress=time.monotonic()
        while not result.done() and time.monotonic()<deadline and not monitor.snapshot().collision:
            count=monitor.snapshot().gt_count
            if count!=last_count:
                last_count,last_progress=count,time.monotonic()
            elif time.monotonic()-last_progress>10:
                raise RuntimeError('simulator ground-truth heartbeat lost during reference trial')
            time.sleep(.05)
        timed_out=not result.done() and not monitor.snapshot().collision
        if not result.done():
            handle.cancel_goal_async()
        monitor.stop()
        m=monitor.snapshot()
        terminal=terminal_identity_outcome(m.gt_positions,manifest['terminal_entities'],
                                           target['terminal_entity_id']+'_region',radius_m=1.)
        candidate_terminal=terminal_identity_outcome(m.gt_positions,manifest['terminal_entities'],
                                           candidate['terminal_entity_id']+'_region',radius_m=1.)
        score=score_ordered_instruction(m.gt_positions,annotation,
            terminal_identity_correct=terminal['terminal_identity_correct'],collision=m.collision,timeout=timed_out)
        nav_success=bool(result.done() and result.result().status==4)
        goal_error=monitor.distance_to(candidate['goal']['x'],candidate['goal']['y'])
        expected=selected==manifest['expected_route_id']
        report.update(nav2_success=nav_success,goal_error_m=goal_error,collision=m.collision,
                      collision_count=m.collision_count,timeout=timed_out,
                      distance_travelled_m=m.path_length_m,ground_truth_positions=m.gt_positions,
                      terminal_identity=terminal,ordered_score=score,
                      point_goal_accuracy_passed=bool(nav_success and goal_error<=.35),
                      validation_criterion='ordered passage and entrance proximity; waypoint accuracy reported separately',
                      passed=bool(nav_success and candidate_terminal['terminal_identity_correct'] is True and not m.collision
                                  and score['instruction_completion'] is expected))
        if not report['passed']:
            raise RuntimeError('reference geometry validation did not pass')
    except BaseException as exc:
        report['error']=str(exc)
        report['error_type']=type(exc).__name__
        raise
    finally:
        if monitor is not None and 'ground_truth_positions' not in report:
            monitor.stop()
            m=monitor.snapshot()
            report.update(ground_truth_positions=m.gt_positions,collision=m.collision,
                          collision_count=m.collision_count,distance_travelled_m=m.path_length_m)
        # Persist before teardown: an interrupted ROS service shutdown must never
        # erase the measurement record collected above.
        with (report_dir/'report.json').open('x') as stream:
            json.dump(report,stream,indent=2,sort_keys=True)
            stream.write('\n')
        print(json.dumps({k:v for k,v in report.items() if k!='ground_truth_positions'}),flush=True)
        if monitor is not None and rclpy.ok():
            shutdown_nav2_lifecycle(monitor,20)
        stack.shutdown()
        if executor is not None:
            executor.shutdown()
        if monitor is not None:
            monitor.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        if thread is not None:
            thread.join(timeout=2)


if __name__=='__main__':
    main()
