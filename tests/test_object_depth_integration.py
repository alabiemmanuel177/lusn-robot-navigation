import hashlib
import numpy as np
import pytest
from integrate_object_depth_candidate import decode_depth, integrate_box, checked_child


@pytest.mark.parametrize('big', [0, 1])
def test_depth_stride_endianness(big):
    values = np.array([[1, 2, 99], [3, 4, 99]], dtype='>f4' if big else '<f4')
    raw = values.tobytes()
    meta = dict(encoding='32FC1', is_bigendian=big, height=2, width=2,
                step=12, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    assert decode_depth(raw, meta).tolist() == [[1, 2], [3, 4]]
    with pytest.raises(ValueError): decode_depth(raw[:-1], meta)
    with pytest.raises(ValueError): decode_depth(raw, dict(meta, sha256='bad'))


def test_no_oracle_identity_and_ambiguity():
    k = np.array([[10,0,10],[0,10,10],[0,0,1]])
    box = dict(query='chair', xyxy=[0,0,20,20], raw_score=.2)
    refs = [dict(entity_id=i, category='chair', x=0, y=0) for i in ('a','b')]
    out = integrate_box(box, np.ones((20,20)), k, np.eye(4), refs)
    assert out['status'] == 'ambiguous'
    assert out['entity_id'] is None and out['human_verdict'] is None
    assert len(out['association']['candidates']) == 2
    assert not out['calibration_eligible'] and not out['runtime_admitted']


def test_mixed_depth_abstains():
    depth = np.ones((20,20)); depth[:,10:] = 3
    out = integrate_box(dict(query='doorway', xyxy=[0,0,20,20]), depth,
                        np.eye(3), np.eye(4), [])
    assert out['status'] == 'unresolved_multiple_surfaces'
    assert out['association'] is None


def test_non_navigation_does_not_touch_depth():
    out = integrate_box(dict(query='background'), None, None, None, None)
    assert out['status'] == 'non_navigation_visual_hypothesis'


def test_child_escape_rejected(tmp_path):
    with pytest.raises(ValueError): checked_child(tmp_path, '../outside')
