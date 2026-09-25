import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import marginal_power_sensitivity as power
from world_paired_power_simulation import exact_two_sided_p


@pytest.mark.parametrize('baseline',[.75,.85,.9])
@pytest.mark.parametrize('icc',[0.,.05,.1])
def test_margins_and_baseline_binary_icc_are_matched(baseline,icc):
    model=power.parameters(baseline,.1,icc,.1)
    assert model['feasible']
    assert abs(model['quadrature_marginal_baseline']-baseline)<1e-9
    assert abs(model['quadrature_marginal_target']-(baseline+.1))<1e-9
    assert abs(model['induced_baseline_icc']-icc)<1e-9


def test_impossible_discordance_is_not_silently_clipped():
    assert not power.parameters(.85,.1,.1,.3)['feasible']
    with pytest.raises(ValueError):power.parameters(.95,.1,0,.1)


def test_batch_pvalues_match_original_exact_enumeration():
    rows=np.array([[1,1,1,1,1,1],[1,1,1,1,1,-1],[0,1,1,1,1,1],[0,0,0,0,0,0],[.1,.2,-.3,.4,.1,-.2]])
    assert np.allclose(power.exact_p_batch(rows),[exact_two_sided_p(row) for row in rows],rtol=0,atol=0)


def test_joint_probabilities_and_sampled_margins():
    model=power.parameters(.85,.1,.1,.14)
    probabilities=power.probabilities(np.array([-10.,0.,10.]),model)
    assert np.all(probabilities>=0) and np.allclose(probabilities.sum(axis=-1),1)
    result=power.simulate(baseline=.85,effect=.1,icc=.1,discordance=.14,seeds=2,replications=5000,random_seed=17)
    assert abs(result['empirical_generator_baseline']-.85)<.005
    assert abs(result['empirical_generator_effect']-.1)<.003
    assert abs(result['empirical_generator_discordance']-.14)<.003
