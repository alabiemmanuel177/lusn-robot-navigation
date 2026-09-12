#!/usr/bin/env python3
"""Unwired collector candidate for prospective expansion; requires source approval.

Caller must arm after localization/provider readiness and retain the observation
window until an evidenced completion/timeout. No simulator or node is started by
importing this module. The frozen historical collector is not modified.
"""
import hashlib
import re
import threading
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
            try:
                transform=self.tf_buffer.lookup_transform('map',rgb.header.frame_id,
                    base.Time.from_msg(rgb.header.stamp),timeout=base.Duration(seconds=0.0))
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
