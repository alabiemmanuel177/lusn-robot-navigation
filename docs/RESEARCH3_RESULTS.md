# Research 3 evidence report

## Final Closure: Descriptive and Exploratory Feasibility Deliverable — 26 September 2026

On 26 September 2026, Emmanuel Alabi Olasubomi (Researcher, Africa/Lagos) formally
authorized Option 2: narrow the study scope to descriptive and exploratory feasibility,
bringing Research 3 to complete, final termination.
Authority record: `reports/research3_closure_authority_20260926.json`.

### Closure Scope & Policy Decisions
- **Deliverable**: Research 3 is formally concluded under a descriptive and exploratory
  feasibility scope rather than a validated four-class runtime calibration study.
- **Candidate Status**: The frozen hybrid candidate
  (`reports/hybrid_score_candidate_20260925_v1/candidate.json`,
  SHA-256 `b9de70b9c8a829d3177bc4b709fc4e53966f9e5df8e75b3d2c8882730a559b45`)
  is retained strictly as an exploratory feasibility candidate.
- **No Further Collection**: Wave C (calibration) and Wave V (validation) are not
  scheduled or launched.
- **No Runtime Calibration Claim**: Validated four-class runtime calibration is not
  claimed.
- **Blocker Resolution**: Blockers B03 and B09 are formally resolved under this
  descriptive deliverable.

---

## Core Scientific & Engineering Findings

### 1. Structural OCR Support Truncation Limitation
A foundational finding of this research is the structural impossibility of populating
low-confidence bins under frozen upstream OCR filtering:
- **Upstream Filtering**: Pinned RapidOCR internal filtering strictly enforces
  `text_score >= 0.5` (`rapidocr_onnxruntime/main.py`). Text proposals below 0.5
  are discarded upstream before detection outputs are emitted.
- **Localizer Propagation**: The entrance localizer copies the retained text score
  directly to `raw_score` without transformation.
- **Pass-through Score Support**: Under identity pass-through, entrance input scores
  are mathematically truncated to the closed interval $[0.5, 1.0]$.
- **Coverage v2 Incompatibility**: Pre-registered Coverage v2 admission requires at
  least 5 scoreable emissions in the $[0, 0.5)$ bin for each class. For both
  `laboratory_entrance` and `office_entrance`, the maximum attainable emissions in
  $[0, 0.5)$ is identically zero.
- **Boundary Verification**: This structural barrier was verified through source audits
  and synthetic boundary testing against the actual OCR filter
  (`reports/hybrid_score_candidate_20260925_v1/ocr_support_audit.json`).
- **Conclusion**: Unchanged collection waves (Wave C / Wave V) cannot overcome this
  frozen upstream threshold. Initiating further collection waves under this stack
  would be scientifically futile.

### 2. Wave S Clean-View Precision Saturation & Error Localization
Wave S executed a fixed serial 400-attempt supervisor protocol across all 10
development environments (`r3geo_base_r001` through `r010`):
- **Execution & Yield**: 398 successful simulator captures, 2 Nav2 lifecycle failures;
  287 scoreable emissions, 72 detector/depth abstentions, 39 intact-frame nondetections.
- **Human Verification**: All 287 scoreable emissions were evaluated across category,
  physical instance identity, and planar reference localization ($\le 0.35\text{ m}$):
  281 correct, 6 incorrect, 0 unreviewable
  (`reports/wave_s_review_receipt_20260924_v1.json`).
- **Observed Clean-View Result**: Human review found **261/261 jointly correct
  emitted observations** of chairs and entrance signage:
  - `chair`: 99 correct, 0 incorrect (100.0% precision across 99 views).
  - `laboratory_entrance`: 84 correct, 0 incorrect (100.0% precision across 84 views).
  - `office_entrance`: 78 correct, 0 incorrect (100.0% precision across 78 views).
- **Geometric Localization Error Isolation**: All 6 incorrect outcomes occurred
  exclusively in the `doorway` class:
  - `doorway`: 20 correct, 6 incorrect (76.9% precision across 26 views).
  - **Confirmed error dimension**: All six were labeled reference-point incorrect,
    with category and instance correct. The labels do not establish the physical
    cause. Portal-void penetration is a proposed explanation, not a demonstrated
    mechanism for every case; the implemented estimator uses side-jamb support.
- **Scope of precision figures**: These are empirical joint-correctness proportions
  conditional on emitted observations in the scheduled development scenes. Repeated
  views share worlds. Zero observed errors does not imply probability one, population
  saturation, recall, calibrated uncertainty or generalization to other scenes.
- **Calibration Impact**: Zero negative outcomes across 261 emissions for three classes
  prohibited fitting multi-class supervised logistic models under the pre-registered
  outcome floor ($\ge 5$ incorrect required per class).

---

## Exploratory Hybrid Candidate Specification

The frozen hybrid candidate (`reports/hybrid_score_candidate_20260925_v1/candidate.json`)
provides a benchmark exploratory baseline:
- **Doorway Model**: 5-feature regularized logistic regression fitted via deterministic
  global Hessian Lipschitz bound solver on 26 valid Wave S doorway emissions
  (`reports/wave_s_doorway_amendment_candidate_20260924_v1.json`). Features: intercept,
  raw logit, valid depth fraction, relative depth IQR, reference distance scaled.
- **Chair & Signage Models**: Direct identity pass-through of original detector/OCR
  matching scores, explicitly designated as uncalibrated matching scores.
- **Validation Status**: Retained as an exploratory feasibility artifact; not admitted
  for runtime robot navigation.
- **Fit diagnostics**: The doorway solver converged after 578 updates. Seven
  leave-one-map-out folds fitted; three failed the unchanged negative-outcome floor
  and remain reported as unfit, not silently excluded.
- **Final archive**: `reports/research3_final_closure_20260926_v2.zip` supersedes
  version 1. Historical claims below remain historical, not validation of this
  hybrid candidate. Original four-class calibration success is not claimed.

---

## Historical Evidence Archive (Prior Phases)

## Authorized held-out graph campaign

The authorized create-once campaign produced 240 records: six routes on three test
maps, eight conditions, five systems and one seed. The raw campaign and every record
passed SHA-256 verification. Independent matrix checks found 240 unique run IDs,
48 complete five-system blocks, and identical eight-condition coverage per route.
The protected graph partition has now been accessed; it must not be described as
sealed or reused for tuning followed by another confirmatory claim.

| System | Episodes | Instruction completions | Critical failures |
| --- | ---: | ---: | ---: |
| B1 | 48 | 48 | 0 |
| B2 | 48 | 36 | 12 |
| B4 | 48 | 36 | 12 |
| B5 | 48 | 36 | 12 |
| B6 | 48 | 48 | 0 |

B6 minus B2 completion is +25 percentage points, with a hierarchical bootstrap
95% interval of +12.5 to +37.5 points. Critical failure difference is -25 points,
with an interval of -37.5 to -12.5 points (5,000 resamples; analysis seed 303).
These intervals describe the authored graph cases, with only three map clusters and
one execution seed. B1 also completes every case; these results do not demonstrate
that B6 improves completion over B1. B4 and B5 match B2 on these aggregate outcomes.

Artifacts:

- `reports/graph_heldout_v1.0.jsonl`, SHA-256 `432380ae41f3f605c23bf953f5172780a1656c5f50df5565e051757d1a2c73fe`.
- `reports/research3_graph_heldout_analysis_v1.0.json`, SHA-256 `75d14233d909b19c9e38ce646d6c82ebd1226360b99e33849ae46988038e03e0`.

The analysis and campaign configuration declare protocol 1.1, while raw episode
records declare 1.0. This metadata inconsistency is retained and disclosed; the
original evidence has not been rewritten. The graph observations are authored
fixtures, not deployed detector observations or Gazebo performance measurements.

## Live integration evidence and measurement limitations

The existing non-protected campaign records 14 terminal outcomes: five Nav2
successes and nine monitor-driven abstentions. All 14 consumed frozen Research 2
predictions. Its sidecars contain 483 predictor decisions and 13 alarms, including
decisions during teardown; these counts are not restricted to robot motion.

The live adapter used by v2 sets collision and wrong-goal fields to false, equates
instruction completion with Nav2 success, and records planned distance rather than
distance travelled. The v2 runner checks a separate collision monitor while waiting,
but never calls its `start()` method, so it does not accumulate active-episode
measurements. It also raises on collision or timeout without a terminal summary; the
campaign analyzer rejects collision episodes. Consequently the reported zero
collisions cannot establish an unbiased collision rate. All initial actions were
`inspect`, which currently dispatches a terminal navigation goal rather than a
distinct inspection viewpoint. Route eligibility uses a catalogue risk prior.

These facts limit the campaign to integration evidence. The immutable v2 records
and their analysis are preserved; this report qualifies their interpretation.

## Measurement repair verification, 8 September

The updated runner activates and stops the Research 1 ground-truth/contact monitor,
uses measured distance and final goal error, retains collisions/timeouts as terminal
trials, and bounds prediction counts by simulated episode timestamps. New summaries
use `research3-live-summary/v2`. Unmeasured semantic instruction completion and
wrong-goal identity are explicitly null. The older adapter sidecars and v1 campaign
analyzer remain unsuitable for estimating these research metrics.

Two isolated, non-protected development pilots verified the runner change:

- `reports/live_episodes/r3-measurement-dev00-v1/summary.json`: 247 ground-truth
  samples, 2.8149 m travelled, 0.1877 m final goal error, seven in-window predictions,
  measured navigation success under the declared 0.35 m position tolerance.
- `reports/live_episodes/r3-measurement-timeout-v1/summary.json`: deliberate 0.1 s
  wall-time limit, three ground-truth samples, timeout retained as a failed trial,
  no prediction observed. This is a timeout-path test, not a performance sample.

The planner now has an independent 0.25 s monitor freshness watchdog, rejects
future-dated timestamps, and invalidates malformed monitor input. An isolated ROS
timer test verified that stale data triggers abstention without incoming messages.
This checks publication of the stop decision; it does not independently measure
physical stopping distance. The watchdog uses ROS time and does not address a
stalled simulation clock. All 68 Python tests passed; modified ROS Python sources
compiled. These repairs do not retroactively validate the old campaign.

## Final Disposition of Remaining Work — Formal Closure

Under the formal authorization of Option 2 by Emmanuel Alabi Olasubomi on 26 September 2026,
Research 3 is formally concluded and terminated under the descriptive and exploratory
feasibility scope. Consequently:
- Items 1–5 from the historical 8 September remaining-work list are closed without further
  live executions.
- Waves C and V are not launched.
- The hybrid candidate is preserved as an exploratory candidate only, without runtime
  admission.
- Research 3 reaches final termination.
