# Updated non-protected engineering snapshot capability

`scripts/package_physical_engineering.py` prepares a deterministic, create-once
gzip/tar bundle and adjacent SHA-256 file. It is not a final study release.
No full bundle has been produced while implementation sources are changing.

## Explicit inventory

The standard inventory includes current Python source/scripts/tests, ROS source
and package metadata, selected schemas/configuration, physical-review/protocol
documentation, fourteen original non-protected audit-input worlds, fourteen
readable worlds, fourteen absent-chair worlds, and nine development base-r010
shape-stress derivatives: four v1, four v2, and chair-only v3. These are **51 world
directories**. Original worlds r015–r020 remain excluded. Each world uses exact named
asset files. It also includes the stationary capture plan and its fourteen
profiles, plus frozen engineering camera settings, fourteen corresponding profiles
and validation command manifest. Engineering settings are not confidence calibration.

No protected-world directory is enumerated. Code may implement protected-data
guards, but protected research data, old human labels and calibration labels are
not bundled. There is no broad reports sweep, logs sweep, external Research 1/2
checkout, model binary, environment credential, or ROS build environment copy.

Optional repeated `--run` arguments select exact non-protected run directories.
Map/split identity is checked before reading their evidence. The run allowlist is
request, capture/measurement/outcome summaries, pending provider task logs,
runtime scene, Nav2 parameters, and raw RGB/depth frames with their metadata,
capture request/summary and observation index. Both `perception_capture` and
observation-independent `context_capture` are supported. No arbitrary neighbouring
file, old reviewed worksheet, human progress journal or unknown log is included.
Provider task logs containing labels rather than pending observations are rejected.

```sh
python3 scripts/package_physical_engineering.py --dry-run
python3 scripts/package_physical_engineering.py \
  --run reports/physical_live_episodes/EXPLICIT_NONPROTECTED_RUN \
  --output /tmp/new_engineering_snapshot.tar.gz
```

`--max-bytes` bounds uncompressed payload size before each read (default 1 GiB).
Large raw captures are opt-in through the explicit run list; select fewer runs
instead of silently dropping frames. Missing required assets fail closed.
The bundle should be produced only after edits and selected capture writes settle.

## Integrity and reproducibility

Every member has its exact byte count and SHA-256 in `MANIFEST.json`. File names
are sorted; tar modes/ownership/timestamps and gzip header name/time are fixed.
Identical inputs therefore produce byte-identical archives even under different
output filenames. The archive is reopened to verify every member and reject
duplicates, unexpected members, unsafe paths and non-file entries. Symlink inputs
and source changes during collection are rejected. Existing bundle/checksum paths
are never overwritten.

The manifest explicitly reports `study_complete: false`,
`calibration_validated: false`, `calibration_frozen: false`, and incomplete historical
execution reproducibility. Selected run source hashes are compared with current
snapshot bytes; differences are disclosed, not relabelled as historical source.
Archive integrity verifies retained bytes, not scientific validity or runtime
reproducibility. Tests use tiny synthetic archives and explicit input inventories;
they do not create a full current-project package.

## Optional read-only environment provenance

`capture_engineering_environment.py --output reports/NEW_ENVIRONMENT_REPORT.json`
records the reporting Python version and NumPy/SciPy/PyYAML/pytest versions,
allowlisted ROS Jazzy package.xml versions/hashes, R1/R2/R3 Git revisions, and
selected Research 3/provider-bridge source/install hashes. Only named files and
read-only Git revision commands are used. No environment variables, package index
URLs, credentials, model/data trees, or protected research assets are inspected.
Missing installations and GPU state remain explicitly unknown; the report does
not infer active overlay selection, GPU allocation or full runtime reproducibility.

Pass `--environment-report reports/NEW_ENVIRONMENT_REPORT.json` to the packager to
include that exact report and its SHA-256 explicitly. The option is not a broad
environment directory sweep. Environment capture does not build a project archive.

Current packaging defaults select `engineering_camera_settings_v2` and the exact
`reports/engineering_environment_20260911_v2.json` report. Historical camera settings
v1 are excluded unless `--include-historical-settings-v1` is explicitly passed;
both versions are then named in the manifest. `--environment-report` can select
another explicit report without changing or overwriting either retained version.

## Optional unlabelled review packet

`--review-packet reports/EXPLICIT_PACKET_DIRECTORY` includes only
`packet_manifest.json`, `inventory.json`, `combined_visual_qa.jsonl`,
`sampling_policy.json`, and an optional manifest-pinned `extra_selection.json`.
The packet manifest's schema, non-protected/no-generated-label declarations and
every listed member checksum are verified. Inventory entries with protected map
IDs, partition mismatches or human labels are rejected. The bundle manifest retains
the packet manifest hash and exact member hashes. Human progress journals are
never swept into the package, even when adjacent to packet files.

Final selected stress captures can reference doorway/LAB/OFFICE v2 and chair v3,
while all retained world versions remain available to explain earlier attempts.
Actual capture inclusion still requires explicit `--run` arguments; adding a
packet never silently adds every run/report directory named inside it.
