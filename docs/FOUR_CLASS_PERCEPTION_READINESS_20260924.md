# Four-class perception: engineering readiness completed

Scope: the development-only candidate is ready for the next reviewed
score-learning/calibration protocol and observation-review preparation. This is
**not** verified human identity accuracy, calibrated runtime admission, navigation
validation or completion of Research 3.

## Approved method and implemented candidate

The user's explicit approval of the world-specific sign-layout approach is
recorded in `reports/world_specific_method_approval_20260924.json`. It does not
approve labels, a fitted model or protected execution. No repeat approval of that
same sign-layout choice is needed.

Candidate v3 combines:

- Grounding DINO's fixed chair query with a supported 0.10 m near-depth band
  inside the predicted box. Support must contain at least 16 pixels and 10% of
  valid central-box pixels; the existing relative-IQR screen still applies.
- Grounding DINO's fixed doorway query with paired-side depth. Disagreeing
  jamb-side depths abstain; catalogue positions never choose measurement pixels.
- Exact RGB OCR LAB/LABORATORY/OFFICE hypotheses with the approved authored
  reference conversion, unchanged 0.35 m evaluation radius and 0.9 m association
  candidate radius. All 40 entrance construction templates across the ten
  development worlds independently match this prior.
- All-reference association, preserving ambiguity. No closest-ID truth selection,
  palette category lookup, expected-target identity or evaluator pose input.
- A fail-closed development adapter with exact RGB-D timestamp checks, rigid-TF
  validation, invalid-score/box rejection and explicit nondetection states.

The live adapter entry point is `scripts/four_class_candidate_runtime_v3.py`.
It returns development hypotheses, **not** an admitted calibrated ROS observation
feed. Model inference was replayed on newly captured frames; continuous moving
robot inference/latency remains part of later runtime/navigation validation.

## Fixed-panel results

| Panel | Scheduled RGB-D slots | Retained intact images | Frames with usable localization TF |
| --- | ---: | ---: | ---: |
| Complete prior Stage A | 144 | 141 | Historical rendering-pose replay, not measured TF |
| Ten-map development panel | 80 | 80 | Historical rendering-pose replay, not measured TF |
| Four fresh frontal views | 80 | 80 | 55 |
| Two fresh repeated-entrance views | 40 | 38 | 24 |

The three historical failures, two new unavailable capture slots and 39 fresh
missing-TF frames remain in their denominators. Repeated stationary frames are
not independent trials. No original human labels were read or reassigned.

All **40 development map/class necessary geometry checks pass** in the broader
panel. Distinct supporting frame counts across its ten maps are:

| Class | Frames with a unique geometric candidate within 0.35 m |
| --- | ---: |
| Chair | 20 |
| Doorway | 14 |
| Laboratory entrance | 42 |
| Office entrance | 17 |

Counts can overlap across classes in a frame and are **not detection-accuracy
estimates**. A point near a reference does not establish correct visual identity.
The fresh measured-TF panel independently supplies supporting frames for all
four classes: chair 15, doorway 14, lab entrance 26 and office entrance 14.

Both repeated-instance views retain two distinct in-radius same-class candidates
in 12 usable frames each (LAB and OFFICE). These are candidate associations, not
human-verified identities. No successful two-doorway simultaneous association is
claimed from these views, and the existing worlds contain only one chair each.
Synthetic ambiguity/order-invariance tests cover the all-reference association
rule; they do not establish repeated-chair visual performance.

All completed detector outputs reconstruct from raw logits/boxes/tokens. The
v3 runtime adapter replay and separately recomputed association distances pass
on all 300 integrated frames across the four panels (849 retained hypotheses).
Unreadable tokens, mixed depth, unassociated detections and empty outputs remain
visible in the raw evidence. Scores remain matching/recognition scores, not joint
correctness probabilities.

## Root-cause fixes and retained alternatives

The investigation traced the chair failure to chair-plus-background depth, not
just detection confidence. The original central-depth candidate failed all ten
map/chair checks. A gap-based foreground candidate passed only the farther chair
view; the fresh frontal replay exposed its remaining failure. The fixed-band v3
candidate passes both broader-panel chair views and the fresh frontal check.
All v1/v2 outputs remain intact; thresholds were not swept until a pass appeared.

The independent fresh capture also exposed an immediate TF lookup racing camera
arrival. A separate R3-only collector freezes the selected exact RGB-D pair,
waits a fixed two seconds, then records TF or its failure. It does not wait for
success, substitute a later frame or use simulator truth. In a prespecified
20-frame stationary development check, **20/20 exact-time TFs were retained**.
Five of those frames also had exact independent simulator-truth timestamps;
all five passed 3 cm / 1 degree. The other 15 lack exact evaluator truth.

This collector is separately versioned; the original frozen v8 instrumentation
still validates with SHA-256
`6b7bc9e5dd4f5289af88ee4524db3544d277eeeb6a0685177b12c128ef6fb49a`.
Research 1/2 source files were not changed. No validation plaintext or protected
world was accessed. All launched readiness jobs and owned simulators finished.

## Verification and next gate

Full suite: **1,227 passed, 1 skipped**, no failures/errors; only the existing
synthetic-depth warning. Report:
`reports/four_class_readiness_regression_20260924_v3.xml`.

Next: prospectively specify/review the exact joint-score learning inputs and
disjoint collection schedule, then obtain genuinely new human category,
association and reference-point labels. Fit/freeze the development candidate,
follow the delayed validation-release gate, and evaluate unchanged calibration
coverage/admission criteria. Readiness does not guarantee those gates will pass.

Evidence is in the `reports/four_class_*_20260924_v*` directories, with the final
perception integrations and independent audits under version **v3**. The
readiness manifest links the exact sources, approvals, tests and reports.
