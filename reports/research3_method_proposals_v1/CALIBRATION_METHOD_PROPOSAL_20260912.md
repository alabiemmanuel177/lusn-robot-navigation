# Proposed development-only calibration protocol, pending human approval

This is a specific candidate for Emmanuel's D7 review, not an approved method or
fitted model. It does not alter the detector's reported confidence to fill coverage
bins. The existing runtime calibration artifact is pooled; class-specific artifact
and consumer support would need implementation and tests after this choice is approved.

## Family and fit

Use one temperature T per semantic class (chair, doorway, laboratory entrance,
office entrance). For a detector probability p, clip only inside numerical loss/
prediction evaluation to [10^-9, 1−10^-9], then

    q = sigmoid(logit(p) / T)

Retain raw p unchanged in all evidence and coverage tables. Fit on development
only. Do not pool the pilot, engineered diagnostic data or validation labels.
Require all existing coverage floors independently for development and validation.
No class may borrow another class's labels to hide a failed class-specific gate.
Concretely: at least one accepted binary observation per required map/class, five
correct and five incorrect per class, and five observations per class in each of
the three raw-confidence coverage bins. This implies at least 15 per class and
60 overall, but the total alone never substitutes for the individual coverage cells.

Minimize weighted binary cross-entropy:

    L(T) = −sum_i w_i [y_i log(q_i) + (1−y_i) log(1−q_i)]

Within a class give each development map equal total weight; within a map give
each represented prespecified view group equal weight; within a group give each
accepted reviewed emission equal weight. Normalize weights to sum to one. Report
both this reviewed-emission distribution and all scheduled attempts, exclusions
and nondetections. Conditioning on emitted/reviewable observations is not equivalent
to modeling sensor detection probability or deployment prevalence.

Use exhaustive deterministic scalar grid minimization over

    G = {1.0} union {exp(log(0.2) + j/1000 * log(25)) : j=0,...,1000}.

No iterative optimizer, learned intercept or additional regularization penalty.
The bounded temperature interval is a fixed constraint. For losses tied within
10^-12 of the minimum, prefer T nearest 1 on the absolute-log scale, then smaller
T. Include the identity model T=1 exactly. Record the complete grid objective and
whether a fitted value is at a boundary. Do not widen the range using validation.

Temperature scaling is deliberately restrictive: it cannot change within-class rank or
independently shift an intercept. This may fail to correct systematic bias. Failure
must be reported, not repaired by post-hoc selection of Platt or isotonic calibration.
Those remain possible separately approved alternatives, not an automatic fallback.

Background: [Guo et al., 2017](https://proceedings.mlr.press/v70/guo17a.html)
studied temperature scaling for neural-network calibration. That work does not
validate transfer to this colour-marker provider; the classwise weighting, grid
and acceptance checks here are our explicit proposed choices, not their results.

## Development diagnostics and freeze

Use leave-one-development-map-out diagnostics with the same fixed family/grid,
without selecting new settings from these diagnostics. Each fold fits only its
training maps. Apply the same class outcome/bin floors and per-map/class floor to
the nine training maps. Report a fold as unfit if any training gate fails; never
invent fold labels. An unfit diagnostic fold is reported, not silently excluded
or used to select another family; it is not by itself an added final admission gate.
Do not report successful cross-validation if some folds were silently omitted.

Fit the final candidate on all accepted development observations only after the
full 400-attempt schedule and review are accounted for. Pin the raw attempt ledger,
label journal, approved rubric, coverage audit, fitting source, class temperatures,
metric definitions and this protocol. Freeze all model/settings/selection before
requesting the reviewer-held validation decryption key. A source hash alone is
not a scientific approval; the actual development freeze must be reviewed.

## Validation and acceptance proposal

Compute each class's Brier score, ECE and MCE using the same map/view-group weighting
within the validation partition. Also report their unweighted per-emission versions.
Use exactly ten equal-width metric bins [0,.1),...,[.9,1]; report count and weight
per bin. Empty bins are absent from the maximum, not evidence of zero error.
Assign bins using the probability currently being evaluated (raw p or calibrated q).
ECE is sum_b W_b |weighted_accuracy_b − weighted_confidence_b|; MCE is the largest
occupied-bin absolute gap. Brier is sum_i w_i(q_i−y_i)^2. Macro-average the four
class Brier and ECE values; aggregate MCE is the maximum class/bin gap.
The three confidence-coverage bins [0,.5),[.5,.8),[.8,1] remain unchanged and separate
from these ten evaluation bins.

Proposed conservative point-estimate admission screen, requiring human acceptance:

- Both partitions satisfy every unchanged coverage floor and full attempt accounting.
- Validation macro Brier improves over raw confidence by more than 10^-12.
- Validation macro ECE and maximum class/bin MCE do not exceed their raw-confidence
  counterparts by more than 10^-12.
- No individual class has worse validation Brier by more than 10^-12.

The 10^-12 value is a numerical comparison tolerance, not a meaningful-effect
margin. These are engineering admission checks, not statistical proof of calibration
or downstream benefit. Four validation worlds and sparse bins can make this screen
noisy; include world-grouped sensitivity and uncertainty and disclose that limitation.
No numerical threshold is relaxed after viewing validation. A failed screen means
no admission of this candidate; changing the family or collecting a new wave requires
a new prospective decision and disclosure that this validation set was consulted.

## Nondetections, diagnostics and labels

Keep no-emission attempts as nondetections with denominators. Do not create p=0 or
an incorrect calibration label for them. Exclude unreviewable verdicts with reasons
and counts. Duplicate/ambiguous entity emissions are not resolved by choosing the
highest score. Stream overflow, missing synchronization or an unclosed observation
window is missing evidence, not verified nondetection. Retain diagnostic results
separately; they cannot satisfy primary negative quotas.

Only after independent validation and explicit human acceptance may the exact
model be frozen for the downstream campaign. This proposal does not promise that
the proposed family will pass, that covariance is calibrated or that navigation
will improve. The final comparative study remains separately gated.
