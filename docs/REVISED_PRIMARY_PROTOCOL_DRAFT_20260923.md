# Revised primary protocol: readiness specification, not a freeze

Status: **blocked, non-executable**. This document replaces neither the accepted
P2 method nor any historical evidence. The old 560-attempt schedule and later
2,016-attempt lighting proposal are not automatically approved schedules for the
new catalogue-blind detector. No generic instruction is recorded as approval of
unseen results, new labels or validation key release.

## Observation contract to establish before primary capture

- Category must come from RGB model evidence, never palette/catalogue identity.
- Box, depth support, map transform and reference-point convention must be bound
  to source/configuration hashes. Missing or mixed depth remains unresolved.
- Retain all same-class instance hypotheses; no nearest-instance truth shortcut.
- Declare duplicate suppression and emission units prospectively. Overlapping
  boxes must not count as independent successful landmark observations.
- Keep raw matching score and eventual joint correctness probability distinct.
  The latter targets correct category AND claimed instance AND planar reference
  consistency under the existing 0.35 m rubric. Catalogue yaw is metadata only.
- No emission, infrastructure failure and human unreviewable remain distinct;
  none becomes a fabricated negative label.

## Confidence decision required

The accepted no-intercept temperature family is preserved, not silently replaced.
For every T>0, sigmoid(logit(p)/T)<0.5 whenever p<0.5. Thus temperature cannot
convert uniformly low matching scores into high joint probabilities. Nor does
it change the *raw* confidence coverage bins used by the approved policy.

A separately reviewed proposal may introduce a supervised joint-score model
upstream of calibration. That would require genuine development-only labels of
the new predictions, separate score-learning and calibration samples, fixed
features/objective/regularization, and no validation feedback in either stage.
The original 397 labels cannot automatically label new boxes or hypotheses.
Do not adopt an intercept, rescale scores, or choose thresholds solely to fill
coverage bins. No such new family, training labels or learned model is approved
by this draft. An alternative is a detector whose native confidence contract is
demonstrably suitable; that too requires evidence, not merely an API field name.

## Required contents of the eventual exact primary manifest

1. Frozen detector/model/prompts, score definition, depth/transform/association
   implementation, runtime dependencies and SHA-256 inventory.
2. Explicit target distribution, all map IDs, views, lighting, simulator seeds,
   ordered attempts, frame-selection rule and fixed budget. No outcome-driven
   additions/replacements/early completion. Geometry-faithful R3-only worlds.
3. Development maps 1–10 and matched untouched calibration-validation maps 11–14;
   declare any extra score-learning split before labels. Reserved navigation
   worlds 15–20 stay inaccessible. A changed distribution needs matched new
   validation, not reuse of old validation selected using its outcomes.
4. Every dispatched failure retained, resource stops distinguished, all emitted
   and nonemitted denominators preserved. Serial/low-priority resource-guarded
   execution until a separately checked concurrency plan is admitted.
5. All development and validation review packages separately hash-bound. Reviewer
   retains validation plaintext/key; development model freeze and human release
   authorization precede decryption. Do not open the existing sealed return.
6. Pilot/design/engineered diagnostics excluded from primary quotas and fitting.
   Coverage v2 unchanged in each partition: >=1 accepted per map/class, >=5
   correct and >=5 incorrect per class, >=5 per raw-confidence bin [0,.5),
   [.5,.8), [.8,1]. Do not count repeated boxes as independent landmarks.
7. Exact approved fit/diagnostic/validation acceptance criteria, fit failure
   policy, model freeze evidence, and eventual navigation-distribution alignment.

## Freeze condition

All localization, four-class feasibility and confidence decisions must be
supported by actual development evidence before the exact schedule is reviewed.
Then obtain substantive human protocol approval bound to the manifest/document
hashes. Until then `primary_protocol_gate.json` explicitly refuses execution and
freeze. This draft completes preparation of the requirements, not Step 4's
scientific freeze or Steps 1–3's empirical acceptance.
