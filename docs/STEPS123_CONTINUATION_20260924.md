# Steps 1–3: evidence and remaining admission gates

## 1. Entrance localization: narrow engineering candidate now works

The accepted reference point is the original side-mounted sign, **not** the
doorway centre or the added readable text. `world/physical.py` places it at
`(door_x + 0.53, side * (half_width + 0.30))`. The readable-world builder places
corridor text at `(door_x, side * (half_width - 0.10))`. These are different
measurement conventions; a correct opening estimate can fail the 0.35 m rule.

The fixed 24-slot development panel retains one historical infrastructure failure
and 23 images. Full-scene RapidOCR 1.4.4 produces ten exact LAB/OFFICE tokens.
No fuzzy spelling correction, palette, expected target or catalogue identity is
used in OCR. Package/model bytes and settings were pinned before inference.
The runtime uses CPU threads only. Installation did not change the frozen model
environments or system packages.

Alternative results are preserved, not selectively discarded:

- Doorway plus OCR context: 12 contextual hypotheses; none within the entrance
  reference radius after the prior paired-side-depth localization.
- Generic sign box plus unique scene context: 14 geometric candidates;
  reference distances 0.513–0.697 m; none within the radius.
- Text-box depth plus the **explicit authored reference conversion**
  `(x + 0.53, y + sign(y)*0.40)` for corridor-side views: ten unique geometric
  candidates, all within the unchanged radius (nine lab, one office).

The last conversion is derived from source construction, not fitted offsets.
It is intentionally restricted to this authored corridor template. It cannot
be represented as a general-world learned entrance detector. Text can occur on
non-entrance signs; structural identity and ownership still need human review.
No human verdicts, probability estimates, calibration admission or bulk-review
request follow from the distance screen. Historical replay still uses assumed
stationary rendering pose; the new live checks do not retroactively certify it.

Evidence: `reports/entrance_context_candidate_20260924_v1/`,
`reports/sign_reference_candidate_20260924_v1/`,
`reports/readable_reference_candidate_20260924_v1/`.

## 2. Independent live pose preflight: bounded check completed

Four serial stationary development views ran with actual simulator model-pose
messages, exact timestamps and retained launch-time expanded SDF, state-publisher
URDF, bridge configuration, world and source hashes. Ground truth was subscribed
to only by the separate evaluator. No navigation goal was dispatched.

All 80 context RGB-D frames were audited, not just matching successes:

| Acquisition view | Exact RGB-D/TF/truth comparisons | Missing truth | Missing TF |
| --- | ---: | ---: | ---: |
| Doorway | 2 | 11 | 7 |
| Office entrance | 5 | 10 | 5 |
| Laboratory entrance | 3 | 7 | 10 |
| Chair | 1 | 10 | 9 |

All 11 comparisons pass <=0.03 m / <=1 degree: maximum translation error
0.010902 m (rounded up), maximum angle about 0.327 degrees. All media hashes and
capture-time source hashes verify. The 69 unavailable comparisons are missing
evidence, not successes. This supports the stationary mount correction in these
four views, not dynamic navigation, universal pose accuracy or full-object pose.

The first instrumentation batch is retained as v1: one incomplete 100-pair
observer and three occupied-domain failures. V2 used a fixed 20-pair observer
and separate domains 81–84. No original evidence was overwritten. The independent
audit uses every context frame and the complete truth journal, not an
outcome-selected subset of observer rows.

Evidence: `reports/independent_pose_live_20260924_v2/independent_audit.json`.
Resource samples retained per view: minimum available memory >22.8 GiB, maximum
CPU pressure avg10 0.54. These guards do not prove zero performance interference.

## 3. Joint confidence: exact prototype available, real fitting still gated

`JOINT_SCORE_METHOD_CANDIDATE_20260923.md` specifies the class-specific weighted
logistic objective, intercept, fixed penalty, deterministic optimizer and input
features. Its synthetic numerical tests pass. Real-data provenance is rejected
by the prototype. A detector or OCR matching score is not presented as joint
category/instance/reference-point correctness probability.

No real model can honestly be finalized from these results: the new candidate
has no new human joint labels, and the authored-template reference conversion
is not an approved primary observation model. Existing labels cannot be attached
to changed boxes. Coverage floors, held-out validation sequestering and the
approved temperature protocol remain unchanged.

Before any score-learning collection or primary freeze, the method decision must
explicitly choose whether to admit the authored-template measurement model. If
admitted, the exact per-class detector/support features and a disjoint fixed
score-learning schedule must be prospectively reviewed. General-scene claims
instead require a detector that independently localizes the intended reference
object, not this authored offset. These alternatives are scientifically different.

This is **not completion of all three scientific gates**. Steps 1 and 2 now have
bounded engineering evidence; Step 3 has tested numerical preparation, not a
fitted or validated model. No validation plaintext or protected world was opened;
Research 1/2 source files and frozen v8 instrumentation were not modified.

Final verification: **1,192 passed, 1 skipped**, no failures/errors, with the
existing synthetic-depth warning. Report:
`reports/steps123_regression_20260924_v2.xml`. `git diff --check` and the original
v8 snapshot validator pass. All launched live/OCR/test jobs have finished.
The specific human scope decision is prepared in
[REFERENCE_METHOD_DECISION_20260924.md](REFERENCE_METHOD_DECISION_20260924.md).
