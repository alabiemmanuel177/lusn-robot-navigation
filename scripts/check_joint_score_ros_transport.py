"""Bounded synthetic ROS transport check, no Gazebo, labels, motion or Wave S.

Use only on an isolated localhost ROS domain. Writes diagnostic evidence once.
"""
import argparse
import json
import os
from pathlib import Path
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--domain-id', required=True, type=int)
    args = parser.parse_args()
    if not 200 <= args.domain_id <= 230:
        raise ValueError('dedicated diagnostic domain in 200..230 required')
    # Inspect only ROS domain settings, never print full process environments.
    for process in Path('/proc').iterdir():
        if not process.name.isdigit() or int(process.name) == os.getpid():
            continue
        try:
            entries = (process/'environ').read_bytes().split(b'\0')
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        if f'ROS_DOMAIN_ID={args.domain_id}'.encode() in entries:
            raise RuntimeError('diagnostic ROS domain already in use')
    os.environ['ROS_DOMAIN_ID'] = str(args.domain_id)
    os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE'] = 'LOCALHOST'
    os.environ['ROS_LOG_DIR'] = str(args.output/'ros_logs')
    os.nice(19)
    from joint_score_collection import OneFrameAttempt, write_once
    from language_nav.live_resources import coexistence_headroom
    coexistence_headroom()
    attempt = OneFrameAttempt(args.output, 'synthetic-transport-preflight-not-wave-s', time.monotonic())
    import rclpy
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import Image, CameraInfo
    from rosgraph_msgs.msg import Clock
    from geometry_msgs.msg import TransformStamped
    from tf2_ros import TransformBroadcaster
    from joint_score_ros_capture import JointScoreCapture
    rclpy.init(args=[])
    source = capture = executor = None
    try:
        source = rclpy.create_node('research3_synthetic_transport_source')
        capture = JointScoreCapture(attempt)
        executor = SingleThreadedExecutor()
        executor.add_node(source); executor.add_node(capture)
        clock_pub = source.create_publisher(Clock, '/clock', 10)
        info_pub = source.create_publisher(CameraInfo, '/camera/camera_info', qos_profile_sensor_data)
        rgb_pub = source.create_publisher(Image, '/camera/image', qos_profile_sensor_data)
        depth_pub = source.create_publisher(Image, '/camera/depth_image', qos_profile_sensor_data)
        broadcaster = TransformBroadcaster(source)
        import numpy as np
        limit = time.monotonic()+8.
        counter = 0
        while not attempt.closed and time.monotonic() < limit:
            counter += 1
            stamp = 1_000_000_000+counter*10_000_000
            clock = Clock(); clock.clock.sec = stamp//10**9; clock.clock.nanosec = stamp%10**9
            clock_pub.publish(clock)
            info = CameraInfo(); info.header.stamp = clock.clock; info.header.frame_id = 'jsc_test_camera'
            info.height = info.width = 32
            info.k = [100., 0., 16., 0., 100., 16., 0., 0., 1.]
            info.r = [1., 0., 0., 0., 1., 0., 0., 0., 1.]
            info.p = [100., 0., 16., 0., 0., 100., 16., 0., 0., 0., 1., 0.]
            info.distortion_model = 'plumb_bob'
            info_pub.publish(info)
            for pub, encoding, step, data in (
                (rgb_pub, 'rgb8', 96, np.zeros((32, 32, 3), np.uint8).tobytes()),
                (depth_pub, '32FC1', 128, np.full((32, 32), 2., dtype='<f4').tobytes())):
                msg = Image(); msg.header = info.header; msg.width = msg.height = 32
                msg.encoding = encoding; msg.step = step; msg.is_bigendian = 0; msg.data = data
                pub.publish(msg)
            tf = TransformStamped(); tf.header.stamp = clock.clock; tf.header.frame_id = 'map'
            tf.child_frame_id = 'jsc_test_camera'; tf.transform.rotation.w = 1.
            broadcaster.sendTransform(tf)
            # Service actual DDS callbacks while keeping publication wall-clock bounded.
            until = time.monotonic()+.03
            while time.monotonic() < until:
                executor.spin_once(timeout_sec=.005)
        capture.finish()
        summary = json.loads((args.output/'summary.json').read_text())
        write_once(args.output/'transport_test.json', dict(
            synthetic_only=True, wave_s_launched=False, simulator_launched=False,
            domain_id=args.domain_id, capture_status=summary['status'],
            passed=summary['status'] == 'captured', human_labels_generated=False))
        print(json.dumps(summary, indent=2))
        if summary['status'] != 'captured':
            raise RuntimeError('synthetic ROS transport check did not pass')
    finally:
        if capture is not None:
            capture.finish()
        if executor is not None:
            executor.shutdown()
        if capture is not None:
            capture.destroy_node()
        if source is not None:
            source.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
