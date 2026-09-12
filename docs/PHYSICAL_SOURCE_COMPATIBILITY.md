# Historical review evidence and changed runtime sources

An unchanged RGB frame, reported claim/pixel and genuine human verdict remain
historical evidence. They do not automatically qualify a different runtime for
deployment. Preserve every original request, label journal, image, task, QA and
source hash. Never relabel or rewrite historical hashes to manufacture compatibility.

`scripts/compare_physical_sources.py` prepares a read-only comparison. It always
returns `blocked_for_equivalence_approval`, `deployment_eligible: false`, and
`equivalence_approved: false`, even when every compared byte matches. It does not
change campaign or calibration source gates, fit calibration, create human labels,
perform differential tests or open protected data.

## Explicit inputs

Run with `--archive BASELINE.tar.gz --request comparison-request.json --output NEW.json`.
`--root` defaults to the Research 3 workspace. Exit 2 means the expected blocked
readiness report; malformed/stale inputs are errors. Output creation is exclusive.

The request uses `schema_version: research3-source-comparison-request/v1` and:

- `archive_sha256`: externally verified archive hash; changing the archive and
  supplying its new hash is not authentication of that archive's origin.
- `baseline_environment_member` and `current_environment_path`: explicit
  `reports/engineering_environment_*.json` files. A freshly captured current
  environment report is required for meaningful current dependency provenance.
- `runs`: explicit entries with `request_member`, `scene_member`, `profile_member`.
  The request is `reports/physical_live_episodes/RUN/request.json`; the scene is
  that run's `runtime_scene.yaml`; the profile is the corresponding frozen
  `reports/engineering_camera_settings_vN/profiles/base-r001..014.yaml`.
  Original development views may instead reference the exact archived
  `reports/stationary_capture_plan_v1/profiles/base-r001..014.yaml`; select by
  the request's recorded hash, never by assuming engineering-freeze profiles
  have identical bytes.
  Development-10 stress captures use the separately allowlisted exact file
  `configs/physical_dev10_camera_profile_v1.yaml`; its distinct hash and scope
  remain separate from ordinary-camera evidence.

The comparison reads only five fixed source members, the archive manifest and
explicit requested evidence members. It never extracts an archive directory.
Selected members must be regular, unique, bounded-size and manifest-hash-pinned.
The archive must declare a nonprotected engineering bundle. Each selected request
must establish development/validation map membership before its scene/profile is
read. Scene/profile hashes must agree with that request. Current historical paths
cannot be remapped to different evidence. Sources and archive are rehashed at end
to detect concurrent changes.

## What is compared

The four originally request-pinned files expected to change are
`run_physical_episode.py`, `physical_catalog.py`, `nav2_adapter.py`, and planner
`node.py`. The fifth is runtime `semantic_routes.py`: its archived source is useful,
but archive presence does not establish that the capture request pinned it or that
those exact bytes executed. Each run reports this distinction explicitly.

The tool reports baseline/current source hashes; original request source bindings;
base capture FOV and colour tolerance; unchanged or changed retained runtime scene
and camera profile bytes; recorded Python/ROS dependency metadata and provider
source/install hashes. Environment metadata equality is not a fresh live probe or
proof of historical execution. Raw RGB/QA/human judgments are not reaudited here;
`selected_bindings_unchanged_full_media_review_not_reaudited` is deliberately narrow.

## Required next evidence, not automatic transfer

After the new implementation settles, pin a new snapshot and current environment
report. Compare old/new nonprotected behavior with differential tests: catalogue
outputs, empty authorization defaults, ROS parameters, observation handling,
candidate generation, and fixed-input perception outputs. Check that held-out
branches are unreachable without scoped authorization. Numerical tolerances and
acceptable differences must be explicit; no post-hoc threshold relaxation.

A future externally approved equivalence artifact should pin both source trees,
this comparison, differential test inputs/results, unchanged provider/camera/scene
dependencies, changed-path scope and known provenance gaps. A separate deployment
eligibility decision may reference that artifact and original calibration approval.
The current bridge and campaign remain exact-source-only; this document does not
authorize adding a bypass. A typed reviewer name cannot authenticate identity.

If equivalence is not established, preserve existing labels as historical evidence
and collect targeted new-runtime validation. Repeating every human review is not
automatically necessary. Even approved source equivalence does not establish
unseen-world calibration transfer, recall, natural error prevalence, or sufficient
coverage of the present 60-target packet. Deliberate colour stress retains its
separate interpretation and needs an approved role in the calibration protocol.

## Catalogue differential command

`scripts/check_nonprotected_catalog_differential.py --archive BASELINE.tar.gz
--archive-sha256 VERIFIED_HASH --output NEW_REPORT.json` loads only the verified,
manifest-pinned archived `physical_catalog.py` into a distinct in-memory module.
It compares catalogue, launch-input validation and absent-anchor outputs against
current source across exactly 14 original, 14 readable and 14 absence worlds.
Every input asset must still match the archived manifest. Three synthetic cases
verify both versions refuse protected identities by default before reading assets.
No real protected catalogue is opened; no archive is broadly extracted.

This is a narrowly scoped differential test: both modules use current shared
Python dependencies. It does not compare ROS callbacks, navigation trajectories
or provider detections, and cannot establish source equivalence by itself. Report
fields for deployment eligibility and equivalence approval remain false.

Actual 11 September checks are retained in
`reports/physical_nonprotected_differential_20260911_v1.json`: 42/42 outputs
match, and all three synthetic unauthorized identities are refused by both versions.
The separate `physical_nonprotected_source_supplement_20260911_v1.json` reports
22 unchanged nonconstructor method bodies across Nav2, planner and semantic-route
nodes, with three changed constructors and no added/removed methods. The ordinary
launch file is byte-identical. Current provider core/node source hashes match the
archived v2 environment report. These are not callback executions or detection
replays: changed initialization state can change unchanged callback behavior.
`--supplement-only` regenerates this narrowly scoped comparison to a new file.

The all-46-run comparison request is
`reports/physical_source_comparison_request_20260911_v1.json`; the final comparison
is `reports/physical_source_comparison_20260911_v2.json`, using verified current
environment v4. The earlier v1 comparison remains unchanged. All selected request,
runtime-scene and exact profile bytes match the archive. Recorded dependency and
provider source/build hashes match between environments. The profiles are 30
stationary-plan, 12 engineering-v2 and four development-10 stress inputs.

Historical reconstruction is incomplete: 29 requests recorded a different
`run_physical_episode.py` hash from the archived snapshot, and 13 recorded a
different `nav2_adapter.py` hash. All 46 omit a `semantic_routes.py` request pin.
These are explicit blockers to claiming the archive reconstructs every capture's
runtime; the archive was a later current-source snapshot. Preserved evidence
bindings are not invalidated, but the 42-world baseline/current differential
does not by itself establish equivalence for those earlier source variants.
