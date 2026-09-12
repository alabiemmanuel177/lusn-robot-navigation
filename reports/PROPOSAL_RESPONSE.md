# Research 3 follow-up method decisions

Name: Emmanuel Alabi Olasubomi
Role: Researcher
Actual date and timezone: 2026-09-12T09:30:00+01:00 (Europe/London / BST UTC+1)

This response addresses proposals, not unseen results. No execution, protected
access, calibrated model or achieved power is approved by a generic acceptance.

## P1. Statistical proposal

Read STATISTICAL_METHOD_PROPOSAL_20260912.md and sign_flip_sensitivity.json.
Accept as the method to investigate, revise, or defer: Accept as the candidate method to investigate (with noted constraints)
Specific revisions/required evidence: 
1. The exact two-sided world-level sign-flip test of the mean paired difference (B6 minus B5) across the 6 held-out worlds is accepted as the candidate inference procedure under the exchangeability null.
2. The discrete arithmetic reality at K=6 is acknowledged: the smallest possible two-sided p-value is 2/64 = 0.03125 (requiring unanimous sign agreement across all 6 worlds). A single discordance or tie immediately inflates the p-value to >= 0.0625 (> 0.05).
3. The analytic sensitivity model (requiring a common positive-sign probability pi approx 0.9635 for 80% power) is noted as an arithmetic illustration under strong assumptions, not empirical power.
4. As prerequisite evidence before any confirmatory freeze, the agent must obtain nonprotected paired B5/B6 navigation outcomes, estimate baseline completion rate, paired discordance, and world-level dependence, and simulate power under a declared sensitivity grid. If empirical power for the +0.10 target effect remains inadequate under K=6, the study must be explicitly designated descriptive/exploratory prior to unblinding held-out worlds.

Final method, assumptions and sample-size approval still follow empirical
nonprotected feasibility work; this is not a confirmatory freeze.

## P2. Exact calibration-method proposal

Read CALIBRATION_METHOD_PROPOSAL_20260912.md in full, including class-specific
temperature grid, weighting, numerical criteria and failure policy.
Accept as the prospective protocol, revise, or defer: Accept as the prospective protocol
Specific revisions: 
1. Family and Objective: Accept the class-specific scalar temperature scaling model q = sigmoid(logit(p) / T_c) for each of the 4 classes (chair, doorway, laboratory entrance, office entrance), fitted on development data only by minimizing weighted binary cross-entropy over the deterministic scalar grid G = {1.0} union {exp(log(0.2) + j/1000 * log(25)) : j=0,...,1000} without learned intercept or post-hoc regularization tuning.
2. Weighting & Scope: Accept equal map weighting, equal view-group weighting within maps, and equal emission weighting within view-groups. Confirm that pilot data, engineered diagnostic attempts, and held-out validation labels are strictly excluded from fitting.
3. Nondetections: Confirm that non-emissions remain recorded as nondetections with proper denominators, never converted to p=0 or negative labels.
4. Diagnostics: Accept leave-one-development-map-out diagnostics with fixed grid/settings, reporting any failed folds transparently without silent exclusion or setting adjustment.
5. Validation Screen: Accept the proposed point-estimate admission screen (independent satisfaction of Coverage v2 floors, macro-Brier strictly improves by > 10^-12, macro-ECE and max class/bin MCE do not degrade by > 10^-12, and no individual class Brier degrades by > 10^-12 over 10 equal-width evaluation bins).
6. Scope Limit: Acceptance of this prospective protocol does NOT constitute approval of any fitted model or validation result, which remain subject to post-validation human review.

Acceptance of a method is not acceptance of a fitted model or validation results.

## P3. Encrypted delayed release

Read VALIDATION_DELAYED_RELEASE.md.
Accept the reviewer-held-key workflow, revise, or defer: Accept the reviewer-held-key workflow
I understand that hashes alone do not hide labels and I must withhold the key,
plaintext return and validation feedback until development freeze (yes/no): yes
Specific revisions: 
1. The AES-256-GCM authenticated envelope workflow in `seal_validation_review.py` is accepted for sequestering validation reviews when expansion validation data is ready.
2. As primary reviewer, I will execute `seal_validation_review.py seal` locally, retain the private key (`validation-review.key`) and plaintext validation review journal exclusively on my local secure machine, and transmit only `validation-return.sealed.json` to the agent/workstation.
3. Decryption key release is strictly gated behind formal human sign-off of the release gate record (`approved-release.json`, schema `research3-validation-release-gate/v1`) after the development candidate model, fitting logs, and calibration protocol are frozen and audited.

## P4. Capture instrumentation source revision

Read EXPANSION_IMPLEMENTATION_GATE.md. The historical detection-triggered collector
does not implement the already approved earliest-frame/nondetection schedule.
Authorize revising only R3 capture instrumentation and repinning its source,
while preserving detector/provider code, confidence formula, camera settings,
scene geometry, coverage floors and all historical evidence (yes/no/defer): yes
Specific constraints: 
1. Scope Limitation: Authorization is strictly confined to capture orchestration and sampling instrumentation (`expansion_sampling.py` and `physical_expansion_capture_candidate.py`) to correctly implement the earliest synchronized frame and exact assigned entity/class selection with explicit nondetection accounting.
2. Invariant Code Guards: The provider score formula, palette, color thresholds, association radius, camera FOV, physical scene geometry/colliders, route IDs, and Coverage v2 floors must remain 100% frozen and unaltered.
3. Verification Gate: Before launching live expansion captures, the integrated collector must be verified through synthetic unit tests, source snapshot re-hashing, readiness arming checks, and an isolated development preflight. Empty/interrupted streams must be recorded as infrastructure failures, not legitimate perceptual nondetections.
4. Diagnostic Asset Scope: The candidate occluder definition (20% projected area of the marker box) and candidate spheres are noted; rendered visual preflight frames remain mandatory before approving collection for the diagnostic panel.

This source-revision approval permits implementation and preparation, not blanket
campaign/protected execution or approval of unrendered diagnostic assets.
