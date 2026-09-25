"""Freeze frame choice before a bounded transport delay, never wait for success."""
import math


class FixedFrameDelay:
    def __init__(self,seconds=2.):
        if not math.isfinite(seconds) or seconds<=0:raise ValueError('positive finite delay')
        self.seconds=seconds;self.pending=None

    def select(self,payload,now):
        if self.pending is not None:raise ValueError('cannot replace a selected frame')
        if not math.isfinite(now):raise ValueError('finite clock')
        self.pending=(now,payload)

    def take_due(self,now):
        if self.pending is None or now-self.pending[0]<self.seconds:return None
        _,payload=self.pending;self.pending=None;return payload
