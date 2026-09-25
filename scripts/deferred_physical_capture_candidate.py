"""R3-only diagnostic collector; original frozen acquisition source unchanged."""
import time
from rclpy.clock import Clock,ClockType
from physical_perception_capture import PhysicalPerceptionCapture,_json_once
from fixed_frame_delay import FixedFrameDelay


class DeferredPhysicalCapture(PhysicalPerceptionCapture):
    def __init__(self,*args,**kwargs):
        self.delay=FixedFrameDelay(2.)
        if kwargs.get('observation_triggered'):raise ValueError('no detection-triggered sampling')
        kwargs['sync_tolerance_ms']=0.
        super().__init__(*args,**kwargs)
        _json_once(self.output/'deferred_tf_policy.json',dict(delay_wall_s=2.,
            frame_selection='earliest eligible exact RGB-D pair; frozen before waiting',
            selection_depends_on_tf_success=False,timeout_policy='retain transform failure; no replacement',
            calibration_eligible=False))
        self.create_timer(.05,self._pair,clock=Clock(clock_type=ClockType.STEADY_TIME))

    def _pair(self):
        if self.finished or len(self.frames)>=self.max_frames:return
        if self.delay.pending is not None:
            selected=self.delay.take_due(time.monotonic())
            if selected is None:return
            stamp,rgb,depth,info=selected
            buffered_rgb,buffered_depth,latest_info=self.rgb,self.depth,self.info
            self.rgb={stamp:rgb};self.depth={stamp:depth};self.info=info
            try:super()._pair()
            finally:self.rgb,self.depth,self.info=buffered_rgb,buffered_depth,latest_info
            self.rgb.pop(stamp,None);self.depth.pop(stamp,None)
            return
        if self.info is None:return
        candidates=sorted(set(self.rgb)&set(self.depth))
        for stamp in candidates:
            if self.last_stamp is None or stamp-self.last_stamp>=self.interval_ns:
                self.delay.select((stamp,self.rgb[stamp],self.depth[stamp],self.info),time.monotonic())
                break
