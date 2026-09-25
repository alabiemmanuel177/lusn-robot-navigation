# Four-class engineering readiness protocol

Authorization: explicit conversation approval in
`reports/world_specific_method_approval_20260924.json`. This is development-only
readiness, not calibration collection, label approval or protected execution.

## Fixed panels

1. Complete existing Stage A: 144 scheduled slots, 141 intact RGB-D frames,
   three historical infrastructure failures. Preserve all views, lighting levels,
   off-centre views and nondetections; no prompt or threshold changes.
2. Broader development panel: maps r001–r010, all four acquisition categories,
   seed 1, views 0 and 1 from `expansion-v1`: exactly 80 scheduled slots. Do not
   substitute a later successful capture for a missing/invalid original. These
   captures are engineering replay inputs; their original human labels are NOT
   read, copied, or used to judge changed detector boxes. No validation map read.

Grounding DINO uses the existing v3 checkpoint and fixed six-query text, box
threshold 0.1, text threshold 0.25. Stage A retains the existing one-thread
runner; the broad runner declares four CPU threads before inference. CPU-only,
low-priority, resource-guarded execution. All raw logits/boxes/tokens retained.
RapidOCR 1.4.4 settings unchanged (one CPU thread, text score 0.5), exact LAB,
LABORATORY, OFFICE only; all other text retained but not repaired.

## Initial integrated candidate (declared before panel integration)

- Chair: Grounding DINO chair box, central RGB-D surface estimate. Missing or
  mixed-depth support abstains; no colour/template category assignment.
- Doorway: Grounding DINO doorway box, paired-side-depth estimator. Disagreeing
  sides abstain. No catalogue coordinate can choose the measured point.
- Lab/office entrance: exact OCR text-box depth plus the approved authored
  reference conversion. Unsupported views/mixed surfaces abstain. Text alone
  does not certify entrance structure or identity.
- Every association keeps all same-class references within the fixed 0.9 m
  candidate radius. Multiple references remain ambiguous, never nearest-selected.
  The 0.35 m reference check is evaluation only, never used to move a prediction.
- Duplicate boxes must not count as independent observations or extra coverage.
  Readiness counts distinct frames/map/classes; all boxes remain in evidence.

## Necessary engineering gates, not accuracy certification

Complete accounting; exact source/media hashes and detector reconstruction;
explicit infrastructure/nondetection/ambiguous states; non-oracle association
tests; at least one unique candidate within 0.35 m per broad-panel map/class;
at least two distinct supporting frames per class overall. Evaluate whether
same-frame repeated doorway/entrance instances are actually exercised and report
the absence if not. Synthetic ambiguity tests are not a replacement for that
visual identity check. Chairs have only one authored instance per source world;
do not claim repeated-chair live validation.

The geometry gates are necessary, not sufficient: human category/identity review
is still required. Scores remain raw detector/OCR matching values, not joint
probabilities. Calibration floors are untouched. Failure of this first integrated
candidate is retained; any subsequent localization change needs a separate
versioned hypothesis and replay, not edits to these pinned outputs.
