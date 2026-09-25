#!/usr/bin/env python3
"""Opt-in collector candidate for prospective expansion; requires a source pin.

Caller must arm after localization/provider readiness and retain the observation
window until an evidenced completion/timeout. No simulator or node is started by
importing this module. The frozen historical collector is not modified.
"""
import hashlib
import re
import threading
import time
import physical_perception_capture as base
from expansion_sampling import first_synchronized_pair


class ExpansionCaptureCandidate(base.PhysicalPerceptionCapture):
    def __init__(self, output_directory, **kwargs):
        if kwargs.pop('max_frames', 1) != 1:
            raise ValueError('expansion uses one prespecified frame')
        if 'observation_triggered' in kwargs or 'capture_categories' in kwargs:
            raise ValueError('category-conditioned sampling is forbidden')
        self.armed = False
        self.armed_at_ns = None
        self.transform_wait_s = 2.0
        self._capture_lock = threading.RLock()
        super().__init__(output_directory, max_frames=1, observation_triggered=False,
                         node_name='research3_expansion_capture_candidate', **kwargs)
        from language_nav_interfaces.msg import SemanticObservation
        self.create_subscription(SemanticObservation, '/semantic_observations', self._observation, 100)
        # Base finish() uses this flag to serialize late exact-frame observations.
        # Frame selection below never uses pending observations or their classes.
        self.observation_triggered = True
        base._json_once(self.output/'expansion_sampling_contract.json', {
            'schema_version':'research3-expansion-sampling-candidate/v1',
            'observation_triggered':False, 'selection':'first_synchronized_pair_after_arm',
            'target_or_confidence_used_to_select_frame':False,
            'arm_required_after_readiness':True, 'execution_authorized':False,
            'source_revision_approval_required':True,
        })

    def arm(self, readiness_evidence):
        with self._capture_lock:
            if self.armed or self.frames or self.finished:
                raise ValueError('arm exactly once before capture')
            required=('localization_converged','provider_ready','transforms_ready','isolated_domain_verified')
            if (not isinstance(readiness_evidence,dict)
                    or any(readiness_evidence.get(key) is not True for key in required)
                    or not re.fullmatch(r'[0-9a-f]{64}',readiness_evidence.get('source_snapshot_sha256',''))):
                raise ValueError('bound positive readiness evidence required before arming')
            now=self.get_clock().now().nanoseconds
            if type(now) is not int or now<=0:raise ValueError('positive simulation clock required')
            base._json_once(self.output/'armed.json', {
                'armed_at_ros_ns':now,'readiness_evidence':readiness_evidence,
                'readiness_is_callers_evidence_obligation':True,
            })
            self.rgb.clear();self.depth.clear();self.pending_observations.clear()
            self.armed_at_ns=now
            self.armed = True

    def _rgb(self,message):
        with self._capture_lock:
            if self.armed and base._stamp(message)>self.armed_at_ns:
                super()._rgb(message)

    def _depth(self,message):
        with self._capture_lock:
            if self.armed and base._stamp(message)>self.armed_at_ns:
                super()._depth(message)

    def _info(self,message):
        with self._capture_lock:
            super()._info(message)

    def _observation(self,message):
        with self._capture_lock:
            if self.armed and int(message.observed_at_ns)>self.armed_at_ns:
                super()._observation(message)

    def finish(self):
        # Close callbacks and serialize the same immutable rows used by the
        # attempt classifier, including when the runner exits exceptionally.
        with self._capture_lock:
            return super().finish()

    def _pair(self):
        if not self.armed or self.done or self.info is None:
            return
        pair=first_synchronized_pair(
            [s for s in self.rgb if s>self.armed_at_ns],
            [s for s in self.depth if s>self.armed_at_ns],self.tolerance_ns)
        if pair is None:return
        rgb_stamp,depth_stamp=pair
        rgb,depth=self.rgb.pop(rgb_stamp),self.depth.pop(depth_stamp)
        record={'index':0,'rgb_stamp_ns':rgb_stamp,'depth_stamp_ns':depth_stamp,
                'sync_difference_ns':depth_stamp-rgb_stamp,
                'camera_info':base.message_to_ordereddict(self.info),
                'trigger_observations':[], 'observation_triggered':False,
                'sampling_contract':'first_synchronized_pair_after_arm',
                'camera_to_map':None,'transform_error':None}
        for kind,message in [('rgb',rgb),('depth',depth)]:
            raw=bytes(message.data);name=f'frame-000-{kind}.bin'
            with (self.output/name).open('xb') as stream:stream.write(raw)
            record[kind]={'file':name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),
                          'width':message.width,'height':message.height,'step':message.step,
                          'encoding':message.encoding,'is_bigendian':message.is_bigendian,
                          'frame_id':message.header.frame_id}
        if not rgb.header.frame_id:
            record['transform_error']='RGB frame_id is empty; transform not guessed'
        else:
            # The exact-stamp transform normally arrives a few milliseconds after
            # the image. Wait a bounded time for that stamp; the selected frame
            # and its stamp never change, so sampling stays detection-independent.
            when=base.Time.from_msg(rgb.header.stamp)
            waited=0.0
            while (not self.tf_buffer.can_transform('map',rgb.header.frame_id,when)
                   and waited<self.transform_wait_s):
                time.sleep(.01);waited+=.01
            record['transform_wait_s']=round(waited,3)
            try:
                transform=self.tf_buffer.lookup_transform('map',rgb.header.frame_id,when,
                    timeout=base.Duration(seconds=0.0))
                record['camera_to_map']=base.message_to_ordereddict(transform)
            except base.TransformException as exc:record['transform_error']=str(exc)
        base._json_once(self.output/'frame-000.json',record)
        self.observation_index[rgb_stamp]={
            'frame':'frame-000.json','rgb_stamp_ns':rgb_stamp,
            'frame_sha256':hashlib.sha256((self.output/'frame-000.json').read_bytes()).hexdigest(),
            'observations':self.pending_observations.pop(rgb_stamp,[]),
            'conflicting_observation_ids':[],
        }
        self.frames.append(record);self.last_stamp=rgb_stamp


def run_frame_provider(output):
    """Invoke the unchanged provider once on the retained bytes, with an audit.

    Live camera subscriptions must be remapped to unused isolated topics. The
    file is chosen before any detection, and is never replaced after processing.
    """
    import json
    from pathlib import Path
    import rclpy
    from rclpy.executors import MultiThreadedExecutor
    from rosidl_runtime_py.set_message import set_message_fields
    from research3_landmark_bridge.node import LandmarkObservationNode
    from sensor_msgs.msg import Image, CameraInfo
    output=Path(output)

    class AuditedProvider(LandmarkObservationNode):
        def __init__(self):
            super().__init__()
            for key in ('rgb_topic','depth_topic','camera_info_topic'):
                if not self.get_parameter(key).value.startswith('/r3_expansion_unused/'):
                    raise ValueError('live image subscriptions forbidden in exact-frame wrapper')
            self.claimed=False
            self.emissions=[]
            original=self.publisher
            emissions=self.emissions
            class RecordingPublisher:
                def publish(self,message):
                    original.publish(message)
                    emissions.append(base.message_to_ordereddict(message))
            self.publisher=RecordingPublisher()
            self.first_seen=None
            self.transform_wait_s=10.0
            self.tf_ready_recorded=False
            self.create_timer(.05,self.process_retained)
            self.create_timer(.05,self.record_transform_readiness)

        def record_transform_readiness(self):
            # Positive evidence that this process's own transform buffer already
            # holds the camera-to-map chain at the current simulated time. The
            # collector arms only after this file exists, so the first frame after
            # arming is never older than the buffer's earliest data.
            if self.tf_ready_recorded:return
            now=self.get_clock().now()
            if now.nanoseconds<=0 or not self.tf_buffer.can_transform('map','camera_depth_frame',now):return
            self.tf_ready_recorded=True
            base._json_once(output/'provider_tf_ready.json',{'schema_version':'research3-provider-transform-readiness/v1',
                'ready_at_ros_ns':now.nanoseconds,'frame':'camera_depth_frame'})

        def process_retained(self):
            frame_path=output/'perception_capture/frame-000.json'
            # Collector writes the index only after the full frame and its bytes.
            if self.claimed or not frame_path.exists():return
            try:
                raw=frame_path.read_bytes();frame=json.loads(raw)
            except (json.JSONDecodeError,FileNotFoundError):return
            # Waiting for transform availability is independent of detections.
            # The wait is bounded: after it, the unchanged provider computation
            # runs anyway and its own transform lookup decides between a
            # recorded failure and a completed frame; the frame never changes.
            stamp=frame['rgb_stamp_ns']
            when=base.Time(nanoseconds=stamp)
            if self.first_seen is None:self.first_seen=time.monotonic()
            transform_ready=self.tf_buffer.can_transform('map',frame['rgb']['frame_id'],when)
            if not transform_ready and time.monotonic()-self.first_seen<self.transform_wait_s:return
            self.claimed=True
            audit=dict(schema_version='research3-exact-frame-processing/v1',status='started',
                       frame_stamp_ns=stamp,frame_sha256=hashlib.sha256(raw).hexdigest(),
                       transform_available_before_processing=bool(transform_ready),
                       transform_wait_s=round(time.monotonic()-self.first_seen,3),
                       observations=[],human_labels_generated=False)
            base._json_once(output/'provider_frame_started.json',audit)
            try:
                messages=[]
                for kind in ('rgb','depth'):
                    meta=frame[kind]
                    if meta['file']!=f'frame-000-{kind}.bin':raise ValueError('unexpected retained filename')
                    data=(frame_path.parent/meta['file']).read_bytes()
                    if len(data)!=meta['bytes'] or hashlib.sha256(data).hexdigest()!=meta['sha256']:
                        raise ValueError('retained image integrity mismatch')
                    msg=Image()
                    ns=frame[f'{kind}_stamp_ns']
                    msg.header.stamp.sec=ns//1_000_000_000;msg.header.stamp.nanosec=ns%1_000_000_000
                    msg.header.frame_id=meta['frame_id']
                    for key in ('width','height','step','encoding','is_bigendian'):setattr(msg,key,meta[key])
                    msg.data=data
                    messages.append(msg)
                self.camera_info=CameraInfo()
                set_message_fields(self.camera_info,frame['camera_info'])
                # No detector implementation, formula or association is replaced.
                self._process(*messages)
                if self.review_handle is not None:self.review_handle.flush()
                audit['status']='completed'
            except Exception as exc:
                audit.update(status='failed',error_type=type(exc).__name__,error=str(exc))
            audit['observations']=self.emissions
            base._json_once(output/'provider_frame_completion.json',audit)
            # Sentinel is published after the entire completion record is closed.
            base._json_once(output/'provider_frame_done.json',{'complete_record_written':True})

    rclpy.init()
    node=AuditedProvider();executor=MultiThreadedExecutor(num_threads=4);executor.add_node(node)
    try:executor.spin()
    except KeyboardInterrupt:pass
    finally:
        executor.shutdown()
        if node.review_handle is not None:node.review_handle.close()
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()


if __name__=='__main__':
    import sys
    if len(sys.argv)<3 or sys.argv[1]!='--exact-frame-provider':raise SystemExit('exact-frame provider mode required')
    destination=sys.argv[2]
    del sys.argv[1:3]
    run_frame_provider(destination)
