import numpy as np
import pytest
from joint_score_method_candidate import features,fit_synthetic,objective_gradient,sigmoid


def fixture():
    x=np.array([features(.15,.95,.01,.1)]*18+[features(.12,.6,.1,.7)]*2)
    y=np.array([1.]*18+[0.]*2);w=np.full(20,.05)
    return x,y,w


def test_gradient_finite_difference():
    x,y,w=fixture();beta=np.arange(5)*.1
    _,analytic=objective_gradient(beta,x,y,w)
    numerical=[]
    for i in range(5):
        d=np.eye(5)[i]*1e-6
        numerical.append((objective_gradient(beta+d,x,y,w)[0]-objective_gradient(beta-d,x,y,w)[0])/2e-6)
    assert np.allclose(analytic,numerical,atol=1e-8,rtol=0)


def test_fixed_solver_and_intercept_capability_on_synthetic_only():
    x,y,w=fixture()
    a=fit_synthetic(x,y,w,provenance='synthetic_unit_test')
    assert a==fit_synthetic(x,y,w,provenance='synthetic_unit_test')
    assert a['objective']<a['initial_objective']
    assert sigmoid(x[0]@a['coefficients'])>.5
    assert not a['runtime_admitted'] and not a['calibration_eligible']


@pytest.mark.parametrize('provenance',['development','validation','pilot','human_review','protected'])
def test_no_real_data_fit_authority(provenance):
    with pytest.raises(ValueError):fit_synthetic(*fixture(),provenance=provenance)


def test_degenerate_labels_and_bad_weights_rejected():
    x,y,w=fixture()
    with pytest.raises(ValueError):fit_synthetic(x,np.ones(20),w,provenance='synthetic_unit_test')
    with pytest.raises(ValueError):fit_synthetic(x,y,w*2,provenance='synthetic_unit_test')


def test_feature_range_and_missingness():
    with pytest.raises(ValueError):features(float('nan'),1,0,.1)
    with pytest.raises(ValueError):features(.3,1,0,1.)
    assert features(.3,1,8,.9)[3]==1
