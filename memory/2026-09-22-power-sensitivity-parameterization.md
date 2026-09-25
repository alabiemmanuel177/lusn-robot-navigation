# Method investigation: power generator parameter semantics

The historical generator was not changed. Its inputs named baseline/effect/ICC
were conditional logit means and a latent-variance parameter, not marginal
binary targets; per-world discordance was clipped. Historical reports therefore
remain usable only under those exact assumptions, not as marginally matched
power estimates. The empirical nuisance ICC is itself a paired-difference ANOVA
ICC, a third distinct quantity.

New candidate code explicitly matches marginal means and B5 binary ICC, reports
infeasible discordance, and retains all grid cells. Twelve generator regression
tests cover moments, feasibility, exact sign flips and realized sampling. The
fixed grid contains 144 cells and 20.4 million simulated realizations across 204
feasible hypotheses; these are synthetic computations, not research observations.
Independent adaptive quadrature matches declared moments to <4.45e−16.

Both systems share a common random world effect in this candidate. Separate
analytic correlation sensitivity documents the resulting optimistic positive-
contrast assumption. Neither numerical verification nor high conditional power
approves a final method, a seed count, or a confirmatory designation. No protected
outcomes were used. Status: DONE_WITH_CONCERNS (empirical assumptions unresolved).
