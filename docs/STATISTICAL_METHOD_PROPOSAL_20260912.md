# Proposed world-paired inference, pending human review

Human inputs: B6−B5 ordered completion, +0.10 absolute target effect, two-sided
alpha 0.05, power target 0.80. Other contrasts/endpoints remain exploratory.
These are design choices, not achieved results. A +0.10 ordered-completion effect
does not by itself mean one fewer catastrophic collision per ten missions, nor
establish a clinical benefit. Safety outcomes must be measured separately.

## Estimand and unit

For each world, compute the B6−B5 difference in completion rates using equal
weights over all eight conditions and equal weights over the frozen simulator
replications within each condition. Average these differences equally across
worlds. Preserve pairing by world, condition and seed. The world is the independent
unit; pixels, views, route variants and simulator repetitions are not extra worlds.
Retain unknown endpoints and compute paired best/worst bounds, rather than silently
removing missing episodes. The single primary null is zero effect; +0.10 is the
planning alternative, not a claim that rejecting zero proves a gain of at least 0.10.

## Candidate primary test

Evaluate an exhaustive two-sided world-level sign-flip test of the mean paired
difference. Its validity requires independent world-level contrasts and justified
sign exchangeability under the null (for example an appropriate randomized design
or a defensible symmetry assumption). Running each system on each world does NOT
by itself prove that assumption. This is not automatically an exact causal test.
Before approval, the proposal must document the procedural-world sampling mechanism,
system execution randomization and whether the required null is defensible.

At K=6 there are 2^6=64 sign configurations. For a nonzero absolute-mean statistic,
each configuration has a sign-reversed partner; the smallest attainable exhaustive
two-sided p-value is 2/64=0.03125. The next possible value is 4/64=0.0625, already
above 0.05. With only five effective nonzero contrasts the minimum is 0.0625.
These arithmetic constraints do not establish power or universal validity. Ties
can make the attainable minimum larger. No Monte Carlo approximation is needed
for six worlds; ties count as at least as extreme.

The accompanying analytic sensitivity script shows that, under independent nonzero
contrasts with a common positive-sign probability pi, rejection at alpha .05 occurs
only when all six signs agree. Its conditional probability is pi^6+(1−pi)^6.
Reaching 0.80 under those assumptions requires pi about 0.96349. This is NOT the
study's estimated power: the +0.10 completion target does not determine pi, and
binary-rate contrasts can have zeros/ties. The report leaves empirical nuisance
estimates and empirical power null rather than substituting this illustration.

SciPy documents paired sample reassignment and sign flipping under its paired
permutation null: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html
The discrete counts above are direct enumeration, not an empirical power estimate.

## Methods not selected by name alone

GEE and cluster-robust asymptotic intervals are not proposed as the default with
only six independent worlds. A wild-cluster bootstrap is not an automatic cure
for small K. Any proposed correction must specify its statistic, reference
distribution, leverage treatment and demonstrate null-size behavior under a
prespecified simulation grid. A paired world bootstrap can be a sensitivity
analysis but must not manufacture extra independent units. No method in this
paragraph has been approved or implemented as the study's final inference method.

## Feasibility work owed before freeze

1. Obtain nonprotected, paired B5/B6 navigation outcomes under fixed configurations.
   Stationary perception captures and the 60 labels are not navigation power data.
2. Estimate baseline completion, paired discordance and between/within-world
   dependence, with uncertainty and missingness. Keep the empirical values absent
   until such outcomes exist; do not infer them from the desired effect.
3. Simulate both null behavior and power for the +0.10 alternative across a declared
   sensitivity grid, documenting paired binary generation, cluster heterogeneity,
   condition weighting, seed count, Monte Carlo seed and simulation uncertainty.
   Include the feasibility constraints that a baseline above 0.90 cannot increase
   by 0.10 and that dependence/discordance choices must define valid probabilities.
4. Compare the target 0.80 power with sensitivity results. Increasing seeds improves
   within-world precision but cannot remove K=6 inferential constraints.
5. Present the exact final method, interval construction, replication list and
   achieved/plausible power to Emmanuel for approval BEFORE held-out access.

If feasibility or assumptions fail, obtain the explicit prospective descriptive/
exploratory designation before examining held-out outcomes. Do not choose the
confirmatory label or statistical method according to the held-out result.

Status: proposal for review. No nuisance estimates, power success, final method,
confidence interval, final sample size or protected access are approved here.
