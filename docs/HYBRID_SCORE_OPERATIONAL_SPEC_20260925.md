# Exact hybrid candidate operationalization

Status: implemented choice within the user's repeated explicit instruction to use
near-one OR pass-through raw scores for zero-negative classes. The agent selects
**unchanged raw-score pass-through**, not near-one. This is an operational choice
under the supplied authority, not a claim the human reviewed this later document.
It supersedes the previously unresolved choice for candidate implementation only.

## Fixed mapping

- Chair, laboratory entrance, office entrance: input_score = original raw_score,
  identically, including0 and1. No smoothing, intercept, temperature, epsilon or
  confidence inflation in the upstream map. These are uncalibrated DINO/OCR
  matching scores, NOT certified probabilities of joint correctness.
- Doorway: input_score = sigmoid(beta dot x), using the already fitted five-feature
  fixed-L2 model in wave_s_doorway_amendment_candidate_20260924_v1.json. No refit,
  parameter selection or replacement of the three unfit diagnostic folds.
- Keep both original matching value and mapped input in all accounting. Missing
  or invalid inputs fail closed. Non-emissions never become probabilities/labels.
- Class selection is explicitly post-Wave-S: observed zero incorrect labels,
  at least50 emissions and ten represented development maps. No saturation claim.
  This is not the originally preregistered four-class joint-score learner.

## Candidate freeze versus scientific admission

Freeze the exact source, model, mapping and development inputs in a create-once
candidate snapshot. This records what could be evaluated next. It is NOT a
validated model, original-protocol success, human development-freeze signoff,
or an execution manifest for another wave. No C/V outcomes inform this choice.
No data-dependent alternative is silently introduced if the candidate fails.

## C/V rules retained, not quietly waived

Keep the scheduled400 C attempts/160 V attempts, serial capture, new source-bound
preflight/manifests and staged custody. Before C launch the hybrid contract must
be connected to a C-capable capture/inference adapter and independently checked;
the S-only driver's wave assertions must not be bypassed.

P2 temperature family, numerical clipping inside loss/prediction only,1001 log
grid points plus identity, weights/tie-breaking, original per-class outcome and
map floors, and three-bin floors remain unchanged. For this amended candidate,
coverage bins apply to untempered input_score; raw matching bins remain side by
side. They cannot be presented as bins of calibrated joint probabilities.

Only after complete C capture and actual human observation labels may C coverage
be evaluated and temperatures fitted. No blanket execution approval supplies
those labels. If any floor fails, report candidate failure; no bin shifting or
extra outcome-adaptive collection. Original failure remains in the study record.

V remains unopened until development freeze and required staged clearance. Human
validation labels remain with the reviewer under the accepted encrypted custody
workflow until artifact-bound release. After release, all original validation
coverage and Brier/ECE/MCE screens still apply, before any runtime admission.

The existing Wave S replay can reveal missing support but is not C/V evidence.
There is no promise this hybrid method can pass the retained gates. If it cannot,
the next decision must explicitly address study scope and admission criteria;
another generic request for autonomous completion does not establish validity.
