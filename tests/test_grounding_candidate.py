import numpy as np
import pytest
from run_grounding_candidate import classify_label, reconstruct


def test_no_partial_or_compound_class_repair():
    assert classify_label(' Laboratory   entrance ')=='laboratory_entrance'
    assert classify_label('entrance') is None
    assert classify_label('laboratory office entrance') is None
    assert classify_label('') is None
    assert classify_label('wall')=='background'


def test_non_square_box_and_masked_token_reconstruction():
    scores,boxes=reconstruct(np.array([[[0.,-np.inf],[-10.,-np.inf]]]),np.array([[[.5,.5,.5,.5],[.1,.1,.1,.1]]]),640,480)
    assert scores.tolist()==[.5]
    assert boxes.tolist()==[[160.,120.,480.,360.]]


def test_invalid_raw_rejected():
    with pytest.raises(ValueError):reconstruct(np.array([[[np.nan]]]),np.ones((1,1,4)),640,480)
