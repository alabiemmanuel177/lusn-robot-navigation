# Research 3 status and handoff

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
