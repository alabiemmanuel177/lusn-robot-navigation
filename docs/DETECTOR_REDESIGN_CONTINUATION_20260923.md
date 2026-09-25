# Continued detector, confidence and localization engineering

Work continued directly through detector inference, audit, depth integration and
a second fixed geometric hypothesis. No additional generic approval was requested.

## Alternative detector completed

Grounding DINO tiny, official revision a2bb814dd30d776dcf7e30523b00659f4f141c71,
completed the original 24-slot panel: 23 intact development images and one retained
historical source failure. Two incompatible legacy checkpoints were rejected before
any image dispatch. The successful checkpoint passed strict complete-weight loading.
The investigation skill enforced that compatibility check rather than permitting
randomly initialized missing layers to produce misleading detector results.

All 850 proposals reconstruct from saved raw logits/boxes/token IDs:

| Exact phrase category | Proposals |
| --- | ---: |
| Chair | 13 |
| Doorway | 37 |
| Laboratory entrance | 15 |
| Office entrance | 5 |
| Sign | 38 |
| Background | 61 |
| Incomplete/mixed/empty phrase, unresolved | 681 |

This candidate produces proposals in all four classes, unlike the tested OWLv2
panels. Counts are not accuracy, verified identities, unique objects or primary
coverage. Chair scores occupy all three raw bins (6/3/4); every other navigation
class remains entirely in the low bin. No candidate is admitted.

Source/results: `reports/grounding_candidate_20260923_v3/`.
The upstream model interface is documented at
https://huggingface.co/docs/transformers/v4.57.1/model_doc/grounding-dino.

## Continued directly into depth/association

Retained all 850 proposals: 681 unresolved text hypotheses, 99 non-navigation,
42 mixed-depth abstentions, 26 unmatched and two unique geometric candidates.
Both unique matches are doorway hypotheses; distances 0.86310 and 0.76581 m are
outside the unchanged 0.35 m reference radius. Thus two geometric matches do not
establish two successful navigation observations.

Then fixed and ran the side-of-opening depth hypothesis on all 57 portal-class
proposals, not a selected successful subset. Results: five unique candidates,
38 side-disagreement abstentions, 13 unmatched and one insufficient-depth case.
Three doorway candidates fall within 0.35 m of a same-class reference. No lab or
office entrance does. These are necessary geometric checks, never human labels;
the all-class localization requirement remains unmet. Preserve the original
central-depth outputs and this negative/partial result.

Source/results: `reports/portal_depth_candidate_20260923_v1/`.

## Independent work completed while inference ran

- Implemented an exact synthetic-only joint-score prototype: four operational
  features plus intercept, weighted logistic loss, fixed L2 penalty, deterministic
  solver and explicit real-data rejection. Nine tests cover gradients, convergence,
  provenance rejection and feature limits. No real observations were fitted.
  See `JOINT_SCORE_METHOD_CANDIDATE_20260923.md` for the prospective method, not an
  approval or promise of calibration coverage.
- Prepared independent pose preflight validation: exact synchronized simulator
  truth, capture-time source binding, rigid-transform checks, separate position
  and orientation errors. Six tests reject commanded/localization substitutes,
  timestamp mismatch and missing binding. No new live ground-truth capture ran.
  See `INDEPENDENT_POSE_PREFLIGHT_CANDIDATE_20260923.md`.
- Added and tested the portal-side estimator without modifying any frozen source.

## Honest remaining work

Four-class reference-point localization and independent live pose validation are
still open. The proposed joint score needs a reviewed method and separate genuine
development score-learning data before any real fit; existing pilot/provider
labels cannot be reassigned to these predictions. Raw confidence coverage is not
solved by this candidate. Primary protocol freeze, validation release and campaign
admission stay closed. Do not ask for bulk labeling of this failed feasibility
panel or treat generic development permission as model/result approval.

No R1/R2 code, scene geometry, frozen provider, historical labels, protected worlds
or sealed validation data were changed/accessed. All launched inference jobs are
complete; this record does not imply unattended background research continues.

Final verification: **1,184 passed, 1 skipped**, zero failures/errors; one existing
synthetic-depth warning. All 59 portal replay input hashes verify. Frozen v8
instrumentation validates unchanged and `git diff --check` passes.
