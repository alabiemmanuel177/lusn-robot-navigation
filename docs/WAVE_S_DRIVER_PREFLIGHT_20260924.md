# Wave S driver, actual-world preflight and execution authority

Status: **pre-launch work complete; fixed Wave S collection authorized**.
No primary Wave S attempt has been consumed or left running by this handoff.
No further execution-authorization request is needed for the bound Wave S scope.

## What is connected

`scripts/joint_score_wave_s_driver.py` connects the approved one-frame state
machine to stationary Gazebo/ROS/Nav2 startup, localization readiness, exact-time
TF, isolated transport, serial admission, resource checks, and owned-process
cleanup. The 90-second budget includes startup. Primary attempts use schedule
IDs and seeds, nice 19, a shared collection lock, and create-once directories.
There is no route dispatch, failed-attempt replacement, or motion command.

`scripts/joint_score_wave_s_inference.py` runs the unchanged pinned detector and
OCR engines in their existing CPU environments, verifies their reports and raw
detector reconstruction, and produces frame-bound completion records for the
class-specific feature and scoring pipeline. A complete primary batch must
account for all 400 scheduled attempts, including infrastructure failures.
Wave S produces features and later human-review evidence, not a learned joint
probability before human verdicts exist.

## Checks and evidence

- All 400 scheduled S poses across ten development worlds passed the existing
  0.30 m footprint static-clearance checker against their actual map assets.
  This is static clearance, not an exhaustive dynamic-collision guarantee.
- Four fixed frontal r001 views, one per acquisition class, were captured in
  Gazebo with engineering-only seed 29. Every view retained the synchronized
  post-arm frame, measured exact-time map transform and fixed two-second delay.
  Capture wall times were 18.68–22.15 seconds, excluding shutdown; these four
  observations are not a campaign-duration or all-world transport guarantee.
- All four captures completed detector/OCR/feature integration. Chair, laboratory
  entrance and office entrance each yielded one scoreable emission. The doorway
  view abstained. This is retained without retry or threshold changes: neither
  preflight transport nor authorization requires a positive detection quota.
- All four lifecycles exited cleanly without forced kills. No domain-218 process
  remained at the final check. Source hashes were rechecked after capture.
- Full regression: **1,311 passed, 1 skipped**, zero failures/errors. The existing
  synthetic-depth RuntimeWarning remains. Thirteen new driver/binding tests cover
  primed TF reuse, fresh process commands, closed deadlines, transport validation,
  changed bytes, bad lifecycle/scope, missing synchronization and invalid timing.
- All 32 component-handoff and 51 four-class-readiness source pins still match.
  Frozen v8 remains `6b7bc9e5dd4f5289af88ee4524db3544d277eeeb6a0685177b12c128ef6fb49a`.
  No R1/R2 source edits, validation-label access, protected worlds or human labels.

Authoritative evidence:

- `reports/joint_score_wave_s_assets_20260924_v3/driver_config.json`
- `reports/joint_score_wave_s_assets_20260924_v3/static_clearance_audit.json`
- `reports/joint_score_wave_s_gazebo_preflight_20260924_v2/capture_audit.json`
- `reports/joint_score_wave_s_inference_preflight_20260924_v1/evidence.json`
- `reports/joint_score_wave_s_regression_20260924_v2.xml`
- `reports/joint_score_wave_s_execution_20260924_v1/execution_manifest.json`
- `reports/joint_score_wave_s_execution_20260924_v1/execution_approval.json`

## Investigation and preserved failures

The investigation workflow identified a confirmed transport defect in the first
live run: creating a new TF buffer only after localization discarded the history
needed to interpolate AMCL's future-dated transforms at the selected image time.
An isolated real tf2 buffer test reproduced the past-extrapolation failure and
showed that retaining the earlier history resolves it. The driver now uses a TF
listener started during localization and preserves its buffer at capture arming.
It does not change the selected frame, lookup timestamp, camera or two-second delay.

Later views in that first run encountered occupied-domain checks even though no
domain processes survived shutdown. Each view now runs in a fresh process/ROS
context, and the fresh four-view run passed without that failure. The initial
failed preflight, its source config and a byte-identical pre-fix driver copy are
retained under the v1 preflight and v2 assets. An earlier package-inventory sort
failure remains in partial assets v1; inventory now safely handles absent names.

## Authority and next execution boundary

The user's explicit prospective instruction is preserved verbatim in
`reports/joint_score_wave_s_authorization_20260924.json`.
`scripts/bind_wave_s_execution.py` checked the live evidence, static audit,
approved protocol/schedule and source pins before deriving a manifest-bound
receipt. Its canonical manifest SHA-256 is
`707e1828780277f991e62f506e4081cdbbfa67e4c7004459e4ef592aed617028`.
This is an agent-bound receipt of the user's existing authority, **not** a human
signature or a claim of subsequent human inspection of unseen assets/results.

The authorization covers only the fixed 400-attempt S schedule. S human review,
score learning and model freeze remain later gates. It does not authorize C/V,
validation-key release, protected-world evaluation, unseen labels or model
admission. Preflight observations must never enter S/C/V datasets or quotas.

Primary entry point (in the sourced ROS/R1/R3 environment with its PYTHONPATH
preserved):

```bash
python3 scripts/joint_score_wave_s_driver.py attempt \
  --config reports/joint_score_wave_s_assets_20260924_v3/driver_config.json \
  --execution-manifest reports/joint_score_wave_s_execution_20260924_v1/execution_manifest.json \
  --execution-approval reports/joint_score_wave_s_execution_20260924_v1/execution_approval.json \
  --output reports/joint_score_wave_s_primary_20260924_v1 \
  --attempt-id EXACT_NEXT_SCHEDULED_S_ID
```

Call in original schedule order, one process at a time; never replay a consumed
ID, switch output roots to evade no-retry accounting, or silently replace a failed
slot. The first action on any resume is source/authority/resource verification.
After all slots close, use inference `prepare`, `detector`, `ocr`, then `export`;
the detector and OCR subcommands require their respective pinned virtualenvs.
Do not fit until new, hash-bound Wave S human verdicts have passed admission.
