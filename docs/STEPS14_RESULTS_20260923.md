# Steps 1–4: results and outstanding acceptance gates

Status: **engineering investigations completed; all four steps are not scientifically
complete**. No primary protocol has been frozen or primary collection launched.

## Step 1: localization

Replayed all 23 intact development frames in the fixed 24-slot panel. Twenty
frames provide x/y/height depth-plane consistency within the existing 0.03 m
tolerance; three do not expose enough planes. Largest observed component residual
is 0.009337 m. The historical plane check's `verified` flag permits height-only
support; the new report explicitly distinguishes all-axis support. Model-initialized
wall matching is a consistency check, not independent rigid-pose truth.

Recorded nominal TF differs from the rendering-camera translation by about
0.13709 m. Implemented a separate R3 candidate correction:
`T_map_render = T_map_nominal inverse(T_base_nominal) T_base_render`.
Tests cover nonzero base roll/pitch/yaw and reject nonrigid transforms. The corrected
recorded transforms agree with commanded rendering-camera transforms to numerical
precision on this stationary panel. This is not an independent ground-truth pose
measurement. Current URDF bytes are pinned, but their historical capture-time bytes
were not independently bound. No live provider or historical transforms changed.

Remaining: bind actual sensor/robot descriptions at capture, independently verify
pose including orientation, and validate the predicted landmark reference point.
Visible wall/surface consistency alone does not satisfy the landmark 0.35 m rule.

## Step 2: detector feasibility

Tested exactly one fixed short-query alternative against the original prompts,
with identical images/model/threshold and all failures retained. Saved logits,
boxes and an independent output reconstruction. No best-case frame selection.

| Display query | Original | Short query |
| --- | ---: | ---: |
| Chair | 9 | 7 |
| Doorway | 0 | 0 |
| Laboratory entrance | 31 | 0 |
| Office entrance | 43 | 7 |
| Sign | 1 | 17 |
| Background | 9 | 14 |
| Total | 93 | 45 |

Doorway maximum score, even before cross-query argmax, is 0.054057 originally
and 0.062962 with short prompts, both below the unchanged 0.1 threshold. Thus
argmax competition is not sufficient to explain the missing doorway outputs,
and this short-prompt change does not solve them. Counts are proposals, not
accuracy or distinct verified objects. No candidate is selected or admitted.

Reporting correction: initial `detector_score_audit.json` used the new sorted
query order for the old run's insertion-ordered columns. It is superseded by
`detector_score_audit_v2.json`, which reconstructs every emitted label using each
run's actual query order. Raw inference outputs are unchanged. A regression test
covers this mismatch. `primary_protocol_gate_v2.json` supersedes the v1 gate and
references the corrected audit.

## Step 3: confidence

All displayed scores in both panels are below 0.5 (largest any-query score is
0.410282 in the short-query panel). Medium/high raw coverage bins remain empty.
Positive temperature preserves the side of 0.5; numerical tests confirm this.
This proves incompatibility of these *observed panels* with unchanged raw-bin
coverage, not impossibility for every future detector/image distribution.
Matching scores also lack a demonstrated joint category/instance/reference-point
probability interpretation. No scores were stretched, relabeled or fitted.

Remaining: establish a defensible observation-confidence model, with a specific
prospective amendment if a supervised joint score or different family is needed.
Genuine new-prediction labels cannot be substituted by old-provider verdicts.

## Step 4: collection protocol

Prepared `REVISED_PRIMARY_PROTOCOL_DRAFT_20260923.md`, specifying the observation
contract, required exact schedule fields, partition isolation, duplicate/failure
accounting, unchanged coverage, and reviewer-held validation release. The
machine-readable readiness record explicitly has `execution_allowed=false` and
`scientific_freeze=false`. The exact supported method and primary budget cannot
be honestly frozen while Steps 1–3 lack acceptance evidence.

## Next necessary work

Continue with separately versioned detector/observation-model development and an
independent pose/reference-point validation design. Do not request bulk labeling
of this failed panel, reopen validation, or run primary capture to fill quotas.
No new generic authorization is required for ordinary scoped development; exact
scientific method changes and actual protocol/model admission remain human gates.

The investigation skill led to testing specific hypotheses before changing any
frozen method, and preserving the negative result rather than lowering thresholds.

Evidence directory: `reports/steps14_feasibility_20260923_v1/`.
Final verification: 1,163 tests passed, one skipped, zero failures/errors. One
existing synthetic-depth warning remains. All 112 pinned diagnostic inputs and
the unchanged v8 frozen instrumentation snapshot verify; `git diff --check` passes.
Official model-interface reference consulted:
https://huggingface.co/docs/transformers/model_doc/owlv2
