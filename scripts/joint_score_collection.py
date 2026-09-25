"""One-frame persistent attempt state machine; no ROS, detector or simulator truth.

Caller must record launch_monotonic BEFORE starting the simulator. The same
host monotonic clock must be used throughout. A consumed attempt is create-once.
"""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import uuid


def write_once(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')


class OneFrameAttempt:
    def __init__(self, output, attempt_id, launch_monotonic):
        if not isinstance(attempt_id, str) or not attempt_id or not math.isfinite(launch_monotonic):
            raise ValueError('attempt identity and finite launch clock required')
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=False)
        self.attempt_id = attempt_id
        self.capture_uuid = str(uuid.uuid4())
        self.launch = launch_monotonic
        self.deadline = self.launch+90.
        self.clock = self.launch
        self.armed = False
        self.closed = False
        self.info = None
        self.arm_stamp_ns = None
        self.buffers = {'rgb': {}, 'depth': {}}
        self.selected = None
        self.selected_at = None
        self.events = 0
        self.event('launch', self.launch, capture_uuid=self.capture_uuid)

    def event(self, kind, now, **fields):
        write_once(self.output/f'event-{self.events:03}.json',
                   dict(kind=kind, monotonic=now, attempt_id=self.attempt_id, **fields))
        self.events += 1

    def advance(self, now):
        if not math.isfinite(now) or now < self.clock:
            raise ValueError('monotonic clock required')
        self.clock = now
        if not self.closed and now >= self.deadline:
            self.close(now, 'infrastructure_failure', '90_second_deadline')
        return not self.closed

    def arm(self, camera_info, now, *, arm_stamp_ns):
        if not self.advance(now):
            return
        if self.armed:
            raise ValueError('attempt cannot be rearmed')
        if type(arm_stamp_ns) is not int or arm_stamp_ns < 0:
            raise ValueError('explicit simulator arming timestamp required')
        k = camera_info.get('k', [])
        if len(k) != 9 or not all(math.isfinite(v) for v in k) or k[0] <= 0 or k[4] <= 0:
            raise ValueError('camera metadata must be ready before arming')
        self.info = deepcopy(camera_info)
        self.arm_stamp_ns = arm_stamp_ns
        self.armed = True
        self.event('arm', now, camera_info=self.info, arm_stamp_ns=arm_stamp_ns)

    def receive(self, channel, stamp_ns, metadata, raw, now):
        if channel not in self.buffers or type(stamp_ns) is not int or stamp_ns < 0:
            raise ValueError('channel and integer stamp')
        if not self.advance(now) or not self.armed or self.selected is not None:
            return
        if stamp_ns <= self.arm_stamp_ns:
            return  # late delivery of a pre-arm image cannot become the selected pair
        if not isinstance(raw, bytes):
            raise ValueError('exact image bytes required')
        for key in ('height', 'width', 'step'):
            if type(metadata.get(key)) is not int or metadata[key] <= 0:
                raise ValueError('image dimensions/step')
        if len(raw) != metadata['height']*metadata['step'] or not metadata.get('frame_id'):
            raise ValueError('image byte size/frame identity')
        value = (deepcopy(metadata), raw)
        old = self.buffers[channel].get(stamp_ns)
        if old is not None and old != value:
            self.close(now, 'infrastructure_failure', 'conflicting_same_stamp_image')
            return
        self.buffers[channel][stamp_ns] = value
        if len(self.buffers[channel]) > 32:
            self.close(now, 'infrastructure_failure', 'image_buffer_overflow')
            return
        common = sorted(set(self.buffers['rgb']) & set(self.buffers['depth']))
        if not common:
            return
        stamp = common[0]
        frame = dict(index=0, rgb_stamp_ns=stamp, depth_stamp_ns=stamp,
                     sync_difference_ns=0, camera_info=self.info, capture_uuid=self.capture_uuid)
        for name in ('rgb', 'depth'):
            meta, data = self.buffers[name][stamp]
            filename = f'frame-000-{name}.bin'
            with (self.output/filename).open('xb') as stream:
                stream.write(data)
                stream.flush()
            frame[name] = dict(meta, file=filename, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        # Persist the selected evidence BEFORE waiting or attempting TF lookup.
        write_once(self.output/'selected_frame.json', frame)
        self.selected = frame
        self.selected_at = now
        self.buffers = {'rgb': {}, 'depth': {}}
        self.event('select', now, stamp_ns=stamp,
                   selected_frame_sha256=hashlib.sha256((self.output/'selected_frame.json').read_bytes()).hexdigest())

    def tick(self, now, lookup):
        if not self.advance(now) or self.selected is None or now < self.selected_at+2.:
            return
        frame = deepcopy(self.selected)
        try:
            transform = lookup(frame['rgb_stamp_ns'], frame['rgb']['frame_id'])
            if not isinstance(transform, dict) or not transform:
                raise ValueError('missing exact-time transform')
            header = transform['header']
            stamp = header['stamp']['sec']*1_000_000_000+header['stamp']['nanosec']
            if stamp != frame['rgb_stamp_ns'] or header['frame_id'] != 'map' or transform['child_frame_id'] != frame['rgb']['frame_id']:
                raise ValueError('TF must match exact selected timestamp and frames')
            p, q = transform['transform']['translation'], transform['transform']['rotation']
            if not all(math.isfinite(v) for v in [p[k] for k in ('x', 'y', 'z')]+[q[k] for k in ('x', 'y', 'z', 'w')]):
                raise ValueError('finite TF required')
            if abs(sum(q[k]**2 for k in ('x', 'y', 'z', 'w'))-1.) > 1e-6:
                raise ValueError('unit quaternion required')
            frame.update(camera_to_map=transform, transform_error=None)
        except Exception as exc:
            frame.update(camera_to_map=None, transform_error=str(exc))
        write_once(self.output/'frame-000.json', frame)
        self.close(now, 'captured' if frame['camera_to_map'] else 'infrastructure_failure',
                   None if frame['camera_to_map'] else 'exact_time_tf_failure')

    def interrupt(self, now):
        if not self.advance(now):
            return
        self.close(now, 'infrastructure_failure', 'interrupted_after_launch')

    def close(self, now, status, reason):
        if self.closed:
            return
        self.closed = True
        self.event('close', now, status=status, reason=reason)
        write_once(self.output/'summary.json', dict(
            schema_version='research3-jsc-one-frame-attempt/v1', attempt_id=self.attempt_id,
            capture_uuid=self.capture_uuid, status=status, reason=reason,
            consumed=True, armed=self.armed, selected_frame_present=self.selected is not None,
            selected_stamp_ns=None if self.selected is None else self.selected['rgb_stamp_ns'],
            launch_monotonic=self.launch, deadline_monotonic=self.deadline,
            detector_processing_completed=False, human_labels_generated=False))
