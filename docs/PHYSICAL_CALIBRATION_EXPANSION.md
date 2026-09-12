# Proposed amendment R3-CA-20260911-01

Status: **draft awaiting human review; no collection or calibration authorized**.

This responds to the user-supplied anonymous protocol review dated 11 September
2026. The review supports the rubric and recommends additional calibration data.
It is a protocol-level recommendation, not a signed per-observation journal,
authenticated reviewer identity, or blanket approval of an expansion schedule.

The kit's confidence-bin counts were independently checked: chair 0/5/10;
doorway, laboratory entrance and office entrance each 0/1/14 for bins
[0, 0.5), [0.5, 0.8), [0.8, 1]. The narrative's 14-correct/1-incorrect counts
per class remain **unverified as human labels** until the actual review return
is received and validated. They must not be inserted into calibration data.

## Phase 1: finish the pilot human review

Keep all 60 targets and their raw evidence. Use the published kit to record the
three explicit judgments and notes. Preserve its original files and append-only
review history. Assess whether category, instance association and position can
actually be judged; count missing/unreviewable dimensions rather than silently
discarding difficult cases. Describe any rubric revisions and require a new
approval before applying them. Do not claim inter-rater reliability from one
human or from assistant presentation checks.

Retain the 0.35 m inclusive **reference-point consistency** criterion. It is not
full-object geometry localization accuracy. Retain the 1e-6 rad yaw check only
for copied catalogue metadata; it does not measure orientation estimation.
Joint correctness is false if any dimension is incorrect, true only if all are
correct, otherwise unreviewable. The review recommendation supports these rules;
an authorized human still supplies the recorded operational approval.

The amendment proposes excluding the existing pilot from both the final fit and
the final validation panel. Its legitimate role is rubric/interface/distractor
development, not calibration certification. This is an explicit proposed use
restriction, not deletion or relabeling of the pilot.

## Phase 2: fixed prospective collection proposal

| Panel | Proposed schedule | Use |
| --- | --- | --- |
| Unmodified-world development | 10 maps × 4 classes × 5 views × 2 simulator seeds = 400 attempts | Candidate fitting after genuine labels and separate fit-protocol approval |
| Unmodified-world validation | 4 other maps × 4 classes × 5 views × 2 seeds = 160 attempts | Untouched validation; never used to fit or select a calibrator |
| Engineered diagnostic | 10 development maps × 4 classes × 2 treatments = 80 attempts | Diagnostic only; cannot fill primary negative quotas |

The primary schedule is enumerated in
`reports/calibration_expansion_proposal_20260911_v2/plan.json`.
All **560** proposed primary poses pass the existing conservative 0.30 m footprint
check on the current maps. This establishes static map clearance only, not
visibility, successful detection, sufficient confidence spread or navigation safety.

Five views use original x, x−0.5, x+0.5, x+1, and a farther along-corridor position:
x+2 for chairs, x−2 for doorway/entrance targets. Nonzero offsets face the claimed
catalogue target. The zero-offset pose is preserved. These provide a fixed range
of distances and oblique views; views through existing structures may occlude
targets. They are not selected by confidence or correctness. Existing repeated
entrances can expose ambiguity; a world with only one chair does not establish
repeated-chair performance. Any added confuser belongs to the engineered panel.

An earlier x+2-for-all proposal produced 84 failed footprint checks near corridor
ends. It remains in `reports/calibration_expansion_proposal_20260911_v1/`, with its
exact amendment input retained. The revised sign was chosen using map clearance
before approval, not detection scores or labels. Do not execute the older draft.

The 80 diagnostic attempts specify a visual occluder covering a nominal 20% of
target projected area, or a same-colour non-landmark distractor. These derivatives
are **not yet built or preflighted**. Exact visual geometry, image evidence and
source hashes must be reviewed before this panel is approved. Preserve collision
geometry and catalogue IDs. Do not silently recategorize these as naturally
occurring failures or pool them into a deployment-prevalence calibration claim.

## Low-confidence and error sampling

Do not lower reported scores, change calibration temperature, move catalogue
reference points, or insert correctness labels to fill cells. Preserve the current
provider score formula, profile/palette/thresholds, association radius, FOV and
source snapshot. The provider's support, colour and spatial terms can produce
values below 0.5, but the proposed real views may still not do so often enough.
That is an empirical limitation to report, not grounds to manipulate scores.

For each scheduled attempt, retain the earliest synchronized frame and all its
observations. Select the prespecified entity in that frame without consulting its
confidence or future human verdict. Retain absent-target cases as nondetections;
do not invent a confidence or treat no emission as a negative calibration row.
Retain all raw rows, failures, incorrect associations and metric errors. Confidence
and error strata are computed only during the subsequent coverage audit.

The two seeds repeat a map/view group; they are not independent worlds. Report
grouped counts and uncertainty. Equal scheduled map/class/view weighting defines
an experimental mixture, not the frequency of conditions in deployment. Changing
viewpoint is deliberate sampling, so even unmodified-world errors must not be
described as an unbiased sample of real-world failures.

## Preserve coverage and define stopping

The original numeric requirements remain unchanged: at least one accepted binary
observation per required map/class; at least five correct and five incorrect per
pooled class; at least five per class/confidence bin with edges [0, 0.5, 0.8, 1].
Unreviewable items remain excluded with counts/reasons, not converted to negatives.

Apply those floors separately to development and validation as a **new proposed
safeguard requiring approval**. They remain modest coverage gates, not proof of
precision, stable fitting, calibration efficacy or navigation benefit. Choose the
calibration family/hyperparameters before examining validation outcomes. Never
fit on validation or use engineered diagnostics to manufacture primary negatives.

Finish the fixed schedule; do not stop on a favorable class balance or add
unbounded repetitions until a result looks acceptable. A verified pre-dispatch
infrastructure failure may have one separately named retry, with the original
retained. Never replace a completed result. If coverage is unmet after genuine
review, freeze remains blocked. Any additional wave needs a new prospective
amendment and disclosed use of development evidence; do not silently revise these
thresholds or tune against the held-out validation results.

## Approvals and remaining gates

Machine-readable draft:
`configs/physical_calibration_expansion_amendment_v1.yaml`.
Pending accept/revise/reject form:
`reports/calibration_expansion_proposal_20260911_v2/review.template.json`.
The form pins the exact draft and plan; no identity, date, acceptance or labels
have been filled on behalf of a human. A completed form alone cannot launch work.

Before collection: receive and validate the Phase 1 return, audit rubric usability,
approve the coverage and amendment, finish diagnostic asset/pose checks, and pin
all execution inputs. Run development before untouched validation. Keep R3 serial,
low priority and resource guarded; do not alter R1/R2 jobs. Protected maps, final
campaign execution and calibration freeze remain separately gated.

The existing belief/verification policy and low-level costmap are unchanged.
Calibration, downstream benefit and closed-loop evaluation remain separate claims.

## Preparation tooling

`scripts/prepare_calibration_expansion.py` validates the unchanged coverage and
nonprotected map scope before reading scenes, checks exact world/profile/request
bindings, performs map-footprint preflight and writes a create-once proposal and
pending review form. It has no subprocess/ROS dispatch path and emits no runnable
execution commands. Regenerate only to a new output directory. The validation
maps correctly use their captured v3 frozen profiles, not their earlier draft
profile bytes. No captured runtime source, provider configuration or old kit has
been changed. Verification: 15 focused tests and 808 full-suite tests passed;
one sandbox socket test was skipped. An independent manifest check verified all
560 unique candidates, the 400/160 partition split and exact input/form hashes.
