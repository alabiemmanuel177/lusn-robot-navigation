# Collection and scoring implementation handoff

User asked to implement and test components before Wave S launch. Finished this
bounded implementation; no Wave S/Gazebo campaign or real model fitting started.

New modules:
- `joint_score_components.py`: exact raw-depth feature supports, endpoint clipping,
  acquisition-class selection, whole duplicate-ID group abstention, fingerprints,
  duplicate accounting, weights, fixed logistic kernel and prediction.
- `joint_score_collection.py`: persistent one-frame state machine, launch-inclusive
  90s deadline, explicit simulator arm timestamp, reject late pre-arm frames,
  two-second fixed TF delay, exact map/child/stamp/unit quaternion checks.
- `joint_score_ros_capture.py`: actual ROS binding, steady-clock timer, resource
  guards. Caller owns lifecycle; no simulator or motion commands.
- `joint_score_pipeline.py`: byte/TF joins, corrected rendering mount, required
  completed detector/OCR records, ordered complete 400-attempt evidence ledger.
- `fit_joint_score_wave_s.py`: protocol/execution/label hashes and human attestation
  joins, required dimensions, unreviewable accounting, floors, four models/40 folds.
- `joint_score_wave_s_admission.py`: exact approved schedule, separate execution
  authority, nice-19, resource check, global flock, no retries/reordering, interrupted
  attempts consumed. This is a context boundary, not a full campaign driver.

Full suite: 1,298 passed/1 skipped, no failures/errors, existing synthetic-depth
warning only. Report `reports/joint_score_components_regression_20260924_v2.xml`.
Five new test files provide 56 tests. Every invented observation/label/attestation
in tests is synthetic, not actual human review or empirical score learning.

Read-only replay `reports/joint_score_component_replay_20260924_v1.json`: three
existing development panels, 200 slots, 159 processed and 41 old infra failures
retained. 35 chair, 7 doorway, 57 lab and 55 office diagnostic emissions, NOT
coverage or accuracy evidence. Repeated stationary frames remain correlated.

Synthetic ROS test `check_joint_score_ros_transport.py` on localhost domain219:
v1 captured but sandbox socket warnings; separately preserved v2 host-local
socket-enabled test passed cleanly. No Gazebo. Both processes finished. ROS
setup's PYTHONPATH must be preserved when adding src:scripts (overwriting it
caused one import check failure, corrected). All source-bound metadata and
generated raw bytes are retained under the two transport report directories.

Handoff `reports/joint_score_components_handoff_20260924_v1/manifest.json`
pins scripts/tests/docs/results and passing regression. v8 snapshot unchanged:
6b7bc9e5dd4f5289af88ee4524db3544d277eeeb6a0685177b12c128ef6fb49a.
No R1/R2 edits, validation plaintext read, protected worlds, publication or jobs
left running. No pinned historical files or protocol text rewritten.

Still before launch: source-bound driver and detector/OCR completion-export wiring,
actual execution asset/source manifest and world clearance audits, isolated
development Gazebo preflight with this new collector, separate manifest-bound
Wave S execution authorization. Manifest checks integrity and audit references,
not independent authenticity or physical truth. Labels and fitted-model freezes
are later gates. No need to request the already accepted scientific method again.
