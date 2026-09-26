# Research 3 status and handoff

## Final Closure — Research 3 concluded under descriptive and exploratory feasibility, 26 September 2026

Emmanuel Alabi Olasubomi (Researcher, Africa/Lagos) formally authorized Option 2:
narrow the study scope to descriptive and exploratory feasibility, terminating
Research 3. Formal authority record: `reports/research3_closure_authority_20260926.json`.

Decision & scope:
- Research 3 is formally closed under the descriptive and exploratory feasibility
  deliverable.
- The frozen hybrid candidate (`reports/hybrid_score_candidate_20260925_v1/candidate.json`,
  SHA256: `b9de70b9c8a829d3177bc4b709fc4e53966f9e5df8e75b3d2c8882730a559b45`) is retained
  as an exploratory feasibility candidate only.
- Wave C and Wave V are not scheduled or launched.
- Validated four-class runtime calibration is not claimed.
- Blockers B03 (scientific design / coverage) and B09 (final claims / completion)
  are formally resolved under the descriptive and exploratory feasibility deliverable.

Core scientific & engineering findings:
1. Structural OCR support limitation:
   Frozen upstream thresholding in RapidOCR (`text_score >= 0.5`) mathematically
   truncates entrance input support to [0.5, 1.0]. Because the localizer copies
   the retained OCR score to `raw_score` and identity pass-through is applied,
   populating the required [0, 0.5) bin for laboratory and office entrances is
   structurally impossible (maximum low-bin emissions is identically 0 vs the required 5).
   Unchanged collection waves cannot overcome this upstream threshold.
   Audit: `reports/hybrid_score_candidate_20260925_v1/ocr_support_audit.json`.
2. Clean-view saturation in Wave S:
   Human review found 261/261 jointly correct emitted chair/entrance observations
   (99 chair, 84 laboratory entrance, 78 office entrance; 0 incorrect). This is
   observed sample precision, not population certainty, recall or independent-view
   generalization. The 26 doorway emissions had 20 correct and 6 reference-point
   errors; category and instance judgments were correct in those six cases.
   Portal-void penetration is a proposed mechanism, not independently established
   as the cause of all six errors by these labels.
   Zero negative samples for three classes prevented four-class logistic fitting under
   the pre-registered outcome floor (>= 5 incorrect per class).

All dangling lock files and background tasks have been cleaned up. Research 3 is
terminated and archived.

Final authoritative archive: `reports/research3_final_closure_20260926_v2.zip`.
Version 2 supersedes version 1's overly strong causal/precision wording. The
original failed calibration gates remain failed; B03/B09 are administratively
resolved by the expressly authorized scope change, not by passing those gates.

## Latest — exact hybrid candidate frozen; OCR support impossibility verified, 25 September 2026

The user's repeated direction permits raw-score pass-through. That option is now
implemented for chair/lab/office, retaining the fitted doorway logistic candidate.
No probabilities near1 were invented. The three pass-through values remain
explicitly uncalibrated matching scores. Candidate snapshot:
`reports/hybrid_score_candidate_20260925_v1/candidate.json`.39 targeted tests pass.

The unresolved mapping choice is now resolved, but original C/V low-bin coverage
is provably unreachable for both entrance classes: frozen RapidOCR filters out
scores below0.5, entrance localization copies the retained score, and pass-through
cannot populate [0,0.5). This was inspected in pinned source and boundary-tested
using the actual filter. See [support blocker](HYBRID_SCORE_SUPPORT_BLOCKER_20260925.md)
and the packet's `ocr_support_audit.json`. It is not merely sparse pilot support.

No C/V launch, modified thresholds, invented human labels, original-protocol success
or runtime admission. A substantive choice between a new four-class calibration
study and narrowed descriptive scope is needed; more execution authority alone
cannot resolve the incompatible support and coverage policy.

## Latest — post-Wave-S amendment recorded; doorway-only candidate fitted

Emmanuel supplied named authorization for a post-outcome saturation-method change.
See [amendment and unresolved choices](AMENDMENT_WAVE_S_SATURATED_CLASSES_20260924.md)
and `reports/wave_s_saturation_amendment_authority_20260924.json`. The original
287 labels, protocol and failed four-class gate remain unchanged. Zero observed
errors in261 selected emissions does not certify p_joint=1 or population saturation.

Authorized doorway-only exploratory candidate fitted with the existing solver:
578 updates, gradient infinity norm9.76e-09. Seven leave-one-map-out folds fitted;
three retain their failure because only four negative training observations remain.
Artifact: `reports/wave_s_doorway_amendment_candidate_20260924_v1.json`.
32 fitting/component regression tests passed. No runtime admission, four-class
freeze, C/V collection, fabricated future labels or validation-key release occurred.

Remaining blockers: exact non-doorway scoring choice (approximately1 versus raw
pass-through is not one rule), compatible prospective C/V acceptance criteria,
actual future human labels and reviewer-held validation release. Generic execution
authority is recorded; it does not resolve these scientific/data dependencies.

## Latest — Wave S review received; outcome gate failed, 24 September 2026

Both observation-return copies match and all287 verdicts validate against the
evidence and emission hashes:281correct,6incorrect,0unreviewable. Per class:
chair99/0, doorway20/6, laboratory entrance84/0, office entrance78/0
(correct/incorrect). All ten map cells are represented per class, but three
classes have no incorrect outcomes against the required minimum of five.
No score models were fitted; C/V have not started. The accepted fixed-budget
failure policy prohibits filling this gap with relabeling, threshold relaxation,
solver fallback or unapproved post-hoc additional attempts.

Receipt: `reports/wave_s_review_receipt_20260924_v1.json`. The separately returned
protocol file and its mirror match but contain null reviewer name/role and fail
standalone named-review validation. The existing named conversation-final protocol
decision remains valid; repeat scientific approval is not the coverage blocker.
Original returned files are preserved unchanged. Recovery requires a separately
reviewed prospective amendment or reporting this phase as insufficient for fitting.

## Latest — Wave S human-review kit ready, 24 September 2026

All400 primary attempts and pinned detector/OCR/export finished at20:12 Lagos:
398 captures,2 Nav2 lifecycle failures;287 scoreable emissions,72 abstentions,
39 nondetections. No retries or duplicate-content exclusions. Human labels and
model fitting have not occurred. The supervisor finished normally.

Use `reports/joint_score_wave_s_human_review_20260924_v2/index.html`, or extract
the matching ZIP and open index.html. README.md contains instructions. Review
all287 observations (99chairs,26doorways,84laboratory entrances,78office entrances)
on category, physical instance and planar reference consistency. Scores are
absent; full/original images, measured camera/map context and catalogue IDs are
provided. Save progress backups; return `wave-s-review-return.json` after personal
confirmation. Nondetections/abstentions/failures are retained, never negative labels.

Packet checks:866 file hashes,861 images,287 emission bindings and ZIP integrity
verified; browser navigation/images/mobile/unfinished-export checks passed;
final export and joint logic tested only on an isolated synthetic fixture.
Version1 was an unpublished QA build with an incorrect camera-arrow axis;
version2 fixes the optical forward axis (+Z), with a regression test. Use v2 only.
Visual design keeps full-scene evidence beside explicit, unselected verdicts.
Machine QA does not establish human reviewability; unreviewable remains valid.

ZIP SHA256: `0852aea8177971c6d302e185e5aab5bef3bd162a015acd5c5ff793fb41a11858`.

## Latest — authorized Wave S collection started, 24 September 2026

The user instructed execution to proceed. The fixed serial 400-attempt supervisor
has started, using the verified execution manifest without changing pinned driver,
detector, protocol or assets. Live status is in
`reports/joint_score_wave_s_supervisor_20260924_v1/`: `launch.json`, one
`closed-NNN.json` per finished attempt, and eventually `complete.json` or
`blocked.json`. This section records launch, not completion; inspect those files
for current progress. Primary evidence is under
`reports/joint_score_wave_s_primary_20260924_v1`.

The supervisor automatically runs the existing detector/OCR/export pipeline after
all 400 attempts close. It never retries consumed attempts, learns from invented
labels, starts C/V, or bypasses a failed safety/integrity gate. Capture workers
remain one because the accepted protocol and bound authority require serial
capture; offline detector uses its pinned four CPU threads, OCR one. Seventeen
targeted driver/binding/supervisor tests passed before launch. No pinned sources
were edited to add the external scheduling wrapper.

## Latest — Wave S driver preflight passed and execution authorized, 24 September 2026

See [Wave S driver handoff](WAVE_S_DRIVER_PREFLIGHT_20260924.md). All 400 scheduled
development poses passed static clearance. Four actual Gazebo views passed
synchronized capture, exact-time measured TF, unchanged detector/OCR integration
and clean shutdown. Three scoreable emissions and one doorway abstention are
retained as engineering evidence only, never calibration coverage or labels.

The user's explicit prospective execution authorization has been bound to
`reports/joint_score_wave_s_execution_20260924_v1/execution_manifest.json` and its
approval receipt after passing checks. No further S execution approval is needed.
The source-bound driver is ready; **no primary S attempts have launched and no
job is left running**. S human review and score-model freeze still precede C/V;
validation release, protected access and unseen model admission remain excluded.

Regression: **1,311 passed, 1 skipped**, zero failures/errors. Original component
and readiness pins and frozen v8 remain valid; no R1/R2 source changes. Initial
TF-history/DDS-context preflight failures and their old source versions remain
preserved; a fresh four-view run verified the driver-only corrections.

## Latest — collection/scoring components implemented and tested, 24 September 2026

The reviewer accepted all seven protocol decisions and explicitly confirmed overall
acceptance in `reports/joint_score_protocol_20260924_v1/review_decision_CONVERSATION_FINAL.json`.
The historical proposal and template remain unchanged; this is not execution or
unseen-model approval.

See [component implementation handoff](JOINT_SCORE_COMPONENTS_IMPLEMENTATION_20260924.md).
New modules implement single-frame ROS collection, post-arm exact synchronization,
fixed-delay TF, create-once attempt accounting, class-specific features,
duplicate-instance abstention, content deduplication, reviewed-data fitting and
manifest-bound serial admission. **1,298 tests passed, 1 skipped**, zero failures
or errors. Only the existing synthetic-depth warning remains.

Development replay: 159 frames processed, 41 existing infrastructure failures
retained; candidates remain in all four classes. A bounded synthetic localhost
ROS transport test passed without launching Gazebo or Wave S. All fitting tests
use invented fixtures; no actual model or human labels were produced. Validation
and protected content remain unopened. R1/R2 and frozen v8 sources are unchanged.

Evidence manifest: `reports/joint_score_components_handoff_20260924_v1/manifest.json`.
Before Wave S: finish source-bound driver/completion-record integration and the
execution manifest, actual-world clearance and isolated Gazebo transport preflight,
then obtain separate manifest-bound execution authorization. No collection job is
left running, and primary launch readiness is not claimed.

## Latest — score-learning/collection protocol finalized for review, 24 September 2026

See [exact protocol](SCORE_LEARNING_COLLECTION_PROTOCOL_20260924.md) and
`reports/joint_score_protocol_20260924_v1/manifest.json`. The create-once packet
contains a validated 960-attempt schedule: 400 supervised score-learning,
400 separate development temperature-calibration, 160 separate validation.
It fixes class-specific depth features, duplicate-instance abstention, one-frame
sampling, missingness, seed lists, weighting, solver and failure rules. Original
P2 coverage/admission criteria remain unchanged; accepting the new upstream joint
probability as their input is an explicit scientific amendment, not an assumed
approval. Readiness evidence hashes were checked before packaging.

The packet includes `review_decision_TEMPLATE.json`, with every decision pending
and no fabricated signature. Review the protocol, complete the seven decision
fields with actual name/role/date, and return the decision record. No repeat
world-specific sign-layout approval is requested. Scientific approval, production
adapter/feature implementation and tested per-wave execution manifests still
precede collection. No real fitting, new labels, simulator launch, validation
release or protected-world access occurred in this protocol preparation.

Verification: **1,242 passed, 1 skipped**, zero failures/errors; only the existing
synthetic-depth warning. All 12 packet/source pins match; frozen v8 still validates
with its unchanged `6b7bc9e5...` digest. Regression report:
`reports/joint_score_protocol_regression_20260924_v1.xml`.

## Latest — four-class engineering readiness completed, 24 September 2026

The user approved the world-specific sign-layout approach. See
[four-class readiness](FOUR_CLASS_PERCEPTION_READINESS_20260924.md).
Candidate v3 passes all 40 development map/class necessary geometry checks and
has fresh measured-TF support for all four classes. Repeated LAB/OFFICE views
retain separate instance candidates; ambiguity remains explicit. A separately
versioned fixed-delay collector resolves the image/TF arrival race in a 20/20
frame check. All unsuccessful earlier candidates and missing frames are retained.

Full regression: 1,227 passed, 1 skipped. Frozen v8 and Research 1/2 sources are
unchanged; all readiness jobs finished. This completes **engineering preparation**,
not human identity verification, calibrated runtime admission or the research.
Next is the exact score-learning protocol and genuinely new observation labels;
no repeat sign-layout approval is needed. Validation and protected gates remain.

## Latest — independent live pose checked; entrance reference mismatch resolved as a candidate

See [24 September continuation](STEPS123_CONTINUATION_20260924.md). Four stationary
development views completed: 11 exact saved RGB-D/TF/simulator-pose comparisons
all pass 3 cm / 1 degree; 69 other frames retain missing-truth/TF status. A new
OCR plus explicitly authored reference-conversion candidate puts ten entrance
hypotheses within the unchanged 0.35 m radius. This depends on the world's fixed
sign layout, not a general learned entrance-localization capability. Earlier
failed localization and instrumentation trials remain intact.

The joint-confidence numerical prototype is tested, but no real model is fitted
or approved. Scientific admission of the template prior and genuinely new human
labels remain required; existing review labels do not transfer to these boxes.
No protected/validation data was opened, frozen sources were not changed, and
all live preflight jobs finished. The three scientific steps are not all closed.

## Continued through alternative detector and portal localization checks

See `docs/DETECTOR_REDESIGN_CONTINUATION_20260923.md`. Grounding DINO v3 completed
all 24 fixed slots (23 images/one historical failure); all 850 proposals reconstruct.
There are proposals for all four classes, but only two central-depth geometric
matches and neither meets the 0.35 m radius. A subsequent fixed side-depth replay
retains all 57 portal proposals; three doorway candidates are within that radius,
none for lab/office entrances. No identity/accuracy/calibration claim follows.
The joint-score synthetic prototype and independent-pose validation tooling are
implemented and tested. Original/legacy evidence remains intact; no live deployment,
primary freeze, human labels, validation release or protected access occurred.

## Steps 1–4 investigation completed; scientific acceptance still blocked

See `docs/STEPS14_RESULTS_20260923.md`. Depth-plane translation consistency passes
on all 20 frames with three-axis support; three other intact frames lack support.
An R3-only nominal-to-rendering mount correction candidate is implemented/tested,
not deployed or independently certified for full pose/reference-point accuracy.
The fixed short-prompt test completed all 24 slots (23 images, one historical
failure): 45 boxes, no doorway or laboratory-entrance output. No candidate selected.
Both prompt panels have only low raw scores; the accepted temperature family
cannot repair raw-bin coverage or establish joint-score meaning. The revised
primary protocol is drafted, **not frozen**. Use corrected score audit and gate
`*_v2.json` in `reports/steps14_feasibility_20260923_v1/`; initial comparison files
are superseded for a caught query-order reporting bug. No simulation is running.

## Object/depth integration completed — 23 September 2026

The fixed 24-slot development replay is complete: 23 intact frames, one retained
historical failure, all 93 predicted boxes retained. There are 34 unique geometric
candidates, 26 multiple-surface abstentions, 23 unmatched hypotheses, and 10
non-navigation hypotheses. All 124 input hashes verify; depth replay and separate
transform/association arithmetic checks pass. These are not human correctness
labels, admitted calibration data, or validated live observations.

The transform uses commanded stationary pose plus the rendering-camera model,
explicitly not measured pose. Next is sensor-transform validation and resolving
the candidate detector's missing doorway proposals and raw-score semantics before
any new primary collection. No validation labels were opened or R1/R2 code changed.
See `docs/OBJECT_DEPTH_INTEGRATION_RESULTS_20260923.md`.

## R3-only redesign: two offline probes completed and audited

The authorized catalogue-blind path completed 1,410 region vectors over 141
development images; all reconstruct. The separate object-localization candidate
completed 23 intact images in 24 fixed source slots, retaining the one historical
failure. All 93 displayed boxes reconstruct from saved raw arrays. No doorway
box exceeds the fixed 0.1 display threshold; no candidate is admitted for primary
calibration, human bulk labeling or runtime use. Depth/association candidate
contracts and focused tests are implemented, but not integrated into live ROS.
See `docs/REDESIGN_ENGINEERING_RESULTS_20260923.md` for results and limitations.
Both offline processes have finished; no live simulation was launched this turn.
Next development integration is already authorized; no generic approval is needed.

## Authorized R3-only redesign in progress — 23 September 2026

Emmanuel explicitly authorized the recommended method redesign and exact packet
publication. See `reports/method_decision_20260923_v1/followup_authorization.json`.
Both requested ZIPs are now published to the existing private GitHub release
`research3-method-decision-20260923-v1`; GitHub asset digests match local hashes.
`upload_receipt.json` supersedes the historical denied upload. No source changes
were committed/pushed, and repository visibility was not changed.

A new, separately versioned RGB-only candidate completed 141 intact development
frames × 10 fixed regions = 1,410 vectors. Independent recomputation passed all
outputs. Inference does not use marker pixels, palettes, claimed classes or
catalogue identities; historical camera sampling remains catalogue-directed.
These are unlocalized region scores, not admitted semantic observations or human
labels. See `reports/catalogue_blind_candidate_20260923_v1/`.

The association candidate rejects unlocalized/preassigned-ID inputs and retains
all ambiguous geometric candidates rather than nearest-ID truth. Synthetic tests
pass. A separate fixed 24-slot object-box feasibility experiment is prepared using
an exact official OWLv2 safetensors revision and a separate CPU-only environment.
No model or primary/protected campaign is admitted; original provider/core v8,
Research 1/2, coverage floors and delayed validation gates remain intact.

## Latest: fixed panel complete; avoid futile human labeling — 23 September 2026

Supersedes the running and raw-bin-only handoff entries below. All 96 fresh
class-aware attempts are accounted for: 76 emissions, 18 nondetections and two
retained resume-launch failures. All 94 complete captures verify; all 76 scores
reconstruct. Raw bins pass the pilot screen: chair [6,12,6], doorway [4,13,2],
laboratory entrance [3,10,4], office entrance [3,9,4]. No captures remain running.

However, the independent raw-coordinate necessary-condition audit proves that
all 19 doorway emissions exceed 0.35 m (range 0.43156–0.71505 m). At most zero
can be jointly correct under the accepted rubric, below the pilot floor of two.
The prepared 76-target kit passed technical relocation/image checks, but is
**not admitted or published as a bulk labeling request**. The newer
`necessary_joint_feasibility.json` supersedes `final/audit.json`'s earlier
raw-bin-only next-gate suggestion. No human labels were generated.

Do not request another 76-item review or claim calibration coverage. Restoring
frontal doorway views could fix that acquisition defect, but does not establish
the missing class-wise negative outcomes for the other classes. The palette-
derived semantic category mechanism and completed, non-admitted semantic probe
are documented in `docs/RESEARCH3_METHOD_DECISION_20260923.md`. That proposal
asks for an explicit separately versioned R3 observation-method redesign, or a
narrower descriptive completion—not a relaxed gate or unseen-model approval.

Provider/core v8, Research 1/2 and protected data remain unchanged/unaccessed.
Regression: 1,123 passed, one skipped; two new focused necessary-pose tests also
passed. Offline missingness and semantic-probe candidates are packaged and
verified but not activated. Research 3 is not scientifically complete.

Local handoffs are verified: `research3_class_aware_pilot_20260923_v1.zip`
(3,100 members; SHA-256 `886d65975489da2e8d9756a566b48defd04bedd3c8fd9eec70775a3ce645ebaf`)
and the smaller `research3_method_decision_20260923_v1.zip`
(111 members; SHA-256 `6db1ee423fb3d88abe33705c5c36e97d867bdff9e98b1e2ab4e7723bc7e310bc`).
The latter and the offline-candidate ZIP were **not uploaded**: auto-review
rejected publishing this new research-image payload without exact destination/
payload approval. See `reports/method_decision_20260923_v1/upload_status.json`.
Do not claim a GitHub download exists or silently retry the rejected upload.

## Fresh class-aware exploratory pilot running — 23 September 2026

Continued autonomous design work after the user's instruction, not a primary
campaign approval. The completed distance × lighting panel produced 78 emissions
and 18 nondetections from 96 attempts, with zero infrastructure failures. All
frames and emitted scores independently verify. Its bins are chair [6,12,6],
doorway [0,10,10], laboratory entrance [3,10,4], office entrance [3,9,5]. It fails
the doorway low-confidence screen and remains excluded from calibration.
Its verified engineering archive has 3,121 members and SHA-256
`9e21a953ba59ae80c761c811bee0b5d711fdac655eaf8ffdab8b76e0028f9493`.

A separately fixed fresh 96-attempt class-aware panel uses near-oblique doorway
views and midpoint/far views for the other three classes, on development maps
1/6, seed 17. This exploratory design explicitly uses earlier feasibility
findings; it does not pool old observations. All 96 prepare-only checks passed.
Execution uses two guarded workers and the unchanged v8 provider/core snapshot.
See `reports/class_aware_acquisition_pilot_20260923_v1/` and the matching protocol.
No primary collection, protected access, validation release or human verdict is
authorized/generated. A design-only review kit is being prepared, conditional on
the complete confidence screen, with no machine assertions of human decidability.

Additional completed work: tested offline missingness contract candidate (not
an active release-policy change), and a fixed CPU-only semantic model probe on
119 earlier Stage A emissions (238 image views). Its relative prompt scores are
not calibrated probabilities or correctness labels; no detector change follows.
The probe shows substantial context/taxonomy sensitivity, so it is not admitted
as a drop-in semantic verifier. See the corresponding 23 September documents.

## Continued design work: distance × lighting pilot — 23 September 2026

After Stage A failed, Emmanuel explicitly instructed continued work. A separate
exploratory 96-assignment development-only interaction pilot is now prepared and
running. The recorded mechanism is saturated marker-size support despite lower
colour agreement; this pilot combines midpoint/far views with the existing
nominal/90%/80% lighting assets. It is not an extension of Stage A or primary data.
All 32 poses and 96 prepare-only requests passed; first dispatch is isolated,
then two guarded low-priority workers. No R1/R2/provider changes, validation
release, primary execution or human-label generation. See
`docs/DISTANCE_LIGHTING_PILOT_20260923.md` and
`reports/distance_lighting_pilot_20260923_v1/` for fixed schedule/source bindings.

## Stage A complete; candidate fails automatic feasibility — 23 September 2026

This supersedes the running entry below. All 144 approved fixed assignments are
accounted for: 119 emissions, 22 nondetections, 3 retained startup failures.
Independent audit passed for all identities and 141 completed RGB-D captures;
all 119 emitted scores reconstruct. Tests: 1,073 passed, 1 skipped.

Chair bins: [9,13,11]; doorway [4,18,6]; laboratory entrance [0,18,11];
office entrance [0,17,12]. Both entrance classes fail the low-confidence pilot
floor of two. Even assigning their one infrastructure failure each a hypothetical
low-confidence emission cannot meet that floor. No labels are requested for this
failed panel, no primary collection is admitted, and coverage remains incomplete.
No Stage A captures remain queued or running. An explicit new scientific design
decision is needed. See `docs/REDESIGN_STAGE_A_RESULTS_20260923.md`.

## Stage A approved and running — 23 September 2026

Emmanuel explicitly approved the bounded 144-assignment lighting/framing pilot.
Approval: `reports/redesign_stage_a_approval_20260923.json`; execution and
additional wrapper source binding: `reports/redesign_stage_a_20260923_v1/`.
The original v8 provider/core snapshot remains unchanged. All 144 prepare-only
checks and the expanded regression suite passed before dispatch.

Three initial environment failures are retained without replay (missing R1
Python import path, then stale R3 install overlay). The corrected process-local
launch environment is prechecked by `scripts/launch_redesign_stage_a.sh`.
Subsequent live RGB-D captures pass integrity checks and continue in two-worker
batches. This entry is a running status, not a completed pilot or coverage pass.
No human labels, primary collection, validation release, model freeze or
protected-world access is authorized by Stage A.

## Calibration redesign prepared; no coverage pass claimed — 23 September 2026

Emmanuel authorized redesign preparation while retaining coverage floors and
Research 1/2 boundaries. The first candidate retains the provider and changes
whole-scene illumination plus camera framing, with no new geometry, marker
material, score formula, palette, noise or synthetic pose displacement.

`docs/CALIBRATION_REDESIGN_AMENDMENT_20260923.md` specifies a 144-attempt
development-only feasibility panel, followed only conditionally by a new
2,016-attempt primary matrix (1,440 development / 576 matched validation).
All 42 lighting variants and 336 static poses are prepared; footprint checks
passed. These are unrendered candidates, not perception or coverage results.

The pilot first checks confidence support automatically, before requesting human
labels. Old data are not pooled; old validation labels remain sequestered. The
new lighting/framing mixture requires explicit scientific review as a primary
distribution. Live lighting-asset admission/source verification and Stage A
execution are next; no simulator, primary capture or model freeze was launched.

## Fixed panel complete; calibration remains blocked — 22 September 2026

This entry supersedes the running/blocked execution counts below. All 80 fixed
development feasibility assignments are accounted for: 49 assigned emissions,
26 perceptual nondetections and five retained infrastructure failures. The final
36 completed at two workers with no further infrastructure failures. No stopped
assignment was replaced. No live capture remains queued.

Independent auditing verified all 80 identities and all 75 completed captures'
frame/byte integrity. Reconstructing the frozen provider scores matched all 49
emissions. Chairs now have 11 low-confidence emissions, but doorway, laboratory
entrance and office entrance still have none. These design-only observations are
not calibration data or human correctness labels. More review of this panel
cannot fill its absent confidence bins.

Results: `docs/STAGE1_FEASIBILITY_RESULTS_20260922.md`. Engineering evidence ZIP:
`reports/research3_stage1_evidence_20260922_v2.zip`; independent verification
passed all 2,710 members and its expected archive digest. This is a point-in-time
engineering package, not a completed scientific release or full runtime image.

Completed independent preparation includes marginally matched synthetic power
sensitivity, an adaptive-integration audit, delayed-release admission regression
tests, scheduled-cohort missingness bounds and 159/159 pinned telemetry
recomputations. The tested classwise mapping candidate remains offline; it is not
activated in the pooled-temperature runtime. See
`docs/CLASSWISE_RUNTIME_INTEGRATION_CANDIDATE_20260922.md`.
The fitting script now refuses freeze invitations for blocked candidates and
uses the canonical human release-gate status before accessing validation labels.
Historical failed candidate files and all sequestered validation data are unchanged.

Track unresolved dependencies in `docs/RESEARCH3_BLOCKER_LEDGER_20260922.md`.
No coverage relaxation, fitted-model approval, validation-key release, new primary
sampling or protected campaign is implied by this progress.

## Two-worker resumption approved and prepared; external workloads block dispatch — 22 September 2026

Emmanuel approved the exact remaining-36 disposition. Record:
`reports/stage1_resume36_approval_20260922.json`. All 36 untouched assignments
passed runner preparation, with ROS domains 100/101, snapshot v8, unchanged
scientific settings and five historical failures retained without replacement.
The corrected external-workload scanner is bound into the new plan and used
both before admission and during the owned-process monitor.

Current executable: `scripts/resume_stage1_two_workers.py`; plan:
`reports/stage1_two_workers_20260922_v4/plan.json`. Version 3 was a prepare-only
intermediate; version 4 avoids changing historical helper functions merely by
importing the module during offline tests. Neither version dispatched a capture.
The full regression suite passed (one existing skip and numerical warning).

Actual admission using the corrected scanner refused launch with external PIDs
1269694, 1270771 and 1271086 active, despite GPU busy only 13%. The prerequisite
is external campaign idleness, not GPU percentage alone. No new attempt was
consumed, no external job changed and no background queue started. Approval is
retained; it does not need repeating when idleness and resource guards pass.
Combined accounting remains 27 emissions, 12 nondetections, five infrastructure
failures and 36 unstarted assignments.

## Guard repair verified; new resource stop after 44 attempts — 22 September 2026

The approved source fix is applied and successfully used by 16 further completed
captures. At the next batch, the whole-host load guard reached 19.354 (limit
19.2), stopping four owned attempts. Combined accounting is now 27 emissions,
12 nondetections, five infrastructure failures and 36 unstarted assignments.
Every completed capture passed exact-frame and byte-integrity checks. All failed
attempts are retained without replay. Combined current accounting:
`reports/stage1_four_workers_20260922_v2/partial_summary.json`.

An active `/home/eao/scra-robot-navigation` campaign was identified afterward.
Gazebo's rewritten single-string argv[0] bypassed the older simulator identifier.
The corrected read-only scanner is regression-tested and verified against the
actual external campaign parent and simulator. Neither external job was changed
or stopped; noninterference cannot be inferred just from the short prior trials.
Read `memory/2026-09-22-external-simulator-admission.md` for the investigation.

Current blocking conditions: external campaign idleness and disposition of the
new infrastructure stop. Proposed conservative resume is exactly 36 untouched
assignments with two workers and corrected external-workload detection, keeping
all thresholds/source pins/scientific settings unchanged. Decision scope:
`docs/STAGE1_RESUME_36_20260922.md`. No R3 background capture is active.

## Approved guard repair applied; remaining capture schedule resumed — 22 September 2026

Emmanuel approved the specific repair and resumption proposal. Conversation
transcription: `reports/resource_guard_repair_approval_20260922.json`. The sole
runtime change catches ProcessLookupError together with FileNotFoundError during
the resource guard's PID read. Permission failures still fail closed and active
Research 2 drivers are still detected. The full regression suite passed, including
new tests against the actual repaired function and approval-bound snapshot checks.

The snapshot generator/validator now accepts only this explicitly hash-bound
additional guard revision. Historical snapshots were not overwritten. New binding:
`reports/expansion_instrumentation_snapshot_20260922_v8/snapshot.json`.
All 56 untouched requests passed actual runner preparation. Their new executor
and plan are `scripts/resume_stage1_four_workers.py` and
`reports/stage1_four_workers_20260922_v2/plan.json`. The first 24 result hashes are
bound into this resume plan; the historical failure is retained without replay.

The first resumed batch completed: two nondetections and two detections, all
passing exact-frame integrity checks. A subsequent admission check stopped before
dispatch at 31% GPU busy; a later read-only check passed at 14%, so the same plan
was resumed without changing any assignment or overwriting evidence. Resource
admission refusals consume no attempts. Collection remains in progress as of this
entry; later entries supersede its progress count.

## Fixed 80-view collection partially executed; scoped repair approval needed — 22 September 2026

After the user authorized resource scaling and continuing all stages, the four
trial captures passed raw RGB/depth checksum, synchronized frame, provider
completion/emission-delivery and no-human-label checks. All 80 unchanged scientific
assignments then passed actual runner preparation for four-worker batches using
ROS domains 96–99. The original serial artifacts were preserved; new pinned plan:
`reports/stage1_four_workers_20260922_v1/plan.json`.

Six batches attempted 24 views: 17 assigned detections, six nondetections, and one
infrastructure failure. All 23 completed captures passed retained-byte and exact
frame integrity checks. The fixed stop rule halted execution; 56 remain unstarted.
Accounting and class raw-confidence bins:
`reports/stage1_four_workers_20260922_v1/partial_summary.json`. These are design-only
observations, never calibration quota credit or human correctness judgments.

The failure was a reproduced process-exit race in the frozen resource guard:
`research2_execution_pids` caught FileNotFoundError but not ProcessLookupError
while reading `/proc/<pid>/cmdline`. It was not a measured GPU-capacity failure.
The minimal candidate handles both vanished-process errors while preserving
fail-closed permission errors and active Research 2 detection. In-memory probe
and focused tests passed; the frozen runtime itself remains unchanged.

Required narrowly scoped approval:
`docs/RESOURCE_GUARD_REPAIR_APPROVAL_20260922.md`. It covers the guard repair, a new
explicit source binding and resumption of only the 56 untouched assignments;
the failed attempt stays retained without replacement. The historical P4
instrumentation approval does not cover this frozen runtime file, so silently
repinning it is not authorized. No worker/background campaign remains active.
Investigation: `memory/2026-09-22-resource-guard-race.md`.

The downstream dependencies are consolidated in
`docs/RESEARCH3_COMPLETION_GATES_20260922.md`. No validation plaintext was read,
no human labels generated, and no model or protected campaign was approved.

## Four-worker live engineering trial completed — 22 September 2026

The user authorized increased resource use. A bounded four-worker development
engineering test used the fixed map-1 view-0 assignments for all four classes,
separate ROS domains 92–95, unique Gazebo partitions and new output IDs. Original
provider/settings/snapshot and the original 80-view serial manifest were unchanged.
Plan and results: `reports/four_worker_capture_trial_20260922_v1/`.

All four processes exited zero in 28.57 seconds, with provider frame completion
recorded for each. Three assigned targets emitted; the laboratory entrance was
a recorded nondetection, not an infrastructure failure or a negative human label.
No retries, calibration fitting, protected access or primary quota credit occurred.

29 one-second whole-host samples spanning dispatch/startup/cleanup: GPU mean
24.69%, peak 35%; CPU mean 28.50%, peak 56.33%; GPU power peak 38 W; VRAM peak
2.33 GiB; available system RAM minimum 22.97 GiB. The full regression suite ran
concurrently during part of this measurement, so CPU figures include testing
and are NOT a clean estimate of four captures alone. Both timings and resource
figures are short-trial observations, not validated campaign scaling estimates.

Eight focused concurrency/executor tests and the full regression suite passed
(one existing skip and synthetic camera-model numerical warning). All four owned
live runners exited. This trial supports resource feasibility at four workers,
but broader capture integrity review and a pinned concurrent schedule are still
needed before executing the 80-view panel with four workers. No background run
is active. Executors and measurement wrappers are separate from historical
two-worker evidence and do not overwrite it.

## Two-worker live engineering trial completed — 21 September 2026

Following a fresh user instruction to test two workers, host admission passed
with GPU baseline 4%, CPU baseline 0.79%, and 26.69 GiB available RAM. The exact
prepared pair ran concurrently and completed in 26.73 seconds (individual worker
durations 25.72 and 26.73 seconds). Both exited zero with `emitted` outcomes for
their assigned entity; no provider failures or executor errors were reported.
This is engineering evidence, not human correctness review or calibration data.

One-second whole-host samples from recorded dispatch through completion (27
samples, including startup and cleanup): GPU busy mean 14.89%, peak 20%; CPU busy
mean 10.95%, peak 23.33% across the machine; GPU power mean 35.04 W, peak 36 W;
VRAM peak 1.44 GiB; minimum available system memory 24.99 GiB. These are sampled
values, not guarantees against sub-second spikes or longer-run contention.

Artifacts: `reports/two_worker_capture_trial_20260921_v1/result.json` and
`resource_samples.jsonl`; capture evidence remains under the two isolated
`reports/physical_live_episodes/r3-parallel-engineering-20260921-w*` run directories.
Measurement wrapper: `scripts/measure_two_worker_trial.py`. The bounded trial is
finished; no background workers or larger campaign were started. The original
80-view serial plan remains unchanged. This pair alone is not a controlled
serial-versus-parallel speedup benchmark or approval of higher concurrency.

## Two-worker engineering test prepared; live test blocked — 21 September 2026

Following the user's explicit "okay test it ASAP", prepared a bounded pair of
concurrent development-only engineering captures with new run IDs, ROS domains
90/91, distinct Gazebo partitions and output directories. These use map 1 chair
and doorway view 0, chosen before observing outcomes. They are excluded from
calibration and do not consume or modify the approved serial 80-view schedule.
Provider, scene and camera settings remain unchanged. This authorization is for
the two-worker test, not wider campaign concurrency.

Both actual runner `--prepare-only` requests passed. Plan and source/profile pins:
`reports/two_worker_capture_trial_20260921_v1/plan.json`. Executor:
`scripts/test_two_worker_capture.py`; execution is opt-in with `--execute` after
sourcing `scripts/ros_env.zsh`. It retains the exclusive R3 lock across both owned
children, checks resources, uses separate process groups and has no automatic
retries or background scheduling. Each worker retains a 600-second outer limit.

Host admission checks measured GPU 94% during preparation and 85% at the actual
execution attempt. The existing <=30% pre-launch safeguard refused dispatch;
neither worker started. No live isolation, capture integrity or speedup result
is claimed. Six focused pair/executor tests passed. A free-GPU window is needed
to run the prepared test; no other research process was altered.

## Approved feasibility executor ready; live resource admission blocked — 21 September 2026

Emmanuel approved the exact proposed 80-view development-only feasibility scope.
The conversation transcription and manifest binding are retained in
`reports/stage1_feasibility_authorization_20260921_v1.json`. This does not grant
primary calibration, validation release, changed scientific requirements or
protected execution.

`scripts/run_stage1_feasibility.py` prepared all 80 requests successfully, using
the unchanged validated instrumentation snapshot v7 and existing provider/worlds.
The create-once execution plan, profile/source pins and exact argv are in
`reports/stage1_feasibility_execution_20260921_v1/execution_plan.json`.
The executor is serial, low priority, exclusive-lock protected, checks resources
before each launch and during owned execution, and never automatically replays a
started assignment. Errors retain evidence and stop the schedule. Other projects'
simulators and GPU busy above 30% block launch; the 30% threshold is a conservative
operational safeguard, not a proven universal noninterference boundary.

Actual live admission was attempted and refused before any start event because
GPU utilization was 83%. Subsequent read-only samples also showed contention.
No new capture was consumed, no simulator launched, no other job changed, and no
background queue is running. The approval need not be repeated; the same pinned
schedule can be admitted when resources pass. Use the ROS environment and
`scripts/run_stage1_feasibility.py --output reports/stage1_feasibility_execution_20260921_v1 --execute`.

Verification: 923 tests passed, one skipped, one numerical warning in an existing
synthetic camera-model test. Eight focused feasibility/executor tests passed.
Research remains incomplete; current live progress is constrained by shared GPU
availability, with later scientific gates still required.

## Stage 1 map screen and bounded proposal prepared — 21 September 2026

Four low-priority offline workers screened all ten development maps. The final
proposal contains 80 unique views: four original assigned targets per map, with
target-facing and fixed off-centre orientations. All pass footprint and analytic
wall-ray checks, not rendered visibility or detector verification. Earlier v1/v2
screening records are retained; v3 is the proposal. Four geometry tests pass.

`docs/STAGE1_BOUNDED_PREFLIGHT_20260921.md` binds the exact v3 manifest and requests
80 serial design-only development captures, with no automatic retries, no source/
camera/score changes, no calibration eligibility and no validation/protected access.
The user authorized offline workers; no live feasibility scope is inferred from
that authorization. Runtime/profile pins and resource admission still precede
execution even if the proposed scope is approved. No new simulator ran this turn.

## Four-worker Stage 1 offline audit executed — 21 September 2026

Following a fresh host-headroom check, four nice-19 CPU workers reconstructed
detector components and confidence for all 397 retained development targets.
All 397 completed without audit errors; all reconstructed scores match within
1.12e-16 using the explicitly recorded min_pixels=18, radius=.9 and temperature=1
assumptions. Resource gates passed before, during and after dispatch. Results and
per-input hashes: `reports/stage1_offline_audit_20260921_v1/`.

This real offline batch took about 4.85 seconds; it is not completion of Stage 1
and does not validate the previous full-stage time estimates. All pixel support
terms are saturated. A fixed-orientation inverse-square area heuristic gives
median depths near 9.95 m for chairs and 11.64 m for doorways to reach 72 pixels.
These are not validated reachable poses or guaranteed low-confidence observations.
Map feasibility and a bounded prospective collection design remain to be prepared.
No simulator was launched, validation labels read, provider changed or new human
label generated. The batch finished; no continuing background worker is implied.

## Current correction: development review received, calibration blocked — 21 September 2026

The older entries below describe earlier checkpoints, not current outstanding
review requests. All 80 diagnostic assets have acceptance decisions recorded.
The development return is present and its SHA matches the calibration pipeline's
input provenance. A sealed validation return is present; this status check and
recovery preparation did not open validation labels or release a key.

The 397 development labels are all correct. No class has a low-confidence sample;
doorway and both entrance classes also lack medium-confidence samples. Coverage
v2 therefore fails and `development_calibration_candidate.json` reports
`coverage_blocked`, with null class models. No actual calibration can be frozen.
The generic freeze invitation in the historical proposal is not actionable while
these requirements fail. Do not ask Emmanuel to repeat completed reviews or
release validation to resolve a development coverage failure.

`docs/CALIBRATION_RECOVERY_PROPOSAL_20260921.md` proposes development-only
feasibility/design preparation followed by an exact prospective collection
amendment, preserving original evidence, coverage requirements and validation
separation. It is not an executable schedule or permission for another wave.
An explicitly narrowed descriptive study is an alternative, not assumed approval
to abandon the original research question. Final calibration, design decisions,
campaign/held-out evaluation and release remain incomplete.

Recovery preparation includes an exact-ID score-support audit of all 397
development targets: every component has at least 72 pixels, the saturation
threshold at default min_pixels=18. The sampled views therefore did not exercise
reduced support. Evidence: `reports/development_score_support_20260921_v1.json`.
No new capture, provider change, validation access or human label was generated.

## Automated chain complete; human gates open — 14 September 2026, 13:40 UTC

Everything the agent could run without new human decisions has run. Full
record: `docs/EXPANSION_EXECUTION_20260912.md`. Deliverables:

1. **Diagnostic asset review (80/80 rendered):**
   `reports/expansion_diagnostic_asset_review_20260914_v2/index.html`. Decide
   accept/revise/reject per candidate and the occluder definition; return
   `DECISIONS.json` bound to the v2 manifest hash. The earlier 78-candidate
   packet is superseded.
2. **Development review kit (397 targets):**
   `reports/expansion_review_development_20260914_v1/research3_expansion_development_review_kit.zip`.
3. **Validation review kit (160 targets, withheld return):**
   `reports/expansion_review_validation_20260914_v1/research3_expansion_validation_review_kit.zip`.
4. **Feasibility evidence:** 160 paired B5/B6 development episodes; B5 0.847
   and B6 0.736 ordered completion, paired discordance 0.139, world ICC about 0.
   Power for +0.10 at six held-out worlds: 0.05 (1 seed), 0.22 (2), 0.60 (4),
   0.90 (8). Sample size and confirmatory status are Emmanuel's decision.
5. **Calibration pipeline** waits on the development return
   (`scripts/fit_expansion_calibration.py develop`), then the freeze decision,
   key release and `validate`.

Collections: development 400/400 (399 emitted, 1 infrastructure failure, 2
completed attempts with bytes lost in a host restart), validation 160/160
emitted, all under instrumentation snapshot v7 after v4/v6 transform races.

## Development collection complete; validation running — 14 September 2026

The 400-attempt development expansion schedule is complete under instrumentation
snapshot v7: 399 emitted, 0 nondetections, 1 infrastructure failure with its
single retry used (`reports/expansion_collection_development_20260912_v1/report.json`).
The host restarted twice on the morning of 14 September (07:17 and 07:38 UTC);
two attempts completed just before the second restart lost their retained bytes
before flush and are listed as `evidence_unrecoverable` in the report and the
kit accounting. They are not re-run.

**Development review kit ready:** `reports/expansion_review_development_20260914_v1/`
(`research3_expansion_development_review_kit.zip`, 395 MB, SHA-256
`ec2fcb32bd534c46fc2d9032cecbf478ae9f15de37ca24c1f2a45fec283e769e`).
397 review targets (99 chair, 98 doorway, 100 laboratory entrance, 100 office
entrance; 37 to 40 per map), each the assigned entity's emission from the exact
retained frame; 742 other emissions in the same frames are inventoried but not
targets. Automated pixel checks passed on all 1,139 emissions. Follow the kit
README: preview, approve the rebound rubric, review, return the ZIP.

Validation collection (160 attempts, one v2 camera freeze per view, gated on the
complete development report) completed at 11:20 UTC: 160 of 160 emitted, no
failures. **Validation review kit ready:**
`reports/expansion_review_validation_20260914_v1/research3_expansion_validation_review_kit.zip`
(159 MB, SHA-256 `6665d7c9f7ec1ef0e2940ea28cf65edcd561d7f8b2a28ceecbdaaffa5600519d`),
160 targets. Review it in a separate sitting, seal the return with your own key
as its README and `docs/VALIDATION_DELAYED_RELEASE.md` describe, and send only
the sealed envelope. The paired B5/B6 feasibility episodes (160) and the two
outstanding occluder re-renders follow in the same detached chain
(`reports/expansion_chain_20260914/`).

Earlier snapshots v4 and v6 failed on exact-stamp transform races; v7 gates
arming on a provider transform-readiness file. Details:
`docs/EXPANSION_EXECUTION_20260912.md`.

## Expansion execution in progress — 12 September 2026 (afternoon)

Emmanuel asked for every outstanding item to be completed. Full record:
`docs/EXPANSION_EXECUTION_20260912.md`. Summary of state at the time of writing:

- **Rendering camera finding.** The v1 diagnostic assets were placed with the
  localization `camera_depth_frame` transform, which is about 0.06 m behind,
  0.05 m left and 0.11 m below the Gazebo sensor that renders pixels. All four
  rendered v1 occluders covered 0% of the projected marker box. A rendering
  camera model was derived from the robot description and verified on 40
  control renders within 7 mm (`reports/rendering_camera_verification_20260912_v1.json`).
- **v2 diagnostic candidates** rebuilt with that model (80/80 static audit v3
  passed). 78 of 80 rendered; all 78 pass agent preflight with occluder box
  coverage 0.174 to 0.203. Asset-review packet:
  `reports/expansion_diagnostic_asset_review_20260912_v1` (open `index.html`).
  Two occluders re-render after the simulator frees; human acceptance pending.
- **Collection running.** The development partition (400 attempts) started at
  11:22 UTC under `reports/expansion_collection_development_20260912_v1` with
  instrumentation snapshot v4; the chain continues into the development review
  kit, validation collection (160 attempts, per-view freezes, gated on the
  complete development report), the validation kit and 160 paired B5/B6
  feasibility navigation episodes. Lifecycle ledgers are append-only.
- **Power feasibility.** Declared-grid simulation at six held-out worlds: one
  seed cannot reach 0.80 power for +0.10 under any grid value; four seeds
  reach it only at paired discordance 0.10 and ICC 0; eight seeds at
  discordance 0.10 and ICC up to 0.10. Empirical nuisance estimates follow from
  the feasibility runs.
- **Calibration pipeline** (`scripts/fit_expansion_calibration.py`) is
  implemented and waits on human labels; no fit exists.
- Source committed on `main`; 913 tests passed before the chain started.

## Exact-frame wrapper preflight passed — 12 September 2026

The user explicitly approved the proposed R3-only wrapper and isolated preflight.
The conversation transcription is preserved in
`reports/human_wrapper_decision_20260912_v1/decision_record.json`. No blanket
campaign or protected-access authority is inferred.

The wrapper invokes the unchanged provider computation exactly once on the
retained RGB-D bytes and camera information, verifies image integrity, waits for
the exact-stamp transform, and records completion/failure plus emitted messages.
Its live camera subscriptions point only at unused isolated topics. An explicit
completed zero-emission record can establish nondetection; missing/failed
completion, wrong frame binding or incomplete emission delivery cannot.

`r3-expansion-instrumentation-dev01-preflight-v2` exited successfully. The retained
frame at 10.500 s was processed, all five emitted observations matched delivery,
and the exact assigned `dev_01-r001-red-chair` was selected. One raw frame and one
context frame were retained, with zero contacts and no motion commands. This is
development engineering evidence outside the primary calibration schedule, not a
human label or calibrated model. The earlier failed preflight remains unchanged.

Snapshot `reports/expansion_instrumentation_snapshot_20260912_v3/snapshot.json`
still validates after execution (SHA-256
`8529e27096464c82faa0fcb23acadc6199a2f95bb5c5311eee6233d19333b32b`).
Historical source/archive bytes and provider files remain unchanged. Snapshot
status describes its creation-time evidence; this subsequent live result is
separate, not a rewrite of that immutable snapshot. No R3 runner remains active.

Verification: 902 tests passed, one skipped. Synthetic wrapper tests cover empty
completion, processing exception, corrupt input, duplicate polling, wrong-stamp or
hash binding, and missing message delivery. The live check validates the emitted
path on one development view; it does not establish all-world collection readiness
or replace rendered diagnostic review, complete primary collection, human labels,
calibration/model gates, power feasibility or campaign approval.

## Active integration and isolated preflight — 12 September 2026

P4 capture integration now exists behind an explicit opt-in source pin. Snapshot
`reports/expansion_instrumentation_snapshot_20260912_v2/snapshot.json` admits only
the capture-runner change relative to the preserved historical source manifest,
plus the two named instrumentation candidates. Provider bytes remain unchanged.
The old source manifest is preserved as history, not claimed to match the changed
active runner. Source-admission regression tests pass.

One isolated, low-priority, resource-guarded development preflight actually ran:
`r3-expansion-instrumentation-dev01-preflight-v1`. It retained a valid synchronized
frame, but no exact-frame provider processing evidence. The infrastructure failure
is preserved; it contributes no primary calibration observation or negative label.
The provider selects newest buffered frames, independently of the collector's
earliest-frame schedule, and lacks empty-result completion acknowledgment.
See `docs/EXPANSION_PREFLIGHT_FINDING_20260912.md` for measured timestamps, a
read-only reproduction and the narrow wrapper proposal requiring explicit approval.
No expansion or protected campaign was launched.

The accepted P2 numerical calibration implementation now has synthetic tests for
classwise grid fitting, weights, coverage, fold failure retention and validation
metrics/screens. It is not connected to live calibration, human label import or
artifact release. See `docs/CLASSWISE_CALIBRATION_IMPLEMENTATION.md`. No genuine
expansion labels, fitted calibration model or claimed validation result were
generated. Remaining work is not exclusively human work.

Verification after this integration: 894 tests passed, 1 skipped; Python compile
checks and `git diff --check` pass. The new source pin still validates after the
live run, and no owned R3 live runner remains. Host resource guards passed both
before and after the trial. This is not a measured guarantee of unchanged R2
performance; no R1/R2 source files or experiment processes were modified.

## P1–P4 method decisions accepted — 12 September 2026

Emmanuel supplied the follow-up decisions, declared 09:30 BST. The structured
conversation transcription is
`reports/human_method_decisions_20260912_v1/decision_record.json`, bound to the
published method-addendum ZIP. P1 accepts the sign-flip method for investigation,
not final inference/power/sample size. P2 accepts the exact prospective classwise
temperature protocol, not a fitted model. P3 accepts reviewer-held-key validation
sealing with a later human release gate. P4 authorizes R3 capture instrumentation
revision while preserving provider code, geometry, settings, coverage and history.
These decisions do not grant blanket execution, protected access or diagnostic
collection without rendered asset review.

Hardened the two authorized instrumentation candidates: explicit readiness evidence
and a positive simulation clock before one-time arming, synchronized callback
access, rejection of delayed pre-arm images/observations, and separate attempt
classification that treats empty/interrupted/truncated or invalid streams as
infrastructure failure. A target nondetection requires other exact-frame provider
emission evidence, avoiding an invented empty-frame acknowledgment from the frozen
provider. All raw observations remain retained; no negative probability labels
are manufactured. Focused instrumentation tests: 22 passed.

The source-revision authorization blocker is cleared. Active runner integration,
new source admission checks and isolated development live preflight are still
engineering work before expansion collection. Candidate snapshots explicitly do
not claim these gates passed. No new simulator was launched in this decision-import
turn. Historical source/provider validation remains intact.

## D1–D8 human decisions received — 12 September 2026

Emmanuel supplied his scientific decisions in this conversation, declared
2026-09-12T08:58:00+01:00. The structured transcription is
`reports/human_decisions_20260912_v1/decision_record.json`, explicitly not an
original signed file or independently authenticated identity. Accepted planning
inputs: B6−B5 ordered completion, the D2 exploratory/weighting/missingness policy,
+0.10 absolute effect, two-sided alpha .05 and power target .80. Final method,
sample size, seed list, calibration and actual results remain unapproved.
Confirmatory ambition is conditional on prospectively assessed feasibility, not
on favorable held-out results. The target endpoint does not establish a clinical
or catastrophic-collision improvement.

Prepared a world-paired statistical proposal and exact classwise development-only
temperature-calibration proposal for review. The six-world sign-flip sensitivity
is analytic only; nuisance estimates and empirical power remain null. Implemented
reviewer-held-key AES-256-GCM validation sealing and hash-bound release checks;
seven synthetic crypto tests pass. No real labels were encrypted/decrypted and
no real key was generated. New validation kits include withholding instructions;
hashes alone are not presented as confidentiality or independent blinding.

The separate method addendum is generated by `scripts/package_method_proposals.py`.
It preserves previous accepted choices and asks only unresolved method/workflow
and capture-source-scope decisions. D1–D8 did not authorize the capture source
revision. The old source freeze and original published review packets stay intact.

## Expansion candidate implementation — 12 September 2026

All 80 diagnostic candidates now exist: 40 spheres and 40 neutral occluders.
Independent static audit v2 passes all 80, including original geometry/hash checks
and conservative occluder wall/ground clearance. Occlusion is analytic 20% of a
provider marker-box silhouette, not a verified rendered/full-semantic-object mask.
Rendered preflight and human acceptance of exact assets remain outstanding.

Implemented/tested a separate, unarmed-by-default collector candidate and pure
selection policy, plus partition-scoped variable-size portable expansion packaging.
No live run or new human observation kit was produced. The frozen source validator
still passes, and all original pinned provider/R3 sources remain unchanged.
The original collector is detection-triggered and cannot implement the accepted
earliest-frame/nondetection schedule unchanged. Integration therefore requires an
explicit capture-source revision, not reuse of the old freeze. See
[implementation evidence and remaining gates](EXPANSION_IMPLEMENTATION_GATE.md).
This is additional offline progress, not proof that every non-human task is done.

## Consolidated human-action packet — 12 September 2026

`reports/research3_human_actions_v1.zip` contains actionable study-decision prompts,
a plain-Markdown response document, a dependency-free return packager, source
references and the full future human-gate register. It has zero new observation
images and does not ask for approval of unfinished assets or future results.
The accepted pilot and eight amendment decisions are not reopened. The packet
distinguishes human scientific choices from empirical nuisance estimates that the
agent must obtain; final replication and result approvals remain evidence-dependent.
See [human instructions](HUMAN_ACTIONS_README.md),
[decision reference](HUMAN_DECISION_GUIDE.md) and [gate register](HUMAN_GATES.md).

The return utility permits partial responses, checks fixed-file hashes, refuses
unchanged templates and never grants execution/calibration authority. It creates
only a new private local ZIP; no GitHub upload or source commit was made. Human
feedback cannot guarantee immediate study closure: asset checks, authorized live
measurements, coverage, calibration and final inference still must be completed.
The documentation skill informed the task-oriented instructions and separation
of decision reference from future prerequisites; unrelated skill setup/sync and
commit steps were outside this task and were not performed.

## Diagnostic construction continuation — 12 September 2026

Built all 40 same-colour sphere candidates in
`reports/calibration_expansion_distractor_assets_20260912_v1` with the new
`scripts/prepare_expansion_distractors.py`. All pass static placement and camera
footprint checks. Independent verification checked all source/derivative hashes,
preservation of original SDF subtrees and non-world assets, and zero added
collisions/plugins. Seven synthetic builder safety tests pass; 35 tests pass for
the builder, approval handoff and amendment planner together.

These are actual built world candidates, not detector observations or final
review evidence. Rendered visual preflight/asset approval, the 40 occlusion
candidates, the fixed expansion executor, captures and the consolidated human
review package remain. No simulation was launched and no R1/R2 file or process was
changed. The sphere candidate README lists the exact deterministic geometry-only
placement recipe and its limitations. No claim of research completion is made.

## Accepted pilot return and expansion preparation — 12 September 2026

Emmanuel Alabi Olasubomi supplied the original return ZIP, amendment decision and
usability audit. All three reported SHA-256 values match the received files.
The original portable kit validates 60 binary labels (56 correct, four incorrect),
with no excluded items; calibration coverage remains blocked as expected.
All eight amendment gates accept the exact frozen v2 proposal hashes. Emmanuel
also explicitly confirmed in this conversation that he personally performed the
review. The 47.44-second journal recording span is not treated as inspection time
or evidence against that confirmation. No independent identity certificate is claimed.

The create-once preparation archive is
`reports/calibration_expansion_handoff_20260912_v1.zip`; its extracted README,
receipt, original returned files, frozen plan and full validator result are in the
matching directory. It is **not a new observation review kit**: it contains zero
expansion captures. Current world/profile/source-plan bindings still match the
approved proposal. The frozen draft files are deliberately unchanged; acceptance
is a separate hash-bound decision. Pilot labels remain excluded from final fit
and validation. The prior entries below are historical, including pending-review
and publication statements that have since been superseded.

The user requested one consolidated remaining observation review. This requires
preserving separate development, validation and diagnostic panels and withholding
validation verdicts from model selection. There is a pre-collection sequencing
constraint: the approved amendment also requires exact diagnostic assets to be
built, visually/static-preflighted and reviewed before collection. Those assets
are still specifications, not approved built derivatives. The existing historical
distractor builder supports different restricted conditions and cannot simply be
reused as if it satisfied the new 20%-occlusion/80-attempt specification.
No new simulation was launched. Host read-only preflight observed an active R2
driver, 26,248,276 KiB available RAM, CPU pressure 0%, load 0.96875/24 logical CPUs;
these are a snapshot, not a reservation or proof of zero interference.

`scripts/package_expansion_handoff.py` now reproduces binding/return validation,
checks current plan agreement and preserves originals without granting launch
authority. Focused verification: 40 tests passed. No R1/R2 files or jobs changed.

## Two-phase calibration amendment — 11 September 2026

Prepared draft R3-CA-20260911-01 in response to the anonymous peer review. The
60-item kit remains Phase 1 rubric/distractor evidence, pending the actual human
review return. Narrative correct/incorrect totals are not imported as labels.
The original coverage numbers are unchanged. The proposed Phase 2 schedule has
560 primary capture attempts, all passing static map-footprint preflight, plus
80 separately specified engineered diagnostic attempts excluded from calibration.
The diagnostic derivatives are not yet built/preflighted. No live collection,
human approval, calibration freeze or protected access is authorized by this draft.
See [amendment and pending form](PHYSICAL_CALIBRATION_EXPANSION.md).

## Portable reviewer kit — 11 September 2026

`reports/research3_reviewer_kit_v1.zip` is ready for transfer: 60 targets, 46
nonprotected captures, concrete proposed criteria, pending accept/revise/reject
form, local preview/review server and hash-bound return validation. No ROS/Gazebo
or project checkout is required. Proposed rules remain unapproved; preparation
generated no human labels. Research 2's review/approval structure was inspected
read-only, not its approval copied into Research 3.

Verified extraction, relocation, first/last image decoding and real localhost
CLI/HTTP serving without repository PYTHONPATH. Synthetic return tests exercise
the real exporter and reject contradictory judgments even after archive hashes
are recomputed. Full suite: 793 passed, one sandbox socket skip. Actual review
kit test server was shut down. No public upload has occurred; an external reviewer
needs the ZIP forwarded or an agreed hosting destination.
See [portable instructions and limits](PHYSICAL_PORTABLE_REVIEW.md).
Earlier engineering archives remain unchanged; this is a subsequent deliverable.

## Active pre-review continuation — 11 September 2026

Latest continuation: the authorized held-out runtime and protected derivative
builder are implemented and tested with synthetic fixtures only. Full verification
reached 781 passed and one sandbox socket skip; the separate host-side review
suite passed all 26 tests. The post-authorization development regression
completed the ordered instruction with zero collisions/timeouts/infrastructure
failures, but its independently measured 0.351632 m goal error exceeds the unchanged
0.35 m tolerance; point-goal success is false.

**Engineering preparation is ready for human policy decisions, not a completed
scientific study.** All 42 fresh ordinary captures and four prespecified distractor
captures are complete and individually presentation-checked. The new
captures bind the current R3 and provider source snapshot, archived before capture
in `reports/fresh_capture_sources_20260911_v1.tar.gz`. Validation uses
`reports/engineering_camera_settings_v3`. The provider's correctness contract
requires acceptable category, stable-entity association **and pose**, not category
alone. The replacement review exposes corresponding reference evidence for all
60 targets and separate explicit judgments. Its rubric remains a draft, so saving
is disabled. Catalogue-supplied yaw is not an independently estimated orientation.
Legacy category-only verdicts cannot silently enter joint calibration. The exporter,
candidate fitter and deployment-admission checks preserve this contract.
No physical human correctness verdicts have been entered. The older v1
60-item packet remains historical image/claim evidence, but source comparison
found older runner/adapter revisions and a missing historical semantic-route source
pin. It must not be presented as calibration of the current runtime. The replacement
is `reports/physical_review_packet_20260911_v2`, independently byte-audited against
all 46 source-bound captures. Old captures, settings freezes and baseline archive
remain unchanged.

All 30 planned stationary development views and all 12 validation views are captured.
Validation used development-frozen camera settings and viewpoint/source bindings
(`reports/engineering_camera_settings_v3` for the fresh captures). All 14 readable derivatives
preserve collision geometry and stable IDs. LAB/OFFICE lettering supplies genuine
review context; the detector remains a simulated RGB-D colour-marker bridge, not
a learned shape or text recognizer. Camera-setting freeze is **not** confidence
calibration or an experiment-protocol freeze.

The corrected physical INSPECT completed at the short observation-facing viewpoint.
Fresh anchor evidence passed after 2.094 seconds' dwell, then the unchanged
one-inspection budget correctly caused abstention. No collision, timeout or
infrastructure failure occurred. See
[independent audit](../memory/2026-09-11-inspection-v2-audit.md).

Exact-frame batch association, individually bound machine visual QA, explicit
review sampling, a separate human-review UI/export path, fail-closed scheduled
execution, interrupted-outcome auditing and updated engineering packaging are
implemented. The final unlabelled packet contains 60 individually checked targets
from 46 runs: 56 ordinary targets and four deliberate shape-stress targets. The
independent packet audit verifies all bindings and zero missing selected items;
all 3,960 source rows are retained. Stress examples are not estimates of natural
error prevalence. See [current review handoff](PHYSICAL_PRE_REVIEW_HANDOFF_20260911.md).
No new human labels have been generated. Final calibration, scientific
design approval, comparative/held-out execution and final release remain incomplete.
Eleven smoke cases now have independently audited measurements (ten original runs
and a separate interruption retry): nine ordered completions and five point-goal
successes, with zero measured collisions/timeouts. The interrupted original is
retained. These are single-layout engineering checks, not campaign estimates.
Exact scene/profile/FOV/source calibration binding, a separately approved
non-protected campaign wrapper, default-deny physical held-out post-execution
audit and scientific release gate are implemented. The corrected desktop preview
was checked in the real browser; no real mobile-device verification is claimed.
R1/R2 files and processes are not modified; bounded R3 coexistence does not prove
zero impact on R2 performance. Earlier entries below are historical snapshots.

## Latest laser and camera continuation — 11 September 2026

Two serial guarded development runs completed and shut down. Laser/SDF audit on
42 scans shows 94.7–100% of finite rays within 10 cm per scan, weakening a large
fixed sensor-frame mismatch hypothesis. Localization variation remains unresolved;
no AMCL settings or scoring thresholds changed. Point errors were 0.250 m and
0.160 m, both passes, with correct ordered routes and no collision/timeout.

Opt-in R3-owned wider RGB/depth FOV improves chair context: two of five individually
inspected matched frames now show the recognizable chair. The other three remain
withheld; entrance plaques still lack visible office/laboratory identification.
No consolidated human review is ready. 292 tests pass; R2 remained active and its
files were not changed. See [debug report](../memory/2026-09-11-laser-and-widecamera.md).

## Latest live continuation — 11 September 2026

Two more guarded serial development runs completed; both stopped and R2's campaign
remained active. Timestamp-paired localization telemetry demonstrates drift from
0.013 m to 0.580 m in the chair-present run, which ends 0.613 m from the goal.
The localization mechanism remains unresolved; scoring thresholds are unchanged.
The absent-chair run passes ordered route, terminal and point-goal checks (0.267 m),
with no collision/timeout and zero anchor observation IDs in decision candidates.
These are engineering cases, not comparative performance or calibration evidence.

All five previously matched frames were individually inspected and withheld from
human review for insufficient visual context/identity cues. The relative-path
review-join bug is fixed with a failing-before/passing-after regression; actual
join output is unchanged. 286 tests pass. See
[diagnostic handoff](../memory/2026-09-11-localization-and-review.md).

## Authorized coexistence trial — 11 September 2026

One isolated low-priority B6 development episode completed alongside Research 2's
single-worker S3 campaign: `r3-coexist-dev10-20260911-v1`, ROS domain 89, explicit
Gazebo seed 1. Research 3 processes shut down; the same R2 campaign PID remained
active. No R1/R2 files or processes were changed. Resource samples recorded peak
10-second CPU pressure 4.18% and minimum available RAM 23.16 GiB. GPU telemetry
and unchanged R2 performance were not established; this is bounded feasibility,
not proof of zero interference or permission for campaign-scale concurrency.

Independent audit: correct ordered route and terminal, no collision/timeout,
but point-goal error 0.4494 m exceeds the unchanged 0.35 m threshold. Navigation
success is therefore false despite Nav2 reporting success. Capture retained five
exact observation-triggered RGB-D frames and 14 independent context frames.
Exact join yields five visual-QA candidates; 542 other provider observations lack
the required retained frame/trigger association. None is yet human-review approved.
The exact-join CLI required an absolute run path (relative-path handling remains
a tooling issue); the successful audit used the same retained bytes unchanged.

Evidence: `reports/coexist_dev10_independent_audit_20260911_v1.json`,
`reports/coexist_dev10_exact_join_20260911_v1.json`, and the run's `resource_guard.json`.
Default R2-idle protection remains; the explicit coexistence flag is limited to
development episodes with timeout at most 120 s and CPU/memory/load checks.

## Current handoff — 11 September 2026

The identified offline implementation pass is complete: absent-anchor runtime
integration, actual simulator seed wiring in an R3-owned launch, consolidated
review gating, comparative analysis/missingness bounds and release-integrity tools.
Verification: **280 Python tests**, **112 non-protected condition preflights**,
two ROS package builds and four package tests pass. No live simulator was launched
and Research 1/2 files were not changed. New live evidence, real human labels,
calibration and final experiment-design approval remain required.
See [offline handoff](OFFLINE_COMPLETION_20260911.md) for precise limits and next steps.
All dated entries below are historical, including earlier missing-integration notes.

## Latest offline continuation — 10 September 2026

Pre-review work continued: 14 separate development/validation missing-chair worlds
were built and passed independent geometry audits. All non-chair models, four
route goals and canonical task geometry are preserved; chair geometry, occupancy
and perception truth are removed. Original world hashes were checked unchanged.
The full suite now passes 209 tests. Runtime absent-anchor integration and live
validation remain open; this does not authorize missing-landmark campaign runs.
Research 2 remains active and no competing simulation was launched.

Human review is deferred until the consolidated non-protected capture set has
passed exact-media checks and individual visual QA. Independent engineering,
analysis implementation and packaging preparation can precede that review;
calibration fitting/freezing and the final calibrated comparative campaign cannot.

Latest extension: 206 tests pass. Added optional detector-independent full-frame
context sampling after runtime readiness, alongside exact detection-linked capture.
Combined capture options pass the offline runner preflight (no simulator launched).
The runner now refuses missing-landmark variants in unchanged chair-present worlds;
physical absence interventions remain unimplemented and must be validated before
that campaign condition can execute. Capture/launch/resource-guard source hashes
are included in new run requests. Research 2 activity still prevents a quiet live
validation run; no Research 1/2 files were changed in this extension.

Follow-up: exact provider-to-frame join implementation is now available, with
11 additional regression tests (202 total passed). It rejects invalid media,
identity/timestamp/pixel mismatches and protected map inputs; successful joins
still require individual visual QA. Research 2 remains active, so no new live
capture or detector-performance claim was made. See the detector preparation doc.

Research 2's six-worker recovery campaign is active. No Research 3 simulator was
launched during this continuation; no Research 1/2 source or result files were edited.
The runner now checks known Research 2 experiment drivers before launch and during
navigation, refusing/interruption-cleaning its own run if they are active. This
host-process check is not a resource reservation: live use still needs a confirmed
quiet window and host-visible process inspection.

- Stage 1: added an eight-second post-inspection fresh-evidence deadline, with
  regression tests; missing anchor evidence terminates in abstention.
- Stage 2: audited all three retained pilots. None has exact detection-to-image
  matches suitable for human review. Optional `--capture-review` now connects
  observation-triggered exact-frame capture and pending provider pixel-review logs.
  This wiring still needs live verification and item-by-item visual QA before
  asking a human to review. Independent frame sampling is also needed for recall.
- Stage 3: created a non-executable 560-episode development/validation draft, with
  240 held-out reservations only. No protected catalogues were loaded. Physical
  corruption interventions, seed/power decisions, calibration and protocol freeze
  remain prerequisites; the matrix is not campaign completion.
- Stage 4: independently analyzed and bundled all three pilot attempts, including
  failures. The bundle is an engineering snapshot, not a final reproducible study.

See [detector preparation](PHYSICAL_DETECTOR_VALIDATION.md),
[protocol draft](PHYSICAL_PROTOCOL_DRAFT.md), and
[continuation evidence](../memory/2026-09-10-stage1-inspection.md).
Earlier test counts and milestones below are historical.
Verification for this continuation: 191 offline tests passed; the two affected
ROS packages (language_nav_runtime and language_nav_bringup) built successfully.

Latest live work: three isolated new-world development attempts completed. Their
independent audits retain one wrong-door failure, one full ordered/point-goal pass,
and one ordered pass with a 0.390 m point-goal miss. Live perception now reaches
the planner through a development-only rendered-colour profile. 161 core tests
pass. See [live debug report](../memory/2026-09-10-stage1-navigation.md).
Research 1 sources/assets were not changed. Stage 1 physical inspection validation
is still open; no campaign or detector-calibration completion is claimed.

Stage 1 has started: [runtime integration progress](STAGE1_RUNTIME_INTEGRATION.md).
The authorized parallel-development batch added the physical runner, observation
identity safeguards and four-route readiness gate. 157 core tests pass, all 14
offline runner preflights pass, and lightweight ROS fault checks pass. New-world
end-to-end execution and physical inspection validation remain in progress.
Research 2's running campaign was left undisturbed; no Gazebo run overlapped it.

Latest readiness pass: 10 September 2026. Current result and evidence:
[readiness pass](READINESS_PASS_20260910.md). Core tests: 86 passed; six ROS packages
built; seven package tests passed. Provider audit: zero blockers. Real ROS fault
checks and an independently audited development Gazebo run passed. Stage 1 can
proceed; the comparative live campaign is not ready. Earlier gate statuses below
describe historical verification, not new-world campaign evidence. Old B6 graph
results precede the corrected repeated-evidence and inspection behavior.

## Gate status

| Gate | State |
| --- | --- |
| Benchmark and split integrity | Passed. Twenty base instructions, three paraphrases each, eight corruption conditions, twelve disjoint map IDs. |
| Research 1 map/route alignment | Earlier audit passed at `697a7bc86fd2eca62866c614ef7b26b5d810cf84`. Current provider has local protected-catalogue opt-in changes; its geometry is unchanged. Landmark tests pass. |
| Core implementation | Passed. Parsing, grounding, belief updates, guarded policies, immutable logging, calibration utilities and evaluation metrics are implemented. |
| ROS 2 build and messaging | Passed. Research 3 now includes the live runtime package; all package tests pass in the combined overlay. |
| Research 2 combined monitor | Passed for non-protected integration. `/research2/warning` and the frozen `monitor_started` event are translated to `failure-monitor/v1`; smoke, malformed, missing and stale inputs fail closed. The consumed checkpoint SHA-256 is `171451f0fa21036a05a5b9eb2181568976e65131fa30f74ad3d0c88f6fea57a6`. |
| Semantic route provider | Passed. Versioned Research 1 semantic catalogues publish route proposals matched to deployed benchmark IDs. Protected catalogues remain denied by default. |
| Nav2 authority and execution | Goal dispatch/cancellation and a bounded intermediate inspection are implemented. A development pilot verified inspection completion followed by risk-driven abstention. Full instruction outcome measurement remains incomplete. |
| Live ROS contract smoke | Passed. The create-once fixture report is `reports/live_contract_smoke_v1.json`; it is explicitly not research evidence. |
| Graph development campaign | Passed as engineering evidence: 400 episodes on 6 maps. |
| Graph validation campaign | Passed as engineering evidence: 160 episodes on 3 maps. |
| Landmark-instance perception | Passed. The Research 1 provider supplies 9 non-protected scene catalogues, 9 semantic-route catalogues, 14 routes and 98 stable instances. |
| Live Gazebo landmark capture | Passed. All 14 non-protected route IDs and all 9 development/validation maps have successful captures: 3,467 raw observations over 47 stable entities. |
| Human landmark review | Passed. 121/121 rows are human verified; 86 validation samples contain 65 correct natural detections and 21 incorrect sphere-challenge detections. Identity-ambiguous v3 and clipped v4 are excluded. |
| Research 3 calibration freeze | Passed. `configs/landmark_calibration_v1.json` has SHA-256 `90ad3edd8173c1b07c80bd1acc1f50cb7342287668db857f7a289a55d32d1c99`. |
| Combined non-protected Gazebo/Nav2 campaign | Integration run recorded 14 terminal outcomes: 5 Nav2 successes and 9 monitor-driven abstentions. Its measurement monitor was never activated. Two new development pilots verify measured position/distance and retained timeout behavior after repair; see `docs/RESEARCH3_RESULTS.md`. |
| Protected held-out execution | Authorized graph campaign completed: 240 checksum-verified episodes, 48 complete paired blocks. Analysis: `reports/research3_graph_heldout_analysis_v1.0.json`. No protected live campaign has run. |
| Reproducible source release | Not frozen. Research 3 and the consumed Research 2 provider source are dirty working trees; result files pin model/config/sidecar hashes but not a clean combined source revision. |

## Results currently supported

The checksum-verified deterministic analysis remains
`reports/research3_graph_analysis_v1.0.json`. It demonstrates the expected policy
logic in the authored graph world; it is not a robot-performance estimate.

The new non-protected live analysis is `reports/live_campaign_v2.analysis.json`.
Across 10 development and 4 validation routes, every episode reached an auditable
terminal outcome and consumed at least one frozen Research 2 prediction. There were
483 predictor decisions and 13 persistent alarms across sidecars, including teardown. Navigation
completed on 5/14 routes; B6 canceled the other 9 after the live risk exceeded its
guard. The development/validation split was 2/10 and 3/4 navigation successes,
respectively. These are integration observations from truthful instructions, not a
held-out estimate and not a basis for claiming 14/14 navigation success.

## Work remaining

The authorized held-out graph campaign and its analysis are complete. B6 completed
48/48 graph cases versus B2's 36/48. This is authored policy evidence.

Ordered-gate scoring and live contact validation are implemented and tested. Local
held-out catalogues now cover three maps, six routes and 42 entities. Research 3
still needs geometry-faithful instruction annotations, comparative analysis,
a finalized live protocol/campaign, and
reproducible source snapshots. The earlier statement that all non-protected work
was finished was too broad. Details and the evidence limitations are recorded in
`docs/RESEARCH3_RESULTS.md`.

Current implementation, the prepared 560-case diagnostic matrix and local source
packaging are described in `docs/LIVE_IMPLEMENTATION_HANDOFF.md`. Terminal identity
measurement is now implemented separately from full instruction completion.

The user approved preserving doorway semantics through new Research 3 geometry.
Twenty physical worlds now exist in `data/physical_worlds_v1`; all 80 candidate
routes passed static geometry/reachability checks. Live reference trials distinguish
the correct second doorway from the wrong first doorway. See `docs/PHYSICAL_WORLDS.md`
for evidence, position-accuracy failures, retained infrastructure interruptions and
the remaining runtime/perception/protocol integration. The old task/geometry design
choice is resolved; the comparative campaign is still unrun.

Protected graph outcomes have been accessed with user authorization. Existing
landmark calibration and live integration used development/validation data only.
