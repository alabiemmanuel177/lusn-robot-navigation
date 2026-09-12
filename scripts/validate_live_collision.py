#!/usr/bin/env python3
"""Deliberate simulation-only obstacle contact; isolated from navigation campaigns."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import threading
import time
import xml.etree.ElementTree as ET

import rclpy
from geometry_msgs.msg import Twist
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import qos_profile_sensor_data
from ros_gz_interfaces.msg import Contacts
from episode_logger.monitor import EpisodeMonitor
from experiment_controller.run_episode import Stack, simulation_launch_command
from rcn.collisions import RAW_CONTACT_TOPICS, disqualifying_pairs

ROOT = Path(__file__).resolve().parents[1]
R1 = Path('/home/eao/risk-calibrated-nav')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    output = ROOT / 'reports/collision_validation' / args.run_id
    output.mkdir(parents=True, exist_ok=False)
    os.environ['RCN_WORKER_ID'] = args.run_id
    base = subprocess.check_output(['xacro', str(R1 / 'src/simulation_worlds/worlds/dev_00.sdf.xacro'),
                                    'headless:=true'], text=True)
    tree = ET.fromstring(base)
    obstacle = ET.fromstring("""<model name="r3_collision_fixture"><static>true</static>
      <pose>-1.25 -0.5 0.4 0 0 0</pose><link name="obstacle">
      <collision name="collision"><geometry><box><size>0.2 1.0 0.8</size></box></geometry></collision>
      <visual name="visual"><geometry><box><size>0.2 1.0 0.8</size></box></geometry></visual>
      </link></model>""")
    tree.find('world').append(obstacle)
    world = output / 'fixture.sdf'
    ET.ElementTree(tree).write(world, encoding='unicode')
    stack = Stack(output / 'logs')
    node = executor = thread = None
    report = {'schema_version': 'research3-live-collision-validation/v1', 'passed': False,
              'simulation_only': True, 'research_performance_evidence': False,
              'protected_test_routes_used': False, 'raw_disqualifying_pairs': []}
    try:
        rclpy.init()
        stack.launch('sim', simulation_launch_command('dev_00', {'x': -2.0, 'y': -0.5, 'yaw': 0}, world))
        node = EpisodeMonitor()
        commands = node.create_publisher(Twist, '/cmd_vel', 10)
        pairs = report['raw_disqualifying_pairs']
        subscriptions = [node.create_subscription(Contacts, topic,
            lambda msg: pairs.extend(disqualifying_pairs(msg.contacts)), qos_profile_sensor_data)
            for topic in RAW_CONTACT_TOPICS]
        executor = MultiThreadedExecutor(num_threads=2)
        executor.add_node(node)
        thread = threading.Thread(target=executor.spin, daemon=True)
        thread.start()
        deadline = time.monotonic() + 90
        while node.snapshot().gt_count < 5 and time.monotonic() < deadline:
            time.sleep(0.1)
        if node.snapshot().gt_count < 5:
            raise RuntimeError('ground-truth stream did not start')
        if node.spawned_in_collision():
            raise RuntimeError('unexpected spawn collision')
        pairs.clear()
        node.start()
        deadline = time.monotonic() + 20
        move = Twist()
        move.linear.x = 0.15
        while time.monotonic() < deadline and not node.snapshot().collision:
            commands.publish(move)
            time.sleep(0.05)
        commands.publish(Twist())
        time.sleep(0.2)
        node.stop()
        measurements = node.snapshot()
        report.update(collision=measurements.collision, collision_count=measurements.collision_count,
                      distance_travelled_m=measurements.path_length_m,
                      ground_truth_positions=measurements.gt_positions)
        report['passed'] = bool(measurements.collision and measurements.collision_count > 0
                                and any('r3_collision_fixture' in str(pair) for pair in pairs))
        if not report['passed']:
            raise RuntimeError('no measured robot/fixture contact within deadline')
    except Exception as exc:
        report['error'] = str(exc)
        raise
    finally:
        if node is not None:
            commands.publish(Twist())
        stack.shutdown()
        if executor is not None:
            executor.shutdown()
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        if thread is not None:
            thread.join(timeout=2)
        with (output / 'report.json').open('x') as stream:
            json.dump(report, stream, indent=2, sort_keys=True)
            stream.write('\n')
        print(json.dumps({k: v for k, v in report.items() if k not in {'ground_truth_positions', 'raw_disqualifying_pairs'}}))


if __name__ == '__main__':
    main()
