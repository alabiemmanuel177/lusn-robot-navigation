import pytest
from fixed_frame_delay import FixedFrameDelay


def test_frame_is_frozen_and_delay_is_bounded():
    d=FixedFrameDelay(2);d.select(('frame-1',123),10.)
    with pytest.raises(ValueError):d.select(('later-frame',124),11.)
    assert d.take_due(11.99) is None
    assert d.take_due(12.)==('frame-1',123)
    assert d.take_due(13.) is None


def test_delay_has_no_detection_or_transform_success_condition():
    d=FixedFrameDelay(2);d.select(dict(tf_available=False),1.)
    assert d.take_due(3.)==dict(tf_available=False)


def test_invalid_delay():
    with pytest.raises(ValueError):FixedFrameDelay(float('nan'))
