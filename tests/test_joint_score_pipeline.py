import json
import numpy as np
import pytest

from joint_score_collection import OneFrameAttempt
from joint_score_pipeline import process_capture, ordered_ledger
from fit_joint_score_wave_s import sha
from prepare_joint_score_protocol import ROOT


def tf(stamp, frame):
    return dict(header=dict(frame_id='map', stamp=dict(sec=0, nanosec=stamp)), child_frame_id=frame,
                transform=dict(translation=dict(x=0., y=0., z=0.), rotation=dict(x=0., y=0., z=0., w=1.)))


@pytest.fixture
def captured(tmp_path):
    a = OneFrameAttempt(tmp_path/'capture', 'synthetic-attempt', 0.)
    info = dict(k=[100., 0., 50., 0., 100., 50., 0., 0., 1.], r=np.eye(3).ravel().tolist(),
                d=[], p=np.zeros(12).tolist(), distortion_model='plumb_bob')
    a.arm(info, 1., arm_stamp_ns=1)
    rgb = np.zeros((100, 100, 3), np.uint8)
    depth = np.full((100, 100), 2., dtype='<f4')
    for channel, data, step, encoding in [('rgb', rgb, 300, 'rgb8'), ('depth', depth, 400, '32FC1')]:
        a.receive(channel, 100, dict(height=100, width=100, step=step, encoding=encoding,
                                    is_bigendian=0, frame_id='camera'), data.tobytes(), 2.)
    a.tick(4., tf)
    frame_sha = sha(a.output/'frame-000.json')
    asset = tmp_path/'invented-model-output.json'; asset.write_text('{"synthetic_only":true}')
    completion = dict(status='completed', frame_sha256=frame_sha, audit_passed=True,
                      input_sha256={str(asset): sha(asset)})
    detector = dict(completion, boxes=[dict(visual_category='chair', xyxy=[0, 0, 100, 100], raw_score=.8)])
    ocr = dict(completion, texts=[])
    slot = dict(attempt_id='synthetic-attempt', wave='S', partition='development', acquisition_class='chair')
    return a.output, slot, detector, ocr


def run(inputs):
    return process_capture(*inputs, nominal_mount=np.eye(4), rendered_mount=np.eye(4),
        catalogue=[dict(category='chair', entity_id='synthetic-chair', x=0., y=0.)])


def test_capture_to_feature_end_to_end(captured):
    result = run(captured)
    assert result['status'] == result['processing_status'] == 'completed'
    assert len(result['emissions']) == 1
    assert result['emissions'][0]['raw_score'] == .8
    assert not result['human_labels_generated']


def test_empty_acknowledged_detector_is_nondetection(captured):
    captured[2]['boxes'] = []
    result = run(captured)
    assert result['status'] == 'completed' and result['perception_status'] == 'nondetection'
    assert result['emissions'] == []


@pytest.mark.parametrize('mode', ['missing', 'failed', 'wrong_frame'])
def test_no_ack_is_infrastructure_not_negative(captured, mode):
    values = list(captured)
    if mode == 'missing': values[2] = None
    elif mode == 'failed': values[2]['status'] = 'failed'
    else: values[2]['frame_sha256'] = 'wrong'
    result = run(values)
    assert result['status'] == 'infrastructure_failure' and not result['emissions']


def test_wave_v_and_tampered_bytes_fail_closed(captured):
    captured[1]['wave'] = 'V'
    with pytest.raises(PermissionError): run(captured)
    captured[1]['wave'] = 'S'
    (captured[0]/'frame-000-rgb.bin').write_bytes(b'changed')
    with pytest.raises(ValueError, match='bytes changed'): run(captured)


def test_ordered_accounting_rejects_missing_attempts():
    s = json.loads((ROOT/'reports/joint_score_protocol_20260924_v1/schedule.json').read_text())
    args = dict(protocol_sha256='p', schedule_sha256='s', execution_manifest_sha256='e')
    with pytest.raises(ValueError): ordered_ledger(s, [], **args)
    attempts = [dict(attempt_id=r['attempt_id'], wave='S', status='infrastructure_failure', reason='synthetic interruption')
                for r in s['rows'] if r['wave'] == 'S']
    result = ordered_ledger(s, attempts[::-1], **args)
    assert result['attempts'] == attempts
