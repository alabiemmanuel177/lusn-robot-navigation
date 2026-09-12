# Stage 1–4 offline continuation, 2026-09-10

## Root cause and bounded fix

Post-inspection Nav2 completion could wait indefinitely for an anchor observation;
the outer episode timeout was the only eventual exit. Actual adapter methods are
tested without ROS: successful inspection starts a pending deadline; lack of fresh
anchor evidence for eight simulated seconds emits a single abstention. Resumption
or completed instructions clear the pending deadline. Live physical inspection
remains unverified, including inspection viewpoints and independent point-goal error.

Separately, an audit of every retained pilot found no exact observation-to-frame
matches: diagnostic capture happened before detections. Never infer human labels
from those images. Observation-triggered capture now buffers exact timestamp RGB,
bounded synchronized depth, camera metadata, TF/errors and raw observations. The
runner's explicit capture-review option also enables provider pending pixel logs.
No review queue has been presented as ready; future frames require join validation
and individual visual QA. This does not establish recall or calibration coverage.

## Reproducible offline outputs

- reports/physical_detector_preparation_v1.json: three runs, not reviewable.
- reports/physical_comparison_draft_v1.json: 560 non-executable development/validation
  episodes; 240 held-out reservations without reading their catalogue contents.
- reports/stage1_physical_pilots_analysis_v1.json: all three engineering trials.
- reports/stage1_physical_pilots_bundle_v1.tar.gz: immutable pilot evidence and
  disclosed current-source snapshot, not an exact historical runtime reconstruction.
  SHA256 b2ce0277037f98bd23d2daed82b7980ff6512c55a4e0b591a7b83b006a417cbc.

## Resource boundary and remaining work

Verification: 191 offline tests passed in 0.77 seconds; sequential builds of
language_nav_runtime and language_nav_bringup both succeeded. These are not live
ROS integration or detector-performance results.

Host preflight detected Research 2 recovery/campaign/episode driver PIDs
496162, 498271, 518133, 520262. No Research 3 simulation launched. Offline tests and
sequential build use lowered priority; this is not a claim of zero shared CPU use.
The new guard detects known absolute-path drivers, not arbitrary renamed commands
or private namespaces; it cannot reserve the host against future launches.

Next live work needs a quiet window: inspection behavior, exact-frame capture,
detector coverage across development/validation, and localization/point-goal
diagnostics. Human correctness labels and a revised calibration freeze follow
usable audited capture. Stage 3 additionally needs genuine physical condition
interventions and a frozen seeded/sample-size protocol before comparative and
held-out execution. Stage 4 final analysis/release depends on those results.
