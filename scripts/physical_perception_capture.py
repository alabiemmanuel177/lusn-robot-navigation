#!/usr/bin/env python3
"""Bounded, create-once RGB-D diagnostics; never publishes or generates labels.

Use PhysicalPerceptionCapture in an existing ROS executor, then call finish()
before destroying it. Or run this script against an already-running isolated
ROS domain. No simulator is launched. Each frame stores exact ROS Image.data
bytes and encoding/step/endian metadata, CameraInfo, and the camera-to-map TF
at the RGB timestamp (or an explicit TF error). Decode RGB respecting row step
and encoding; decode depth respecting encoding/endian, retaining NaNs. These
are diagnostic inputs, not detector successes or human-reviewed observations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import rclpy
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from rosidl_runtime_py.convert import message_to_ordereddict
from sensor_msgs.msg import CameraInfo, Image
from tf2_ros import Buffer, TransformException, TransformListener


def _stamp(message):
    return message.header.stamp.sec * 1_000_000_000 + message.header.stamp.nanosec


def _json_once(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


class PhysicalPerceptionCapture(Node):
    """Read-only camera subscriber. Caller owns executor and node lifecycle."""

    def __init__(self, output_directory, *, max_frames=5, interval_s=1.0,
                 sync_tolerance_ms=3.0, rgb_topic='/camera/image',
                 depth_topic='/camera/depth_image', info_topic='/camera/camera_info',
                 observation_triggered=False, node_name='research3_physical_perception_capture',
                 capture_categories=None):
        if type(max_frames) is not int or not 1 <= max_frames <= 20:
            raise ValueError('max_frames must be an integer in [1, 20]')
        if not math.isfinite(interval_s) or interval_s <= 0:
            raise ValueError('interval_s must be positive and finite')
        if not math.isfinite(sync_tolerance_ms) or not 0 <= sync_tolerance_ms <= 100:
            raise ValueError('sync tolerance must be finite and in [0, 100] ms')
        if capture_categories is not None and (
                not observation_triggered or isinstance(capture_categories, str)
                or not capture_categories or any(not isinstance(value, str) or not value.strip()
                                                  for value in capture_categories)):
            raise ValueError('capture_categories requires observation mode and nonempty category names')
        self.output = Path(output_directory)
        self.output.mkdir(parents=True, exist_ok=False)
        super().__init__(node_name, parameter_overrides=[
            Parameter('use_sim_time', value=True)])
        self.max_frames = max_frames
        self.interval_ns = int(interval_s * 1e9)
        self.tolerance_ns = int(sync_tolerance_ms * 1e6)
        self.frames = []
        self.rgb, self.depth = {}, {}
        self.observation_triggered = observation_triggered
        self.pending_observations = {}
        self.missed_observation_frames = 0
        self.observation_messages_received = 0
        self.capture_categories = frozenset(capture_categories or ())
        self.observation_index = {}
        self.max_observations_per_frame = 64
        self.observation_overflow = 0
        self.observation_conflicts = 0
        self.info = None
        self.last_stamp = None
        self.finished = False
        self.counts = {'rgb_received': 0, 'depth_received': 0, 'camera_info_received': 0}
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.create_subscription(Image, rgb_topic, self._rgb, qos_profile_sensor_data)
        self.create_subscription(Image, depth_topic, self._depth, qos_profile_sensor_data)
        self.create_subscription(CameraInfo, info_topic, self._info, qos_profile_sensor_data)
        if observation_triggered:
            from language_nav_interfaces.msg import SemanticObservation
            self.create_subscription(SemanticObservation, '/semantic_observations',
                                     self._observation, 100)
        _json_once(self.output / 'request.json', {
            'schema_version': 'research3-perception-diagnostic-request/v1',
            'max_frames': max_frames, 'interval_s': interval_s,
            'sync_tolerance_ms': sync_tolerance_ms,
            'topics': {'rgb': rgb_topic, 'depth': depth_topic, 'camera_info': info_topic},
            'generates_labels': False, 'publishes_motion': False,
            'observation_triggered': observation_triggered,
            'rgb_association': 'exact_timestamp_only', 'buffer_frames': 32,
            'capture_categories': sorted(self.capture_categories),
            'max_observations_per_frame': self.max_observations_per_frame,
        })

    @property
    def done(self):
        return self.finished or len(self.frames) >= self.max_frames

    def _info(self, message):
        if not self.done:
            self.counts['camera_info_received'] += 1
            self.info = message
            self._pair()

    def _rgb(self, message):
        self._add(self.rgb, message, 'rgb_received')

    def _depth(self, message):
        self._add(self.depth, message, 'depth_received')

    def _observation(self, message):
        if self.finished:
            return
        self.observation_messages_received += 1
        stamp = int(message.observed_at_ns)
        observation = message_to_ordereddict(message)
        # Image sampling is complete, not message batching. A detector publishes
        # several objects separately for the same already-written RGB frame.
        if stamp in self.observation_index:
            entry = self.observation_index[stamp]
            self._retain_observation(entry['observations'], observation,
                                     entry['conflicting_observation_ids'])
            return
        if self.done:
            return
        if stamp <= 0 or (self.last_stamp is not None
                          and stamp - self.last_stamp < self.interval_ns):
            return
        pending = self.pending_observations.setdefault(stamp, [])
        # Pending conflicts are retained as duplicate IDs so the join audit can
        # reject the frame instead of silently choosing an inconsistent message.
        self._retain_observation(pending, observation)
        while len(self.pending_observations) > 32:
            del self.pending_observations[min(self.pending_observations)]
            self.missed_observation_frames += 1
        self._pair()

    def _retain_observation(self, observations, observation, conflicts=None):
        matches = [row for row in observations
                   if row.get('observation_id') == observation.get('observation_id')]
        if observation in matches:
            return
        if matches:
            self.observation_conflicts += 1
            if conflicts is not None:
                identifier = observation.get('observation_id')
                if identifier not in conflicts:
                    conflicts.append(identifier)
                return
        if len(observations) >= self.max_observations_per_frame:
            self.observation_overflow += 1
            return
        observations.append(observation)

    def _add(self, buffer, message, count):
        if self.done:
            return
        self.counts[count] += 1
        buffer[_stamp(message)] = message
        while len(buffer) > 32:
            del buffer[min(buffer)]
        self._pair()

    def _pair(self):
        if self.done or self.info is None or not self.rgb or not self.depth:
            return
        if self.observation_triggered:
            matches = sorted(set(self.rgb) & set(self.pending_observations))
            matches = [stamp for stamp in matches if self.last_stamp is None
                       or stamp - self.last_stamp >= self.interval_ns]
            if self.capture_categories:
                matches = [stamp for stamp in matches if any(
                    row.get('category') in self.capture_categories
                    for row in self.pending_observations[stamp])]
            if not matches:
                return
            rgb_stamp = matches[0]
        else:
            rgb_stamp = max(self.rgb)
        if self.last_stamp is not None and rgb_stamp - self.last_stamp < self.interval_ns:
            return
        depth_stamp = min(self.depth, key=lambda stamp: abs(stamp - rgb_stamp))
        if abs(depth_stamp - rgb_stamp) > self.tolerance_ns:
            return
        rgb, depth = self.rgb.pop(rgb_stamp), self.depth.pop(depth_stamp)
        index = len(self.frames)
        record = {'index': index, 'rgb_stamp_ns': rgb_stamp,
                  'depth_stamp_ns': depth_stamp, 'sync_difference_ns': depth_stamp - rgb_stamp,
                  'camera_info': message_to_ordereddict(self.info)}
        record['trigger_observations'] = self.pending_observations.pop(rgb_stamp, [])
        record['observation_triggered'] = self.observation_triggered
        for name, message in (('rgb', rgb), ('depth', depth)):
            raw = bytes(message.data)
            filename = f'frame-{index:03d}-{name}.bin'
            with (self.output / filename).open('xb') as stream:
                stream.write(raw)
            record[name] = {'file': filename, 'sha256': hashlib.sha256(raw).hexdigest(),
                            'bytes': len(raw), 'width': message.width, 'height': message.height,
                            'step': message.step, 'encoding': message.encoding,
                            'is_bigendian': message.is_bigendian,
                            'frame_id': message.header.frame_id}
        frame_id = rgb.header.frame_id
        record['camera_to_map'] = None
        record['transform_error'] = None
        if not frame_id:
            record['transform_error'] = 'RGB frame_id is empty; transform not guessed'
        else:
            try:
                transform = self.tf_buffer.lookup_transform(
                    'map', frame_id, Time.from_msg(rgb.header.stamp),
                    timeout=Duration(seconds=0.0))
                record['camera_to_map'] = message_to_ordereddict(transform)
            except TransformException as exc:
                record['transform_error'] = str(exc)
        _json_once(self.output / f'frame-{index:03d}.json', record)
        if self.observation_triggered:
            self.observation_index[rgb_stamp] = {
                'frame': f'frame-{index:03d}.json', 'rgb_stamp_ns': rgb_stamp,
                'frame_sha256': hashlib.sha256(
                    (self.output / f'frame-{index:03d}.json').read_bytes()).hexdigest(),
                'observations': list(record['trigger_observations']),
                'conflicting_observation_ids': [],
            }
        self.frames.append(record)
        self.last_stamp = rgb_stamp
        for stamp in list(self.pending_observations):
            if stamp < rgb_stamp:
                self.missed_observation_frames += 1
                del self.pending_observations[stamp]

    def finish(self):
        """Write an immutable summary, even when no images arrived. Idempotent."""
        if not self.finished:
            self.finished = True
            index_reference = None
            if self.observation_triggered:
                index_path = self.output / 'observation_index.json'
                _json_once(index_path, {
                    'schema_version': 'research3-captured-frame-observations/v1',
                    'frames': list(self.observation_index.values()),
                    'max_observations_per_frame': self.max_observations_per_frame,
                    'observation_overflow': self.observation_overflow,
                    'observation_conflicts': self.observation_conflicts,
                    'human_labels_generated': False,
                })
                index_reference = {'file': index_path.name,
                                   'sha256': hashlib.sha256(index_path.read_bytes()).hexdigest()}
            _json_once(self.output / 'summary.json', {
                'schema_version': 'research3-perception-diagnostic/v1',
                'frames_captured': len(self.frames), 'frames_requested': self.max_frames,
                'received_counts': self.counts,
                'complete': len(self.frames) == self.max_frames,
                'frames': [f'frame-{i:03d}.json' for i in range(len(self.frames))],
                'detector_performance_validated': False, 'human_labels_generated': False,
                'observation_triggered': self.observation_triggered,
                'observation_index': index_reference,
                'capture_categories': sorted(self.capture_categories),
                'observation_overflow': self.observation_overflow,
                'observation_conflicts': self.observation_conflicts,
                'observation_messages_received': self.observation_messages_received,
                'unmatched_observation_frames': (
                    self.missed_observation_frames + len(self.pending_observations)),
                'sampling_scope': 'bounded diagnostic sample, not exhaustive detector coverage',
            })
        return len(self.frames)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--max-frames', type=int, default=5)
    parser.add_argument('--interval', type=float, default=1.0)
    parser.add_argument('--timeout', type=float, default=30.0)
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error('timeout must be positive and finite')
    rclpy.init()
    node = None
    try:
        node = PhysicalPerceptionCapture(args.output, max_frames=args.max_frames,
                                         interval_s=args.interval)
        deadline = time.monotonic() + args.timeout
        while rclpy.ok() and not node.done and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        if node is not None:
            node.finish()
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
