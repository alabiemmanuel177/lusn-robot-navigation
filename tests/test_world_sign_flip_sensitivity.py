import importlib.util
from pathlib import Path
import pytest

SPEC=importlib.util.spec_from_file_location('flip',Path(__file__).resolve().parents[1]/'scripts/world_sign_flip_sensitivity.py')
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)


def test_six_same_signs_minimum():
    assert M.exact_pvalue([.1,.2,.3,.4,.5,.6])==.03125
    assert M.exact_pvalue([-.1,-.2,-.3,-.4,-.5,-.6])==.03125


def test_mixed_signs_not_significant_at_point05():
    assert M.exact_pvalue([-.001,.2,.3,.4,.5,.6])>=.0625


def test_zero_effective_world_reduces_resolution():
    assert M.exact_pvalue([0,.2,.3,.4,.5,.6])==.0625
    assert M.exact_pvalue([0]*6)==1


def test_sensitivity_does_not_claim_empirical_power():
    report=M.sensitivity()
    assert report['empirical_power'] is None
    p=report['required_common_positive_sign_probability_for_80_percent']
    assert p**6+(1-p)**6==pytest.approx(.8)
