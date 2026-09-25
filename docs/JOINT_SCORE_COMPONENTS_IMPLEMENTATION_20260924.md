# Wave S collection and scoring components — implementation handoff

The seven method decisions and overall acceptance are recorded in
`reports/joint_score_protocol_20260924_v1/review_decision_CONVERSATION_FINAL.json`.
The hash-bound protocol retains its historical proposal heading; it was not
rewritten after review. Acceptance is not execution or unseen-model approval.

## Implemented components

| Module | Responsibility |
| --- | --- |
| `scripts/joint_score_collection.py` | Create-once launch/arm/select/close ledger; one post-arm exact RGB-D pair; persist bytes before fixed two-second TF delay; 90-second deadline including startup; no replacement/retry; explicit failures |
| `scripts/joint_score_ros_capture.py` | ROS Jazzy subscriptions and steady-wall-clock timer, exact-time map TF, simulator-clock arming, periodic resource checks; no simulator launch or motion |
| `scripts/joint_score_wave_s_admission.py` | Exact schedule and protocol-review checks, separate manifest-bound execution authority, source hashes, nice-19 requirement, headroom, global serial lock, ordered attempts and interruption accounting |
| `scripts/joint_score_components.py` | Class-specific depth features, whole duplicate-instance abstention, acquisition-class filtering without target-ID selection, canonical content fingerprints, duplicate accounting, weights, deterministic logistic solver/prediction |
| `scripts/joint_score_pipeline.py` | Capture-byte and exact-TF validation, source-bound mount correction, completed detector/OCR result joins, feature extraction and complete ordered Wave S evidence ledger |
| `scripts/fit_joint_score_wave_s.py` | Protocol/execution/evidence/human-label joins, all 400 attempts, human dimension-to-joint consistency, unchanged learning floors, four class fits and all 40 map-out diagnostics |

The frozen v3 localizer and earlier synthetic-only fitter were not modified.
Feature extraction recomputes support from raw depth, and does not use evaluator
truth. Counterpart fields remain raw matching scores, not silently overwritten
joint probabilities. Scalar temperature calibration remains a later C-wave task.

## Verification performed

- Unit/integration fixtures exercise chair-band agreement with the pinned v3
  estimator; doorway side strips; OCR central support; strict depth bounds;
  endpoint score clipping; duplicate-instance rejection; empty acknowledged
  inference versus missing inference; immutable frame choice; late pre-arm image
  exclusion; interruption, timeout, overflow and exact TF failure.
- An entirely invented 400-attempt fixture joins labels and fits all four models
  and 40 map-out folds. Other tests require transparent unfit folds, reject
  missing/foreign/mismatched/non-human labels and preserve unreviewable cases.
  These fixtures are NOT research observations or actual human attestations.
- Admission tests exercise protocol-only authorization rejection, low-priority
  and headroom guards, global serial locking across output roots, no reordering
  and no retries of consumed attempts.
- Replay of the three saved development panels accounts for 200 slots: **159
  replayed, 41 existing infrastructure failures retained**. New selection/features
  retain 35 chair, 7 doorway, 57 laboratory-entrance and 55 office-entrance
  diagnostic emissions. These include correlated stationary frames and are NOT
  new independent samples, primary evidence, labels, or coverage certification.
- A bounded, low-priority synthetic ROS transport check on localhost domain 219
  exercised actual ROS message callbacks and exact-time TF with the new binding.
  The selected pair was persisted before the delay and a valid TF was retained.
  No Gazebo, robot motion or Wave S collection ran. The first sandbox check
  captured successfully but logged socket restrictions; a separately retained
  host-local check (`joint_score_ros_transport_20260924_v2`) passed without those
  warnings. Neither run is a source-bound Gazebo-world preflight.

Regression reports and exact input pins are linked by
`reports/joint_score_components_handoff_20260924_v1/manifest.json`.
No genuine score model was fitted, no human labels generated, and no validation
plaintext or protected world opened. Research 1/2 source trees were not edited.

## Interfaces and caller obligations

`admitted_attempt(...)` is the primary collection boundary. It verifies a separately
approved `research3-jsc-execution/v1` manifest and opens the attempt **before**
the caller starts its simulator. Run it in a dedicated nice-19 process. Pass the
returned `OneFrameAttempt` into `JointScoreCapture` on a serial ROS executor.
The caller owns simulator startup/cleanup and must stop its own processes after
the context closes. No global process killing is provided. A crash leaving a
launch event but no summary remains a consumed, unresolved infrastructure record;
do not restart that attempt or silently skip its accounting.

Execution manifests must pin the actual worlds, scenes, maps, expanded robot,
camera/bridge, model assets, environment, collection/scoring sources and actual
clearance/transport audits. The `preflight_status` assertion is not proof on its
own: inspect the hash-bound audits before human execution approval. The current
manifest validator checks schema, required groups and byte integrity; it does
not independently repeat every physical preflight or authenticate a reviewer.

Use `process_capture(...)` only with the unchanged detector/OCR engines' explicit
completion records. Each requires the selected frame hash, completed status,
source/raw-output pins and a passed upstream audit, plus boxes or texts (an empty
list is valid only with completion evidence). The caller must export these records
from the pinned, audited engines. Missing/error completion becomes infrastructure
failure, never a nondetection or human incorrect verdict. Integrity errors raise
and must be retained as failed processing, not repaired by replacing the frame.

`ordered_ledger(...)` requires exactly all 400 S attempt IDs and restores declared
schedule order, independently of execution completion order. Exact content
duplicates contribute only the earliest occurrence; rejected attempts stay in
denominators. Fingerprints consume decoded RGB, metric depth and explicit camera
calibration, not timestamps, paths or row padding.

Human returns for the fitting adapter use `research3-jsc-human-labels/v1`, wave S,
named human reviewer and timezone-aware date, canonical `evidence_sha256`, and
one verdict per eligible emission (including unreviewable verdicts). Each row
binds `emission_id` and canonical `emission_sha256`, three rubric dimensions,
`joint_verdict`, and optional `yaw_metadata`. No yaw estimate is claimed when
that metadata is not applicable. Protocol/execution/label declarations are
human attestations, not independent cryptographic identity authentication.

Run the real fitting adapter only after collection and human review exist:

```sh
PYTHONPATH=src:scripts python3 scripts/fit_joint_score_wave_s.py \
  --protocol docs/SCORE_LEARNING_COLLECTION_PROTOCOL_20260924.md \
  --schedule reports/joint_score_protocol_20260924_v1/schedule.json \
  --protocol-review reports/joint_score_protocol_20260924_v1/review_decision_CONVERSATION_FINAL.json \
  --execution-manifest PATH_TO_APPROVED_S_EXECUTION_MANIFEST \
  --execution-approval PATH_TO_HUMAN_S_EXECUTION_APPROVAL \
  --evidence PATH_TO_COMPLETE_S_EVIDENCE \
  --human-review PATH_TO_NEW_S_HUMAN_LABELS \
  --output PATH_TO_NEW_CANDIDATE_MODEL
```

The placeholders deliberately do not refer to fabricated approvals or evidence.
The output remains `upstream_freeze_approved: false` and `runtime_admitted: false`.
The retained synthetic prototype still refuses real provenance. Fitting, model
freeze, C collection and V release are separate stages.

## What still precedes Wave S launch

1. Build and audit the source-bound Wave S execution manifest and driver wiring,
   including export of pinned detector/OCR completion records into this adapter.
2. Recheck the exact scheduled poses against actual readable-world assets and
   complete the isolated development **Gazebo** transport preflight using the
   new one-frame collector. The synthetic ROS test does not replace that check.
3. Obtain the separate manifest-bound Wave S execution authorization, then collect.

This handoff completes the requested component implementation and testing, not
campaign orchestration, calibration coverage or permission to launch Wave S.
