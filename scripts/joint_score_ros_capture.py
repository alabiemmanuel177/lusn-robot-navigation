"""ROS binding for a caller-owned, authorized JSC attempt; no launch command.

The orchestrator creates OneFrameAttempt before simulator launch and passes it
here. This node only subscribes. Acquisition category/identity are not inputs.
Run in a serial executor; tick uses wall time even if simulator time stops.
"""
import time

from rclpy.clock import Clock, ClockType
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from rosidl_runtime_py.convert import message_to_ordereddict
from sensor_msgs.msg import CameraInfo, Image
from tf2_ros import Buffer, TransformListener
from language_nav.live_resources import coexistence_headroom


class JointScoreCapture(Node):
    def __init__(self, attempt, *, resource_guard=coexistence_headroom):
        self.resource_guard = resource_guard
        self.last_resource_check = time.monotonic()
        attempt.event('resource_check', self.last_resource_check, sample=resource_guard())
        super().__init__('research3_joint_score_capture', parameter_overrides=[
            Parameter('use_sim_time', value=True)])
        self.attempt = attempt
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.create_subscription(CameraInfo, '/camera/camera_info', self.info, qos_profile_sensor_data)
        self.create_subscription(Image, '/camera/image', lambda m: self.image('rgb', m), qos_profile_sensor_data)
        self.create_subscription(Image, '/camera/depth_image', lambda m: self.image('depth', m), qos_profile_sensor_data)
        self.create_timer(.05, self.tick, clock=Clock(clock_type=ClockType.STEADY_TIME))

    def info(self, message):
        if not self.attempt.armed and not self.attempt.closed:
            stamp = self.get_clock().now().nanoseconds
            if stamp <= 0:
                return  # do not arm against a missing simulator clock
            try:
                self.attempt.arm(dict(message_to_ordereddict(message)), time.monotonic(), arm_stamp_ns=stamp)
            except ValueError:
                self.attempt.close(time.monotonic(), 'infrastructure_failure', 'invalid_camera_metadata')

    def image(self, channel, message):
        stamp = message.header.stamp.sec*1_000_000_000+message.header.stamp.nanosec
        metadata = {k: getattr(message, k) for k in ('height', 'width', 'step', 'encoding', 'is_bigendian')}
        metadata['frame_id'] = message.header.frame_id
        try:
            self.attempt.receive(channel, stamp, metadata, bytes(message.data), time.monotonic())
        except ValueError:
            self.attempt.close(time.monotonic(), 'infrastructure_failure', 'invalid_image_metadata')

    def lookup(self, stamp, frame_id):
        # Buffer interpolation at the requested time is permitted; latest TF is not.
        value = self.tf_buffer.lookup_transform('map', frame_id,
            Time(nanoseconds=stamp, clock_type=ClockType.ROS_TIME), timeout=Duration(seconds=0.))
        return dict(message_to_ordereddict(value))

    def tick(self):
        now = time.monotonic()
        if self.attempt.closed:
            return
        if now-self.last_resource_check >= 5.:
            try:
                self.attempt.event('resource_check', now, sample=self.resource_guard())
            except RuntimeError as exc:
                self.attempt.close(now, 'infrastructure_failure', 'resource_guard: '+str(exc))
                return
            self.last_resource_check = now
        self.attempt.tick(now, self.lookup)

    def finish(self):
        if not self.attempt.closed:
            self.attempt.interrupt(time.monotonic())
