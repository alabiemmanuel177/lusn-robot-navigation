# Authorized physical held-out runtime and asset reference

Research 3 has executable, default-deny paths for protected derivative building,
single-episode live execution, and independent post-execution measurement audit.
Their implementation is not permission to use protected data. Only synthetic
fixtures have exercised the new protected paths during pre-review preparation;
no actual held-out build, live evaluation, human approval, or calibration fit is
claimed by those tests.

## Separate authorities

| Operation | Authorization schema | Required authorization scope |
| --- | --- | --- |
| Build derivatives and a schedule template | `research3-protected-asset-build-authorization/v1` | `heldout_derivative_build_only` |
| Execute one approved episode | `research3-physical-heldout-runtime-authorization/v1` | `physical_heldout_live_execution` |
| Recompute retained measurements | `research3-physical-heldout-authorization/v1` | `physical_heldout_measurement_audit` |

Each envelope requires `status: approved_frozen`, `reviewer_type: human`, a named
`approved_by`, and `approved_at_utc`. These fields record an external attestation;
they do not authenticate a person's identity. No tool in this path creates a
genuine human approval. Build approval does not authorize a live run, and runtime
approval does not replace separate audit approval.

The entry points read explicit authorization metadata before protected schedules
or assets. Their frozen design must pass
[`check_physical_design_readiness.py`](../scripts/check_physical_design_readiness.py).
Scientific choices, nuisance estimates and confirmatory seeds must actually be
supplied; synthetic test values are not approved experiment settings.

## Build metadata and outputs

[`build_authorized_heldout_assets.py`](../scripts/build_authorized_heldout_assets.py)
accepts only `--authorization` and `--authorization-sha256`, both required, plus
standard `--help`. It does not launch ROS or Gazebo.

Its approval also requires:

- `recipe: readable_and_exact_chair_absence/v1`;
- `source_sha256`, with exactly the paths in `SOURCES` in
  [`physical_asset_authorization.py`](../src/language_nav/physical_asset_authorization.py);
- `shortest_path_source_sha256`, pinning the unchanged Research 1 geometry-verifier
  dependency `rcn/shortest_path.py`;
- `design` and `plan`, each a `{path, sha256}` reference;
- optional `calibration`, also a pinned reference. When supplied it must be
  `landmark-calibration/v1` from development or validation, never protected labels.

The plan uses `research3-protected-asset-build-plan/v1`. Its `output_directory`
must be a new contained directory below this repository's `data/` directory.
Each explicit `worlds` row supplies:

- a unique `base_instruction_id` from `base-r015` through `base-r020`;
- `source_directory` ending in that same stable ID;
- exact `source_sha256` pins for all nine names in the helper's `FILES` constant;
- a pinned `instructions` reference;
- positive finite `timeout_s` and `camera_color_tolerance`, plus
  `camera_horizontal_fov` in the accepted range `[0.5, 2.0]` radians.

The instructions document contains the authored `canonical` instruction with
partition `held_out`, plus all eight existing `deployed_variants`. Every deployed
variant contains exactly `variant_id`, `base_instruction_id`, `raw_text`, and
`provenance`. Evaluator answers do not enter that deployable record.

The builder reuses the existing transforms. `readable/` adds visual-only LAB and
OFFICE lettering without changing original collisions, map bytes, task or entity
IDs. `absence_base/` retains the independently verified removal of exactly six
chair components and their occupancy/perception representation.
`missing_landmark/` adds the same readable signage to that absent-chair world;
its updated hashes are bound to both the removal proof and visual-only audit.
Original input files are not overwritten.

The output contains create-once build request/result records and
`runtime_schedule_template.json`. Interrupted builds retain partial output and a
failure record; the tool does not overwrite or automatically retry them.

The template uses `research3-physical-heldout-schedule/v1` and lists every approved
map × seed × eight variants × five systems (`B1`, `B2`, `B4`, `B5`, `B6`). Each
world/condition/seed has a distinct paired-block index shared across its five
systems. This is a listing, not a frozen counterbalanced execution order. It has
`status: pending_separate_runtime_authorization` and
`live_execution_authorized: false`. If no genuine calibration was supplied,
`calibration_sha256` is null and runtime admission remains blocked.

## Runtime admission and command surface

[`run_authorized_heldout_episode.py`](../scripts/run_authorized_heldout_episode.py)
requires `--authorization`, `--authorization-sha256`, and `--episode-id`.
`--prepare-only` validates the approved episode and prints its request without
importing ROS or launching anything. It still accesses authorized protected
deployable inputs; it is not an authorization bypass.

The runtime approval supplies pinned `design`, `calibration`, and `schedule`
references, `execution_source_sha256`, `provider_source_sha256`, and an explicit
integer `ros_domain_id` from 1 through 101. All gates in `GATES` in
[`physical_heldout_authorization.py`](../src/language_nav/physical_heldout_authorization.py)
must be true: non-protected detector validation, calibration freeze, scientific
protocol freeze, held-out launch approval, non-protected runtime regression, and
the requirement that Research 2 be idle.

The unique scheduled episode fixes its run ID, map, deployed instruction, system,
approved simulator seed, timeout, camera settings and exact world assets. Run IDs
must match `[A-Za-z0-9][A-Za-z0-9_-]{0,95}`. The runner offers no caller overrides
for those choices, no coexistence override, and no protected capture, palette
adaptation or human-review mode. Missing-landmark conditions require a validated
physical absence intervention; an unchanged chair world is rejected.

Authored partitions are preserved, not relabeled:

| Artifact or interface | Partition |
| --- | --- |
| World manifest and execution catalogue | `held_out` |
| Landmark scene and provider/ROS interface | `test` |
| Request and summary | `partition: held_out`, `catalog_partition: held_out`, `runtime_partition: test` |

The normal engineering CLI still rejects held-out execution. The separate
`heldout_adapters.launch.py` and provider enforce authorization again. All three
catalogue-consuming ROS nodes receive the authorization path, hash and episode
ID. The provider uses a Research 3-owned initializer and unchanged Research 1
detector callbacks, with explicit protected scene loading after admission.

## Source identity, isolation and evidence limits

`SOURCE_FILES` is the required Research 3 execution source inventory, including
the parser, belief update, planner, adapters, monitor bridge and authorized entry
points. `PROVIDER_FILES` is the exact Research 1 code/configuration inventory,
including detector callbacks, projection, controller, logger, measurement helpers
and named runtime YAML files. Despite its historical field name,
`provider_source_sha256` includes both code and configuration byte hashes.
These are bounded direct-dependency pins, not a claim of complete external model,
ROS binary, package, or environment closure.

The wrapper requires Research 2 idleness and resource headroom, uses nice level
15 and thread limits of 2, and holds the shared Research 3 execution lock.
Checks reject other owned runners or exact Research 3 launch signatures; they
never kill Research 2 processes. Authorized nodes require the actual ROS domain
and per-run `RCN_WORKER_ID`, `GZ_PARTITION`, and `IGN_PARTITION` to match. Output
paths are confined to `reports/physical_live_episodes/<run_id>/research2` and
`research3`; existing run directories and symlinks are rejected.

Before evaluator assets are opened, the live runner writes immutable
`measurements.pre_evaluation.json`. Evaluation requires an independently admitted
context bound to that file's hash, run ID, map, asset hashes and exact supplied
trajectory. Raw request flags alone cannot authorize evaluation. Final
`measurements.json` includes recomputed annotations, and the summary binds both
measurement hashes. See [the audit reference](PHYSICAL_HELDOUT_AUDIT.md).

Historical captures and source freezes remain immutable. New source pins are not
retroactively substituted into old evidence. Fresh non-protected capture under
the settled source is planned to address historical source-inventory gaps;
documentation and synthetic tests do not claim that recapture, detector coverage,
human labeling or recalibration is complete.

See [the authorized workflow](howto-authorized-physical-heldout.md) for commands.
