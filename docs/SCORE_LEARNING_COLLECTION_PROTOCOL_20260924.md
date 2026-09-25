# Joint-score learning and collection protocol — final proposal v1

Protocol ID: R3-JSC-20260924-01. Status: **authored and ready for scientific
review; not human-approved, execution-armed or a fitted-model freeze**.
The user requested finalization of this protocol. The already approved
world-specific sign-layout decision is not being reopened. No new labels,
validation release, unseen model acceptance or protected campaign is authorized
by this document. Existing evidence and failed candidates remain immutable.

## 1. Scope and changes requiring explicit acceptance

The target probability is joint category, physical-instance and planar
reference-point correctness, conditional on a scoreable emitted candidate.
It is not detector recall, full object geometry, calibrated covariance, learned
yaw, or generalization beyond the authored corridor/sign distribution.

This proposal replaces the synthetic prototype's underspecified depth feature
with the exact class-specific definition below. It adds a separate supervised
score-learning wave and defines duplicate handling. The learned probability,
not the original DINO/OCR matching value, becomes the **raw input to P2 and its
Coverage v2 gate**. This is a substantive observation-method amendment requiring
human acceptance, not a claim that changing names or scores cures coverage.
Original matching values and their bin tables remain in every audit.

The four-class v3 readiness manifest is the candidate authority:
`reports/four_class_perception_readiness_20260924_v1/manifest.json`.
Source/model inventory hashes are transitively bound by that manifest and the
detector/OCR plans. Verify actual files before arming, not merely manifest bytes.
Keep the fixed six-query prompt, thresholds, checkpoint, exact OCR tokens,
0.10 m chair band, portal strips, authored sign conversion, 0.9 m association
radius, camera FOV 2.0 rad and source-bound rendering transform unchanged.
Do not alter Research 1/2 sources or frozen v8 instrumentation.

## 2. Fixed sampling budget and data separation

| Wave | Maps | Simulator seeds | Fixed acquisition cells | Attempts |
| --- | --- | --- | --- | ---: |
| S: supervised score learning | development r001–r010 | 101, 102 | 4 classes × 5 views × 2 seeds per map | 400 |
| C: temperature calibration | development r001–r010 | 201, 202 | same acquisition cells, fresh captures | 400 |
| V: calibration validation | validation r011–r014 | 301, 302 | same acquisition cells, fresh captures | 160 |

These are resource-bounded engineering budgets, **not power calculations or a
promise of coverage**. The 400/160 C/V budgets retain the accepted expansion
sizes; S adds 400. No engineered sphere/occluder attempts belong to these waves.
No world r015–r020 is accessed. Validation here is distinct from the six-world
held-out comparative navigation campaign.

The exact 960 rows are in the accompanying `schedule.json`. Copy pose coordinates
and view-group identities from the previously declared
`reports/calibration_expansion_handoff_20260912_v1/plan.json`, replacing seeds
and attempt IDs only. This is pose metadata reuse, **not capture/label reuse**.
Use the approved readable-world derivative, not the historical world's hash.
Before arming each wave bind actual world, scene, map, camera, expanded SDF/URDF,
bridge, model/environment and collector hashes in a new execution manifest.
Recheck static clearance with the existing 0.30 m footprint. The protocol's
schedule does not pretend those new execution checks have already passed.

Order: S, then C after upstream-model freeze, then V after development-calibration
freeze and staged authorization. Within each wave: map, class in the order chair,
doorway, laboratory_entrance, office_entrance, seed, then view 0–4.
The acquisition class chooses a view and scoring stratum; acquisition identity
is never an inference input or a filter for the claimed instance.

Seeds and fresh timestamps do not make deterministic stationary scenes independent.
Preserve canonical RGB/depth/calibration-content fingerprints (excluding timestamp
and file headers), capture UUIDs and frame hashes. Do not reuse a physical capture
across roles. Exact repeated content within a wave contributes only its earliest
scheduled occurrence to fitting/coverage; retain all attempts in denominators.
Cross-wave identical content is excluded from the later role, with a leakage
report, never silently replaced. Shared development maps/views are deliberate;
C is not independent-world validation. Report world/view clustering and duplicate
counts. If this design yields insufficient diversity, it fails; a new collection
design requires a prospective amendment, not seed shopping or extra attempts.

## 3. Capture and missingness contract

Serial, low-priority execution (nice 19); one simulator and at most four CPU
inference threads, OCR one thread. Use the existing coexistence/resource guards
before launch and retain samples during execution. No unsolicited termination of
other workloads, unreviewed concurrency, or GPU occupancy escalation.

For each stationary attempt, arm only after camera metadata and recorder readiness
are recorded. Select the **first exact-timestamp RGB/depth pair after arming**,
independently of detections, scores, TF availability or human outcomes. Persist
that pair, then wait a fixed two seconds before its exact-time TF lookup. Use
the tested source-bound mount correction; never substitute commanded pose or
simulator truth. Simulator truth is evaluator-only when available.
One selected pair per attempt; full uncropped RGB and raw depth must survive.
Use a 90-second wall-clock attempt deadline, including startup; absence of a
complete pair/TF at closure is infrastructure failure, not nondetection.
No selected-frame replacement and no outcome-dependent retries. A pause before
an attempt starts may resume that unstarted row; interruption after launch
consumes the row. Persist launch/arm/select/close events and failure reasons.

Keep distinct: infrastructure failure; intact-frame no relevant detection;
depth/template abstention; unassociated; ambiguous association; duplicate-instance
abstention; scoreable emission; human-unreviewable. All contribute to scheduled
attempt accounting. Nondetections and abstentions are **never p=0 or invented
negative labels**. Failed inference must not masquerade as empty detection output.

The existing 20-frame deferred-TF preflight is supporting transport evidence,
not an already integrated one-frame production collector. Before primary use,
verify the one-frame adapter, timeout/accounting, immutable inputs, no-target
inference boundary, and missing-stream behavior with tests and an isolated
development transport-only preflight, excluded from S/C/V.

## 4. Emission and review unit

Run unchanged inference for all four classes and preserve every raw proposal.
Primary rows for an attempt are only its declared acquisition **class**, not its
assigned target ID. Other classes remain diagnostic evidence and cannot increase
primary quotas. A proposal must have valid localization, exactly one association
within 0.9 m, and complete finite features. No nearest-ID choice.

Group localized unique-association proposals by (frame, visual class, claimed
entity ID). If more than one proposal claims the same entity, abstain for that
whole group; do not select the highest score, average boxes or count duplicates.
Different uniquely claimed entities in the acquisition class may each emit once.
Apply this rule identically in S/C/V and any future scored runtime. Retain the
abstained proposals for diagnostic review, excluded from primary label quotas.
This conservative rule can reduce doorway yield; it is a testable failure risk,
not a guarantee of readiness after selection.

Each emitted row has immutable frame/box/source-index, class, claimed ID, measured
reference XY, raw matching score, feature vector and provenance. Reviewers see
full scene context, highlighted proposal, catalogue context and reference-point
evidence; hide raw/joint/calibrated probabilities during correctness review.
Do not prefill judgments from distance tests or transfer old-provider labels.

The human supplies category, instance and planar-reference judgments. Inclusive
distance <=0.35 m is reference-point consistency, not full geometry accuracy.
Catalogue-derived yaw is only a <1e-6 rad copy-integrity check; if no yaw is
emitted, record not-applicable, never an orientation-estimation success. Joint
incorrect if any required dimension is incorrect; joint correct only if all
required dimensions are correct; otherwise unreviewable. Preserve each dimension,
reviewer name, actual timezone-aware date, evidence hashes and revision history.
Only binary human verdicts enter fitting; unreviewable counts/reasons stay visible.

## 5. Exact score-learning model

One independent logistic model per class, `p_joint = sigmoid(beta dot x)`.
Five features in fixed order:

1. Intercept 1.
2. `clip(logit(clip(raw_score, 1e-9, 1-1e-9))/12, -1, 1)`.
   Retain the original score; clipping is numerical only. This explicitly extends
   the prototype, which rejected endpoint scores.
3. Valid-depth fraction, as defined below.
4. `min(depth_IQR / median_depth, 1)`, as defined below.
5. Measured XY distance to the sole association candidate divided by 0.9 m.
   This is an association residual, **not ground-truth localization error**.

All depth validity uses finite values strictly between 0.05 and 12 m. Pixel
bounds use the pinned estimators' ceiling/clipping rules; NumPy quantiles use
linear interpolation. Depth support is defined before labels are inspected:

- Chair: fraction of valid pixels in the central 40%-width/height ROI *before*
  band selection; IQR and median of the v3 selected 0.10 m foreground band.
- Doorway: concatenate the valid pixels in the two pinned 15%-width side strips
  (15% vertical trimming); fraction is total valid / total in-frame strip pixels;
  IQR and median from the concatenated valid depths, not the empty opening.
  Existing per-side support and disagreement gates remain unchanged. No extra
  IQR rejection is added to the doorway localizer by feature extraction.
- Lab/office: valid fraction, IQR and median of the central 40% ROI of the OCR
  quadrilateral's axis-aligned box, before authored reference conversion.

Recompute missing support summaries from the original depth; never fill with
zero, another class's statistic or a catalogue depth. Existing depth/template
abstentions persist. A new feature extractor must match these definitions and
be pinned/tested before arming. The historical prototype is not silently edited.
No map/entity ID, palette, expected target, simulator semantic truth, human verdict
or catalogue yaw is a feature. No feature standardization or parameter search.

Within each class: equal weight per represented map, then per represented
prespecified acquisition view group (seeds share a group), then per accepted
binary emission. Normalize to one; report dropped/nonrepresented cells. Require
at least one binary emission in each of ten map/class cells and >=5 correct and
>=5 incorrect per class before fitting S. These are minimum learning safeguards,
not a statistical adequacy claim. No confidence-bin quota is imposed on S's
matching scores: S is not the P2 calibration partition.

Minimize weighted binary cross-entropy plus `0.01/2 * sum(beta_j^2)`, including
intercept. Zero initialization; fixed gradient-descent step
`1/(0.25 * sum(w_i * ||x_i||^2) + 0.01)`, infinity gradient tolerance 1e-8,
maximum 20,000 updates. Nonconvergence, missing class or failed outcome floors
means no model freeze; no penalty/feature/solver fallback or additional sampling.
Record coefficients, objective, gradient, iteration count, weights and all pins.
The synthetic-only fitter remains synthetic-only until a separately gated real
fitting adapter implements provenance and review validation.

Report S leave-one-map-out diagnostics by refitting the upstream score learner
without that map, using fixed settings and S outcome floors on nine training maps.
Report failed folds explicitly. No diagnostics-based tuning. Training-set fit is
not calibration evidence. Freeze the exact four upstream models and scoring
implementation before C collection. Human acceptance of this freeze is separate
from accepting this prospective protocol.

## 6. P2 calibration, coverage and validation

P2's accepted scalar temperature family, grid, weighting, tie-breaks, numerical
clipping, ten metric bins and admission comparisons remain unchanged; see
`docs/CALIBRATION_METHOD_PROPOSAL_20260912.md` (historical proposal wording).
Fit only on C. Require independently for C and V: >=1 binary observation per
required map/class, >=5 correct and >=5 incorrect per class, and >=5 in each
**untempered p_joint** bin [0,.5), [.5,.8), [.8,1]. Always also publish original
matching-score bins. Temperature-adjusted q never fills raw-score coverage.

P2 C leave-one-map-out fits temperatures only on the other nine C maps while
holding the previously frozen upstream model fixed. Label these diagnostics
conditional on that fixed model; they are **not unseen-world end-to-end CV**,
since S includes those development worlds. S's separate map-out diagnostics
assess its learner; do not conflate the two estimates. No fold failures hidden.

Freeze final upstream model, temperatures, feature/emission rules, S/C labels,
attempt ledgers, coverage/diagnostic reports and protocol before V collection
and review. Stage V separately; do not transfer old validation labels. Emmanuel
keeps plaintext/key and returns only an AES-256-GCM sealed return according to
`docs/VALIDATION_DELAYED_RELEASE.md`. Human release approval must bind the whole
upstream-plus-temperature development artifact and protocol, not temperatures
alone. No validation feedback to selection. Existing sealed material stays closed.

After authorized release, validate the human return and apply unchanged P2
admission: macro Brier improves >1e-12; macro ECE and maximum class/bin MCE do not
degrade >1e-12; no class Brier degrades >1e-12; complete accounting and independent
coverage floors pass. These are point-estimate engineering screens, not proof
of calibration. Failure means no admission, no reuse for tuning without declaring
contamination and approving a new protocol. Human model/result acceptance follows.

## 7. Gates, handoff and completion definition

1. Human reviews the exact amendment, budget/seeds, depth features, duplicate rule,
   upstream probability meaning and unchanged P2 use. Record actual decisions
   against proposal/schedule hashes; no generated signature or backdating.
2. Implement and audit production collection/feature/real-fit adapters, read-only
   source checks, pose/asset preflight and exact execution manifest. Arm S only
   after its scoped execution authorization. Merely passing static plan tests
   does not grant execution or prove the collection chain works.
3. Complete S and its human review; fit and approve upstream freeze or record
   failure. Then complete C and its human review; freeze development calibration.
4. Clear V's separate collection, encrypted review and release gates; evaluate,
   then obtain explicit fitted-model/result acceptance.
5. Only afterward proceed to admitted live runtime, development B5/B6 feasibility,
   power/inferential decision and separately authorized comparative campaign.

Reviewer burden cannot honestly be collapsed to a single final label round:
S labels must precede C generation with a frozen upstream model. Protocol decisions
can be reviewed together now; observation packages will be grouped by wave.
Zero automatic human labels, fitted models, calibration passes, protected reads
or live launches are produced by the protocol packaging command.

Protocol completion means exact prospective specifications, reproducible schedule,
machine-checked boundaries and a hash-bound review template are delivered. It does
not mean the research, calibration coverage or scientific approvals are complete.
