#!/usr/bin/env python3
"""Declared-grid null-size and power simulation for the world-paired sign-flip test.

Implements the feasibility items of the accepted P1 method decision: paired
binary outcomes are generated per world x condition x seed with a world random
effect, aggregated to one equal-weight paired difference per world, and tested
with the exact two-sided sign-flip test over 2^K configurations. Every grid
point, generator choice, Monte Carlo seed and simulation uncertainty is recorded.
Nuisance values are grid inputs; when nonprotected paired outcomes exist their
estimates are recorded alongside, not substituted silently. This is not a claim
about the study's achieved power.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path

import numpy as np

SCHEMA = 'research3-world-paired-power-simulation/v1'


def exact_two_sided_p(differences, tolerance=1e-12):
    values = np.asarray(differences, dtype=float)
    observed = abs(values.sum())
    configurations = np.array(list(itertools.product((-1., 1.), repeat=len(values))))
    statistics = np.abs(configurations @ values)
    return float(np.mean(statistics >= observed - tolerance * max(1., np.abs(values).sum())))


def simulate_pair_probabilities(rng, *, baseline, effect, icc, worlds):
    """Per-world success probabilities for B5 and B6 with a shared world effect on the logit scale."""
    if not 0 < baseline < 1 or not 0 <= icc < 1:
        raise ValueError('baseline in (0,1) and icc in [0,1) required')
    target = min(.999, baseline + effect)
    sigma2 = icc * (math.pi ** 2 / 3) / max(1e-9, 1 - icc)
    world_effect = rng.normal(0., math.sqrt(sigma2), size=worlds)
    logit = lambda p: math.log(p / (1 - p))
    inv = lambda z: 1 / (1 + np.exp(-z))
    return inv(logit(baseline) + world_effect), inv(logit(target) + world_effect)


def simulate_world_differences(rng, *, baseline, effect, icc, discordance, worlds, conditions, seeds):
    """Paired binaries with prescribed marginal rates and within-pair dependence via discordance."""
    p5, p6 = simulate_pair_probabilities(rng, baseline=baseline, effect=effect, icc=icc, worlds=worlds)
    differences = np.zeros(worlds)
    for w in range(worlds):
        a, b = float(p5[w]), float(p6[w])
        # Joint distribution with margins a, b and P(discordant) = discordance when feasible.
        lower, upper = abs(a - b), min(a + b, 2 - a - b)
        d = min(max(discordance, lower), upper)
        p11 = (a + b - d) / 2
        p10 = a - p11
        p01 = b - p11
        p00 = 1 - p11 - p10 - p01
        probabilities = np.clip([p11, p10, p01, p00], 0., 1.)
        probabilities /= probabilities.sum()
        draws = rng.choice(4, size=conditions * seeds, p=probabilities)
        y5 = np.isin(draws, (0, 1)).astype(float)
        y6 = np.isin(draws, (0, 2)).astype(float)
        differences[w] = (y6 - y5).mean()
    return differences


def run_grid(*, worlds, conditions, seeds, alpha, effect, baselines, discordances, iccs, replications, seed):
    rng = np.random.default_rng(seed)
    rows = []
    for baseline, discordance, icc in itertools.product(baselines, discordances, iccs):
        rejections = {}
        for label, true_effect in (('null', 0.), ('alternative', effect)):
            count = 0
            for _ in range(replications):
                differences = simulate_world_differences(rng, baseline=baseline, effect=true_effect, icc=icc,
                                                         discordance=discordance, worlds=worlds,
                                                         conditions=conditions, seeds=seeds)
                if exact_two_sided_p(differences) <= alpha:
                    count += 1
            rate = count / replications
            rejections[label] = dict(rate=rate, monte_carlo_se=math.sqrt(rate * (1 - rate) / replications))
        rows.append(dict(baseline_completion=baseline, paired_discordance=discordance, world_icc=icc,
                         ceiling_limited=baseline + effect > .999, null_size=rejections['null'],
                         power=rejections['alternative'], reaches_target_power=rejections['alternative']['rate'] >= .8))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worlds', type=int, default=6)
    parser.add_argument('--conditions', type=int, default=8)
    parser.add_argument('--seeds', type=int, default=1)
    parser.add_argument('--alpha', type=float, default=.05)
    parser.add_argument('--effect', type=float, default=.10)
    parser.add_argument('--baselines', type=float, nargs='+', default=[.3, .5, .6, .7, .8, .85])
    parser.add_argument('--discordances', type=float, nargs='+', default=[.1, .2, .3, .4])
    parser.add_argument('--iccs', type=float, nargs='+', default=[0., .1, .3])
    parser.add_argument('--replications', type=int, default=2000)
    parser.add_argument('--seed', type=int, default=20260912)
    parser.add_argument('--nuisance-estimates', type=Path, help='optional JSON of empirical nonprotected estimates to record')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    rows = run_grid(worlds=args.worlds, conditions=args.conditions, seeds=args.seeds, alpha=args.alpha,
                    effect=args.effect, baselines=args.baselines, discordances=args.discordances, iccs=args.iccs,
                    replications=args.replications, seed=args.seed)
    minimum_p = 2 / 2 ** args.worlds
    payload = dict(schema_version=SCHEMA, worlds=args.worlds, conditions=args.conditions, seeds=args.seeds,
                   alpha=args.alpha, target_effect=args.effect, target_power=.8, monte_carlo_seed=args.seed,
                   replications=args.replications, minimum_attainable_two_sided_p=minimum_p,
                   rejection_possible_at_alpha=minimum_p <= args.alpha,
                   generator='world logit random effect (variance from ICC on the logistic scale), paired Bernoulli '
                             'with prescribed margins and discordance, equal condition and seed weights, exact sign-flip test',
                   grid=rows, max_power=max(r['power']['rate'] for r in rows),
                   any_grid_point_reaches_target=any(r['reaches_target_power'] for r in rows),
                   nuisance_estimates=(json.loads(args.nuisance_estimates.read_bytes()) if args.nuisance_estimates else None),
                   evidence_scope='declared-grid simulation; not achieved study power; nuisance values are inputs unless an estimate file is bound',
                   method_approved=False, protected_outcomes_read=False)
    with args.output.open('x') as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
    print(json.dumps({k: payload[k] for k in ('worlds', 'seeds', 'minimum_attainable_two_sided_p', 'max_power', 'any_grid_point_reaches_target')}))


if __name__ == '__main__':
    main()
