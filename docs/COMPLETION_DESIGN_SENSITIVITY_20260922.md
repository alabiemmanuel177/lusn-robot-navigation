# Consolidated design sensitivity — proposal, not freeze

The refreshed non-executable design is
`reports/completion_design_candidate_20260922_v1/design.json`. It records the
human-selected B6−B5 primary ordered-completion endpoint, one-primary-contrast
multiplicity policy, +0.10 target improvement, alpha .05 and target power .80.
It does not select a final seed list, replication count or inference method.

Existing uncalibrated development navigation evidence has 72 complete pairs out
of 80 scheduled pairs: B5 completion .84722, B6 .73611, difference −.11111 and
paired discordance .13889. Eight incomplete pairs must remain in missingness
accounting. These are not results from a frozen calibrated comparative campaign.
The recorded ICC estimate −.13310 is preserved, not silently clipped to zero.
That historical estimate is an ANOVA ICC on paired differences, not B5 binary
ICC and not the latent-logit parameter used in the older sensitivity generator.
These three quantities must not be substituted for each other.

The scheduled-cohort audit retains all 80 pairs and reproduces 159 available
summaries from pinned telemetry/evaluator sources (one infrastructure failure has
no summary). B5 has 65 known successes, 11 known failures and four unknowns;
B6 has 56 known successes, 20 known failures and four unknowns. Equal-world,
equal-condition best/worst bounds are B5 [.8125,.8625], B6 [.7000,.7500],
B6−B5 [−.1625,−.0625], and discordance [.125,.225]. These are identification
bounds for this fixed engineering cohort, not population confidence intervals.
Sources: `reports/navigation_feasibility_audit_20260922_v1.json` and
`reports/development_navigation_recomputation_20260922_v1.json`.

For reference, the existing declared-grid simulations use six worlds, eight
conditions, a +.10 planning effect and exact world-level sign flips. At grid
baseline .85 and paired discordance .14, their conditional rejection rates are:

| Seeds per condition | Historical latent parameter 0 | Historical latent parameter .05 | Historical latent parameter .10 |
| --- | ---: | ---: | ---: |
| 1 | .0470 | .0405 | .0440 |
| 2 | .2150 | .2135 | .2095 |
| 4 | .5975 | .5360 | .4875 |
| 8 | .9025 | .8125 | .7550 |

Sources: the four `reports/world_paired_power_bound_20260914_seeds*.json` files.
Audit clarification: those historical generator inputs are not marginal binary
ICCs. The generator adds normal effects to nominal logits, so its nominal .85
baseline and +.10 difference are not preserved as marginal probabilities under
heterogeneity. It also clips requested discordance to conditional feasibility
bounds. These files are retained as historical evidence, not silently replaced.
These figures are Monte Carlo results under specified generators and assumptions,
not achieved study power or a guarantee. The full files retain simulation errors,
null rejection rates and the rest of the sensitivity grid; these selected rows
are an explicitly identified illustration near the preliminary margins, not a
new data-driven power design. Eight seeds do not meet .80 under every displayed
dependence assumption. More within-world repeats do not create more independent
worlds or remove the six-world p-value resolution limit.

At eight seeds, a five-system/eight-condition schedule would contain 4,480
nonprotected episodes across 14 worlds and 1,920 reserved held-out episodes across
six worlds. These are arithmetic counts only: neither schedule nor access is
authorized, and stationary-capture timings do not predict navigation runtime.

Final inference assumptions, replication choice, missingness treatment and
confirmatory versus descriptive designation still require prospective approval
before protected outcomes. Calibration/design gates also remain unresolved.

## Marginally matched supplemental candidate

`reports/marginal_power_sensitivity_20260922_v1/report.json` records a separately
declared 144-cell grid, with 100,000 replicates per feasible null/alternative
hypothesis, 20,400,000 total realizations and 56 infeasible alternative cells.
Infeasible requested discordance is explicitly reported, never silently clipped.
The source hashes and random seeds were recorded before execution in `protocol.json`.

At marginal B5 baseline .85, marginal B6−B5 effect +.10 and marginal paired
discordance .14, the candidate's conditional rejection probabilities are:

| Seeds per condition | B5 binary ICC 0 | B5 binary ICC .05 | B5 binary ICC .10 |
| --- | ---: | ---: | ---: |
| 1 | .03892 | .02574 | .01817 |
| 2 | .21913 | .15011 | .10740 |
| 4 | .59562 | .46029 | .34822 |
| 8 | .90917 | .79403 | .66818 |

Monte Carlo standard errors for the eight-seed row are approximately .00091,
.00128 and .00149. They quantify simulation noise only, not uncertainty in the
unknown empirical parameters or generator assumptions. The maximum simulated
null rejection rate across feasible cells is .01782. The new binary ICC
definition differs from the old latent parameter; comparisons are not controlled
replications of identical models.

The model matches marginal probabilities and B5 binary ICC by numerical
quadrature. It assumes independent worlds, eight condition replicates per seed,
conditional independence within worlds, complete outcomes and a common additive
world effect on both systems' logits. That last assumption makes every world's
true alternative contrast positive; this can be optimistic. B6 and paired
difference ICCs are reported separately rather than equated to B5 ICC.

`reports/world_effect_sign_sensitivity_20260922_v1.json` separately varies
cross-system world-effect correlation. Its analytic large-replication
sign-agreement probabilities demonstrate why more seeds do not necessarily solve
world-level effect heterogeneity. It is neither finite-sample power nor a
universal upper bound and does not fix paired discordance to .14.

Numerical implementation references: [NumPy Gaussian quadrature](https://numpy.org/doc/stable/reference/generated/numpy.polynomial.hermite.hermgauss.html)
and [multinomial sampling](https://numpy.org/doc/2.3/reference/random/generated/numpy.random.Generator.multinomial.html).
All new calculations are synthetic method-investigation evidence, not additional
research observations, achieved power, final method selection or authorization.

Independent adaptive integration verified all 204 feasible null/alternative
hypotheses against the declared marginal targets and binary ICCs, with maximum
absolute moment discrepancy 4.45e−16 (tolerance 1e−8). All 84 infeasible hypotheses
(56 alternative, 28 null) remain explicit. This validates numerical matching,
not empirical assumptions. Audit: `reports/power_numerical_audit_20260922_v1.json`.
