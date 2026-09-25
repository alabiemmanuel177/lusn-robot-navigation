# Joint-score method candidate, not an approved amendment

Purpose: explicitly model joint category/instance/reference-point correctness,
instead of presenting a text-matching score as that probability. This is a new
observation model, not a renamed temperature calibrator. It requires prospective
human scientific review and genuinely labeled, separate score-learning data.

## Exact candidate

For each of four classes independently, fit logistic regression with intercept:
`p_joint = sigmoid(beta dot x)`. No products of marginal category/pose probabilities
or independence assumptions. Features, in fixed order:

1. Intercept 1.
2. `clip(logit(raw_matching_score)/12, -1, 1)`.
3. Fraction of valid central-box depth pixels, in [0,1].
4. `min(depth_IQR/median_depth, 1)`.
5. Distance from depth-derived point to the unique geometric instance candidate,
   divided by 0.9 m. This is an operational association feature, not a human truth
   label or an independently measured localization error.

No map ID, entity ID, colour signature, expected target class, simulator semantic
label, human verdict or catalogue yaw enters x. Ambiguous associations, missing
depth or mixed surfaces abstain before this score; no p=0 substitution. This
means the model concerns the emitted/reviewable candidate distribution, not recall.

Objective: weighted binary cross-entropy plus `(0.01/2) * sum(beta_j^2)`, including
intercept regularization. Equal-map, equal-view-group, equal-emission weights
within each class, positive and normalized. Both outcomes required. No tuning of
features or penalty using validation. Retain the original raw detector score.

Solver: zero initialization, deterministic gradient descent with step
`1/(0.25 * sum_i w_i ||x_i||^2 + 0.01)`, gradient infinity tolerance 1e-8,
maximum 20,000 updates. Nonconvergence is failure, not a solver/penalty search.
The script is deliberately a synthetic-only test harness; it refuses real-data
provenance. Tests verify analytic gradients, deterministic convergence, input
rejection and the intercept's capability on invented numerical fixtures. These
fixtures are not research observations or human labels.

## Necessary separation and remaining decisions

A new, explicitly approved score-learning wave must be disjoint at the capture
level from primary calibration and untouched validation, with all duplicates/view
groups accounted for. Historical pilot/design labels are not silently promoted.
Do not transfer old-provider labels to new detector predictions. Do not open old
validation plaintext to decide whether this model works.

Freeze this upstream model before primary calibration collection. Only then can
the accepted P2 temperature method be evaluated on its output, subject to a human
decision explicitly accepting that *new upstream probability* as the raw input
to Coverage v2. This would be a substantive observation-method amendment, not
permission to transform scores until bins fill. Preserve original matching-score
tables alongside joint scores, and do not lower existing outcome/bin/map floors.

The exact score-learning schedule and honest human review are not yet ready:
four-class detector/reference-point feasibility remains a prerequisite. No real
model has been fitted; no evidence says this family will pass coverage, calibration
or navigation tests. This prepares the implementation and specific method for
review, not an approval request to rubber-stamp a failed detector.
