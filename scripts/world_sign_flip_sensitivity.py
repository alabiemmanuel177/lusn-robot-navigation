#!/usr/bin/env python3
"""Exact six-world arithmetic sensitivity, not empirical study power."""
import argparse
import itertools
import json
import math
from pathlib import Path


def exact_pvalue(differences):
    values=list(differences)
    if not 1<=len(values)<=16 or any(type(v) not in (int,float) or not math.isfinite(v) for v in values):
        raise ValueError('one to sixteen finite world contrasts required')
    observed=abs(math.fsum(values))
    tolerance=1e-14*math.fsum(abs(v) for v in values)
    extreme=sum(abs(math.fsum(s*v for s,v in zip(signs,values)))>=observed-tolerance
                for signs in itertools.product((-1,1),repeat=len(values)))
    return extreme/(2**len(values))


def sensitivity():
    # With six nonzero independent world contrasts, alpha .05 and this absolute
    # mean sign-flip statistic, rejection requires all six signs to agree.
    rows=[{'assumed_probability_world_difference_positive':p,
           'conditional_rejection_probability':p**6+(1-p)**6}
          for p in (.5,.6,.7,.8,.9,.95,.97,.99)]
    low,high=.5,1.
    for _ in range(70):
        mid=(low+high)/2
        if mid**6+(1-mid)**6<.8:low=mid
        else:high=mid
    return {
        'schema_version':'research3-six-world-signflip-sensitivity/v1',
        'evidence_scope':'analytic_assumption_sensitivity_not_empirical_power',
        'worlds':6,'configurations':64,'alpha':.05,'target_power':.8,
        'minimum_two_sided_p':2/64,'next_attainable_p_increment':2/64,
        'five_nonzero_worlds_minimum_p':2/32,
        'assumptions':['independent world contrasts','nonzero continuous contrasts',
                       'valid null sign exchangeability','identical assumed sign probability across worlds',
                       'absolute equally weighted mean test statistic'],
        'conditional_sign_probability_sensitivity':rows,
        'required_common_positive_sign_probability_for_80_percent':(low+high)/2,
        'target_effect_to_sign_probability_mapping_estimated':False,
        'baseline_completion':None,'paired_discordance':None,'world_dependence_estimate':None,
        'empirical_power':None,'method_approved':False,'protected_outcomes_read':False,
        'limitation':'The +0.10 target does not determine a world-positive probability without a justified data model and evidence.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    with args.output.open('x') as stream:json.dump(sensitivity(),stream,indent=2,sort_keys=True)
    print(json.dumps(sensitivity(),indent=2))
