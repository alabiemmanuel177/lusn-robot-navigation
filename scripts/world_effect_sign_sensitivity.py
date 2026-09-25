"""Analytic large-replication sensitivity to cross-system world-effect correlation.

Not empirical power: the correlation grid is hypothetical and not estimated.
Under paired logit-normal worlds, sign(p6-p5) has an analytic normal probability.
At six worlds and alpha .05, all six nonzero signs must agree for rejection.
"""
import itertools
import math
from marginal_power_sensitivity import baseline_parameters,intercept
from run_stage1_feasibility import ROOT,write,sha


def sign_limit(baseline,effect,icc,correlation,worlds=6):
    if not -1<=correlation<=1:raise ValueError('correlation outside [-1,1]')
    sigma,alpha=baseline_parameters(baseline,icc)
    beta=intercept(baseline+effect,sigma)
    denominator=sigma*math.sqrt(2*(1-correlation))
    if denominator==0:
        if beta==alpha:raise ValueError('degenerate zero-effect limit not supported')
        probability=1. if beta>alpha else 0.
    else:
        probability=.5*(1+math.erf((beta-alpha)/denominator/math.sqrt(2)))
    return dict(baseline=baseline,target_marginal_effect=effect,baseline_binary_icc=icc,
        cross_system_world_effect_correlation=correlation,
        positive_true_world_contrast_probability=probability,
        limiting_unanimous_sign_rejection_probability=probability**worlds+(1-probability)**worlds,
        worlds=worlds,finite_replication_power=False,empirical_parameter_estimate=False)


if __name__=='__main__':
    rows=[sign_limit(b,.1,i,r) for b,i,r in itertools.product((.75,.85,.9),(0.,.05,.1),(0.,.5,1.))]
    write(ROOT/'reports/world_effect_sign_sensitivity_20260922_v1.json',dict(
        schema_version='research3-world-effect-sign-limit/v1',rows=rows,source_sha256=sha(__file__),
        assumptions='independent worlds; two correlated normal world effects on system logits; matched marginal means; continuous nonzero alternative world contrasts',
        note='Hypothetical asymptotic sign-agreement sensitivity, not achieved power, not a universal finite-sample upper bound, and not an approved new design.',
        paired_discordance_not_fixed=True,protected_outcomes_read=False,final_method_approved=False))
    for row in rows:
        if row['baseline']==.85:print(row)
