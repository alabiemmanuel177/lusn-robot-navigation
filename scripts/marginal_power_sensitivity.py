"""Candidate sensitivity generator with marginally matched paired binary outcomes.

Synthetic planning only. No empirical data fit, final method approval or achieved
power claim. Infeasible discordance is reported, never silently clipped.
"""
from functools import lru_cache
import itertools
import math
import numpy as np

NODES,WEIGHTS=np.polynomial.hermite.hermgauss(80)
NODES=NODES*math.sqrt(2);WEIGHTS=WEIGHTS/math.sqrt(math.pi)
LEGENDRE_NODES,LEGENDRE_WEIGHTS=np.polynomial.legendre.leggauss(80)


def sigmoid(z):return 1/(1+np.exp(-np.clip(z,-709,709)))


def intercept(mean,sigma):
    if mean==0:return -math.inf
    if mean==1:return math.inf
    lo,hi=-50.,50.
    for _ in range(90):
        mid=(lo+hi)/2
        if float(WEIGHTS@sigmoid(mid+sigma*NODES))<mean:lo=mid
        else:hi=mid
    return (lo+hi)/2


@lru_cache(maxsize=None)
def baseline_parameters(baseline,icc):
    if not 0<baseline<1 or not 0<=icc<=.5:raise ValueError('supported baseline/ICC range')
    if icc==0:return 0.,math.log(baseline/(1-baseline))
    lo,hi=0.,8.
    for _ in range(65):
        sigma=(lo+hi)/2;alpha=intercept(baseline,sigma)
        probability=sigmoid(alpha+sigma*NODES)
        induced=float(WEIGHTS@((probability-baseline)**2))/(baseline*(1-baseline))
        if induced<icc:lo=sigma
        else:hi=sigma
    sigma=(lo+hi)/2
    return sigma,intercept(baseline,sigma)


def maximum_discordance(alpha,beta,sigma,baseline,target):
    if sigma==0:return min(baseline+target,2-baseline-target)
    if target==1:return 1-baseline
    if target==0:return baseline
    # Split at p5(z)+p6(z)=1 so quadrature never spans the min() kink.
    cut=max(-12.,min(12.,-(alpha+beta)/(2*sigma)))
    total=0.
    for lo,hi,left in ((-12.,cut,True),(cut,12.,False)):
        if lo==hi:continue
        z=(hi-lo)/2*LEGENDRE_NODES+(hi+lo)/2
        margins=sigmoid(alpha+sigma*z)+sigmoid(beta+sigma*z)
        values=(margins if left else 2-margins)*np.exp(-z*z/2)/math.sqrt(2*math.pi)
        total+=(hi-lo)/2*float(LEGENDRE_WEIGHTS@values)
    return total


@lru_cache(maxsize=None)
def parameters(baseline,effect,icc,discordance):
    target=baseline+effect
    if not 0<=target<=1:raise ValueError('target marginal completion outside [0,1]')
    sigma,alpha=baseline_parameters(baseline,icc)
    beta=intercept(target,sigma)
    lower=abs(effect)
    upper=maximum_discordance(alpha,beta,sigma,baseline,target)
    if not lower-1e-10<=discordance<=upper+1e-10:
        return dict(feasible=False,reason='requested discordance outside conditional-mixture feasibility interval',
                    discordance_lower=lower,discordance_upper=upper)
    mixture=0. if upper-lower<1e-12 else (discordance-lower)/(upper-lower)
    mixture=min(1.,max(0.,mixture))  # numerical roundoff at the explicit boundary only
    p5=sigmoid(alpha+sigma*NODES);p6=sigmoid(beta+sigma*NODES)
    return dict(feasible=True,sigma=sigma,alpha=alpha,beta=beta if math.isfinite(beta) else None,mixture=mixture,
                baseline=baseline,target=target,effect=effect,discordance=discordance,
                discordance_lower=lower,discordance_upper=upper,
                quadrature_marginal_baseline=float(WEIGHTS@p5),quadrature_marginal_target=float(WEIGHTS@p6),
                induced_baseline_icc=float(WEIGHTS@((p5-baseline)**2))/(baseline*(1-baseline)),
                induced_target_icc=float(WEIGHTS@((p6-target)**2))/(target*(1-target)) if 0<target<1 else None,
                induced_paired_difference_icc=float(WEIGHTS@((p6-p5-effect)**2))/(discordance-effect**2) if discordance>effect**2 else None)


def probabilities(z,model):
    p5=sigmoid(model['alpha']+model['sigma']*z)
    p6=np.full_like(z,model['target'],dtype=float) if model['beta'] is None else sigmoid(model['beta']+model['sigma']*z)
    lower=np.abs(p6-p5);upper=np.minimum(p5+p6,2-p5-p6)
    discordance=lower+model['mixture']*(upper-lower)
    p11=(p5+p6-discordance)/2
    values=np.stack((p11,p5-p11,p6-p11,1-p5-p6+p11),axis=-1)
    if float(values.min()) < -1e-12:raise ValueError('invalid conditional joint probability')
    values=np.maximum(values,0.)
    return values/values.sum(axis=-1,keepdims=True)


def exact_p_batch(differences):
    differences=np.asarray(differences,dtype=float)
    signs=np.asarray(list(itertools.product((-1.,1.),repeat=differences.shape[1])))
    observed=np.abs(differences.sum(axis=1))
    tolerance=1e-12*np.maximum(1.,np.abs(differences).sum(axis=1))
    return (np.abs(differences@signs.T)>=observed[:,None]-tolerance[:,None]).mean(axis=1)


def simulate(*,baseline,effect,icc,discordance,seeds,replications,random_seed,worlds=6,conditions=8):
    model=parameters(baseline,effect,icc,discordance)
    if not model['feasible']:return dict(model,simulated=False)
    rng=np.random.default_rng(random_seed)
    rejected=0;total5=0;total6=0;total_discordant=0
    n=conditions*seeds
    for offset in range(0,replications,1000):
        count=min(1000,replications-offset)
        z=rng.normal(size=(count,worlds))
        draws=rng.multinomial(n,probabilities(z,model))
        differences=(draws[:,:,2]-draws[:,:,1])/n
        rejected+=int(np.count_nonzero(exact_p_batch(differences)<=.05))
        total5+=int((draws[:,:,0]+draws[:,:,1]).sum())
        total6+=int((draws[:,:,0]+draws[:,:,2]).sum())
        total_discordant+=int((draws[:,:,1]+draws[:,:,2]).sum())
    denominator=replications*worlds*n
    rate=rejected/replications
    return dict(simulated=True,model=model,replications=replications,random_seed=random_seed,
        rejection_rate=rate,monte_carlo_se=math.sqrt(rate*(1-rate)/replications),
        empirical_generator_baseline=total5/denominator,empirical_generator_target=total6/denominator,
        empirical_generator_effect=(total6-total5)/denominator,
        empirical_generator_discordance=total_discordant/denominator,
        achieved_study_power=False)
