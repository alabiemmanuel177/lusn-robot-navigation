import numpy as np
import pytest
from research3_steps14_feasibility import temperature, PROMPTS


def test_temperature_cannot_cross_half():
    p=np.array([.001,.054,.1,.319,.499,.5,.501,.8,.99])
    for t in (.2,1.,5.):
        q=temperature(p,t)
        assert np.array_equal(q<.5,p<.5)
        assert np.array_equal(q>.5,p>.5)
    assert np.allclose(temperature(p,1.),p)


@pytest.mark.parametrize('t',[0,-1,float('nan'),float('inf')])
def test_temperature_rejects_invalid(t):
    with pytest.raises(ValueError):temperature(.2,t)


def test_exact_diagnostic_queries():
    assert len(PROMPTS)==6
    assert PROMPTS['doorway']=='a photo of a doorway'
