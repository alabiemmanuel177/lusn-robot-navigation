import json
import pytest
from joint_score_collection import OneFrameAttempt


INFO = {'k': [100., 0., 50., 0., 100., 50., 0., 0., 1.]}
META = dict(height=2, width=2, step=2, frame_id='camera', encoding='mono8', is_bigendian=0)


def tf(stamp, frame):
    return dict(header=dict(frame_id='map', stamp=dict(sec=stamp//10**9, nanosec=stamp%10**9)),
                child_frame_id=frame, transform=dict(translation=dict(x=0., y=0., z=0.), rotation=dict(x=0., y=0., z=0., w=1.)))


def pair(attempt, now=2.):
    attempt.receive('rgb', 100, META, b'1234', now)
    attempt.receive('depth', 100, META, b'5678', now)


def test_persist_first_pair_before_tf_never_replace(tmp_path):
    a = OneFrameAttempt(tmp_path/'a', 'synthetic', 0.)
    a.arm(INFO, 1., arm_stamp_ns=1)
    pair(a)
    assert (a.output/'selected_frame.json').exists()
    assert not (a.output/'frame-000.json').exists()
    a.receive('rgb', 200, META, b'abcd', 2.5)
    calls = []
    def lookup(stamp, frame):
        calls.append(stamp)
        return tf(stamp, frame)
    a.tick(3.99, lookup)
    assert calls == []
    a.tick(4., lookup)
    a.tick(5., lookup)
    assert calls == [100]
    assert (a.output/'frame-000-rgb.bin').read_bytes() == b'1234'
    assert json.loads((a.output/'summary.json').read_text())['status'] == 'captured'


def test_prearm_pairs_are_not_selected(tmp_path):
    a = OneFrameAttempt(tmp_path/'a', 'synthetic', 0.)
    pair(a, .5)
    a.arm(INFO, 1., arm_stamp_ns=1)
    assert a.selected is None
    pair(a)
    assert a.selected['rgb_stamp_ns'] == 100


@pytest.mark.parametrize('mode', ['no_stream', 'no_info', 'unmatched', 'tf_missing', 'wrong_stamp', 'interrupted', 'late_pair'])
def test_missingness_stays_infrastructure_failure(tmp_path, mode):
    a = OneFrameAttempt(tmp_path/'a', 'synthetic', 0.)
    if mode != 'no_info':
        a.arm(INFO, 1., arm_stamp_ns=1)
    if mode in ('tf_missing', 'wrong_stamp', 'interrupted'):
        pair(a)
    elif mode == 'unmatched':
        a.receive('rgb', 100, META, b'1234', 2.)
        a.receive('depth', 101, META, b'5678', 2.)
    elif mode == 'late_pair':
        pair(a, 89.)
    if mode == 'tf_missing':
        a.tick(4., lambda *args: None)
    elif mode == 'wrong_stamp':
        a.tick(4., lambda stamp, frame: tf(stamp+1, frame))
    elif mode == 'interrupted':
        a.interrupt(3.)
    else:
        a.tick(90., tf)
    s = json.loads((a.output/'summary.json').read_text())
    assert s['status'] == 'infrastructure_failure'
    assert not s['detector_processing_completed']
    assert not s['human_labels_generated']


def test_deadline_includes_startup_and_cannot_retry(tmp_path):
    a = OneFrameAttempt(tmp_path/'a', 'synthetic', 0.)
    a.arm(INFO, 91., arm_stamp_ns=1)
    assert a.closed and not a.armed
    with pytest.raises(FileExistsError):
        OneFrameAttempt(tmp_path/'a', 'synthetic', 92.)


def test_overflow_not_silent_eviction(tmp_path):
    a = OneFrameAttempt(tmp_path/'a', 'synthetic', 0.)
    a.arm(INFO, 1., arm_stamp_ns=0)
    for i in range(1, 34):
        a.receive('rgb', i, META, b'1234', 2.)
    assert a.closed
    assert json.loads((a.output/'summary.json').read_text())['reason'] == 'image_buffer_overflow'


def test_delayed_prearm_pair_excluded(tmp_path):
    a = OneFrameAttempt(tmp_path/'a', 'synthetic', 0.)
    a.arm(INFO, 1., arm_stamp_ns=100)
    pair(a)
    assert a.selected is None
    a.receive('rgb', 101, META, b'1234', 3.)
    a.receive('depth', 101, META, b'5678', 3.)
    assert a.selected['rgb_stamp_ns'] == 101
