import numpy as np
import pytest
from audit_object_localization_candidate import reconstruct


def test_square_padding_scale_and_uncalibrated_score_reconstruction():
    logits=np.array([[[0.,-1.,-2.,-3.,-4.,-5.]]],dtype=np.float32)
    boxes=np.array([[[.5,.5,.5,.25]]],dtype=np.float32)
    labels,scores,corners=reconstruct(logits,boxes,640,480,.1)
    assert labels.tolist()==[0] and scores.tolist()==[.5]
    assert corners.tolist()==[[160.,240.,480.,400.]]


def test_no_silent_finite_or_shape_repair():
    logits=np.zeros((1,1,6),dtype=np.float32); boxes=np.zeros((1,1,4),dtype=np.float32)
    logits[0,0,0]=float('nan')
    with pytest.raises(ValueError):reconstruct(logits,boxes,640,480,.1)


def test_threshold_strictly_greater_and_no_padding_box_clipping():
    logits=np.zeros((1,1,6),dtype=np.float32);boxes=np.array([[[1.,1.,1.,1.]]],dtype=np.float32)
    assert len(reconstruct(logits,boxes,640,480,.5)[0])==0
    assert reconstruct(logits,boxes,640,480,.1)[2][0,3]>480
