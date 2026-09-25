import json
from pathlib import Path
import sys
import pytest
pytest.importorskip('scipy')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_power_sensitivity import independent_moments
from marginal_power_sensitivity import parameters


@pytest.mark.parametrize('b,e,i,d',[(.85,.1,.1,.14),(.75,0,.05,.2),(.9,.1,.1,.1)])
def test_independent_quadrature_matches_declared_moments(b,e,i,d):
    model=parameters(b,e,i,d)
    value=independent_moments(json.dumps(model,sort_keys=True))
    assert value['baseline']==pytest.approx(b,abs=1e-8)
    assert value['target']==pytest.approx(b+e,abs=1e-8)
    assert value['baseline_binary_icc']==pytest.approx(i,abs=1e-8)
    assert value['discordance']==pytest.approx(d,abs=1e-8)
