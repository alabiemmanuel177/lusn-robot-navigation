# Expansion integration preflight: exact-frame provider evidence gap

Historical finding: the first preflight failed. The subsequently approved exact-frame
wrapper passed isolated development preflight v2; see the newest entry in STATUS.md.
This document retains the original diagnosis and proposal below for audit history.

## Evidence and scope

The P4-approved opt-in runner integration is pinned in
`reports/expansion_instrumentation_snapshot_20260912_v2/snapshot.json`.
It changes capture runner orchestration and the separately pinned sampling
candidate, not the historical provider, camera profiles, scenes or numeric floors.
The old source manifest and source archive are preserved. The old manifest is no
longer a valid admission pin for the changed active runner; the new pin is explicit.

One stationary development preflight ran under the exclusive R3 execution lock,
ROS domain 89, low CPU/I/O priority and resource guards:
`reports/physical_live_episodes/r3-expansion-instrumentation-dev01-preflight-v1`.
This is engineering evidence, outside the fixed primary expansion attempt budget.
No navigation instruction was dispatched. No protected world was accessed.

The collector armed at simulation time 10.584 s and retained synchronized RGB-D
at 10.602 s with a valid camera-to-map transform. It received 55 semantic messages
before closing, but none matched that exact frame. The provider's review-task log
begins at 10.902 s. The attempt was retained as `infrastructure_failure` with
`no_provider_frame_processing_evidence`, not as an incorrect label, target
nondetection, successful capture or replaceable calibration sample.

The provider logged an earlier startup transform extrapolation warning. That
warning alone does not establish why the particular retained frame had no output.
The independently verified structural problem is that its `_try_pair` chooses
`max(self.rgb)` and returns immediately while another frame is processing.
Endpoint discovery and a transform in the collector do not guarantee that the
provider processed the collector's earliest frame. A synthetic test invokes the
actual frozen provider method and demonstrates selection of timestamp 20 while
timestamp 10 remains buffered. This establishes a possible skip mechanism, not
a fabricated trace proving which internal branch skipped the live frame.

## Why no detection-chasing retry or relaxed gate

Selecting the first frame with a semantic output would restore the historical
detection-triggered bias. Waiting longer cannot prove completion of a frame the
provider never consumed. An empty semantic stream also cannot distinguish a true
empty detection result from processing/transport failure because the provider has
no per-frame completion acknowledgment. A later observation cannot be joined to
the retained frame merely because the robot was stationary.

No score, threshold, association radius, palette, FOV or scene change is proposed
to solve this instrumentation problem.

## Narrow proposed remedy, not yet implemented or approved

An R3-only orchestration wrapper can deliver the one retained, unmodified RGB-D
pair and its camera information on isolated provider input topics, then record
processing start/completion/failure for that exact stamp. It must call the frozen
provider computation unchanged, including on zero-emission frames. Completion
must be recorded only after processing returns successfully, and partial output
followed by an exception must remain infrastructure failure.

This changes the active invocation and processing instrumentation, even without
editing provider files. Explicit approval is requested instead of silently treating
the earlier source authorization as unlimited permission. It requires synthetic
zero-output, exception, duplicate delivery and wrong-stamp tests, a new immutable
source pin, and an isolated development preflight before any campaign decision.

## Investigation learning

For asynchronous RGB-D providers, discovered endpoints are readiness evidence,
not evidence that a particular frame was consumed. Match capture and processing
by exact stamp plus input integrity, and retain a completion acknowledgment even
when no semantic message is emitted. Keep image sampling independent of outputs.

The investigation skill was used to trace the failure and reproduce the queue
selection behavior before proposing a change. Its unrelated global setup,
telemetry, repository routing and synchronization actions were not performed;
they are outside this scoped research task and writable workspace.
