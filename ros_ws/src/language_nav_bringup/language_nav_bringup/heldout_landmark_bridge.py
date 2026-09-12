"""Authorized R3-owned initializer; unchanged pinned R1 detector callbacks.

No review/capture output, no provider monkeypatch and no R1 source changes.
"""
import inspect
from pathlib import Path
import threading

import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image
from tf2_ros import Buffer, TransformListener
from language_nav_interfaces.msg import SemanticObservation
from research3_landmark_bridge.node import LandmarkObservationNode
from research3_landmark_bridge import core
from semantic_perception.live_risk_node import decode_image
from semantic_perception.projection import quaternion_matrix
from language_nav.physical_heldout_authorization import node_authorization, pinned, R1


class HeldoutLandmarkObservationNode(LandmarkObservationNode):
    def __init__(self):
        Node.__init__(self, 'research3_landmark_bridge')
        authorization = node_authorization(self)
        if authorization is None:
            raise PermissionError('protected provider requires explicit episode authorization')
        # Verify actual imported implementations, not merely files in a checkout.
        for value, name in ((LandmarkObservationNode, 'extensions/research3_landmark_bridge/research3_landmark_bridge/node.py'),
                            (core, 'extensions/research3_landmark_bridge/research3_landmark_bridge/core.py'),
                            (decode_image, 'src/semantic_perception/semantic_perception/live_risk_node.py'),
                            (quaternion_matrix, 'src/semantic_perception/semantic_perception/projection.py')):
            expected = R1 / name
            if Path(inspect.getfile(value)).resolve() != expected.resolve():
                raise PermissionError('provider implementation imported from an unapproved path')
        for name, default in {'scene': '', 'calibration': '', 'review_log': '',
                              'rgb_topic': '/camera/image', 'depth_topic': '/camera/depth_image',
                              'camera_info_topic': '/camera/camera_info', 'output_topic': '/semantic_observations',
                              'sync_tolerance_ms': 3., 'color_tolerance': 38., 'min_pixels': 18,
                              'association_radius_m': .9}.items():
            self.declare_parameter(name, default)
        if self.get_parameter('review_log').value:
            raise PermissionError('protected review task generation is forbidden')
        self.review_handle = None
        scene = Path(str(self.get_parameter('scene').value)).resolve()
        authorization.asset(scene)
        calibration = pinned(authorization.root, authorization.approval['calibration'])
        if Path(str(self.get_parameter('calibration').value)).resolve() != calibration.resolve():
            raise PermissionError('provider calibration differs from approved artifact')
        expected_tolerance = authorization.episode['camera_color_tolerance']
        fixed = {'sync_tolerance_ms': 3., 'min_pixels': 18, 'association_radius_m': .9,
                 'color_tolerance': expected_tolerance, 'rgb_topic': '/camera/image',
                 'depth_topic': '/camera/depth_image', 'camera_info_topic': '/camera/camera_info',
                 'output_topic': '/semantic_observations'}
        if any(self.get_parameter(name).value != value for name, value in fixed.items()):
            raise PermissionError('provider settings differ from fixed approved detector contract')
        self.scene = core.load_landmark_scene(scene, allow_protected=True)
        if self.scene.partition != 'test' or self.scene.map_id != authorization.episode['map_id']:
            raise PermissionError('provider scene differs from authorized protected map')
        self.temperature = core.calibration_temperature(str(calibration))
        self.sync_tolerance_ns = 3_000_000
        self.color_tolerance = float(expected_tolerance)
        self.min_pixels = 18
        self.association_radius_m = .9
        self.source = f'research3-landmark-bridge:{self.scene.map_id}:v1'
        self.sequence = 0
        self.rgb, self.depth = {}, {}
        self.camera_info = None
        self.processing_lock = threading.Lock()
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.publisher = self.create_publisher(SemanticObservation, '/semantic_observations',
            QoSProfile(depth=20, reliability=ReliabilityPolicy.RELIABLE))
        self.create_subscription(Image, '/camera/image', self._rgb, qos_profile_sensor_data)
        self.create_subscription(Image, '/camera/depth_image', self._depth, qos_profile_sensor_data)
        self.create_subscription(CameraInfo, '/camera/camera_info', self._info, qos_profile_sensor_data)


def main(args=None):
    rclpy.init(args=args)
    node = None
    executor = MultiThreadedExecutor(num_threads=4)
    try:
        node = HeldoutLandmarkObservationNode()
        executor.add_node(node)
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
