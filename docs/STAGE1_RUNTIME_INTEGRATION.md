# Stage 1 runtime integration

Started 10 September 2026. Status: in progress, not live-new-world validated.

Live update: three new-world development attempts now ran and were audited.
Two selected and crossed the correct second-right doorway; one of those passed
the independent 0.35 m point-goal criterion and the other missed it at 0.390 m.
The first attempt failed and remains retained. A map-scoped camera palette enabled
live anchor/terminal observations in the third attempt; detector accuracy and
calibration transfer are still unvalidated. See the
[live debug report](../memory/2026-09-10-stage1-navigation.md). Current core tests: 161 passed.
Physical inspection validation remains open. Earlier sections describe batch milestones.

## Parallel-development batch

The user authorized parallel agents. Three bounded work areas were assigned:
the new-world runner, observation/inspection provenance, and independent contract
tests. Root integrated the changes and owned shared adapters/launch files. No
agents launched simulations or edited Research 1/2. ROS builds used at most two
parallel package workers; Gazebo work remained serialized and was not launched.

Implemented in this batch:

- `scripts/run_physical_episode.py` provides offline `--prepare-only` validation
  and a development/validation live runner. All 14 non-protected runner preflights
  pass. It checks isolated transport, detects an occupied ROS domain, retains
  create-once evidence and source/asset hashes, and separates post-execution
  evaluator geometry from runtime inputs. Live execution remains untested.
- The runner verifies map metadata and scene/catalogue identity and associations.
  A held-out map cannot be admitted merely by relabelling its partition.
- Observation IDs, source timestamps, sequences and sources survive the route
  join. The planner keeps an atomic per-instruction identity ledger and rejects
  mutated/replayed/regressing/future observation or graph updates.
- Post-inspection motion requires a fresh anchor observation acquired after
  inspection completion. A fresh decision or terminal-only refresh is insufficient.
- Physical-world planning waits for all four proposals and all four Nav2
  assessments before selecting a route. An ineligible assessment counts as an
  assessment, not an eligible path.
- Confirmed adapter execution identity, rather than the latest speculative
  decision, determines the measured navigation endpoint. Missing confirmation
  leaves goal accuracy unknown and cannot support navigation success.
- The Research 2 Python executable now follows the launch-time root override.

The integrated lightweight ROS fault fixture passed all seven checks in domain 86;
report: `reports/readiness_fault_smoke_parallel_v1.json`. This started no simulator
and no Research 2 inference process. Changed ROS packages built and package tests
passed. The batch is engineering verification, not new-world detector evidence.
Final batch verification: 157 core tests passed, including 19 runner tests and 34
independent integration checks. All 14 offline runner preflights pass. Python
compilation and tracked whitespace checks pass; package aggregate remains seven
tests with zero errors/failures/skips.

Belief processing remains snapshot-based with persistent identity bookkeeping,
not calibrated temporal evidence accumulation. Chronologically newer frames do
not establish independent viewpoints. Stale entities remain timestamped semantic
memory, while post-inspection execution requires freshness. Source/clock resets
require a fresh episode. Observation coverage remains zero for physical proposals
until a measured coverage model is supplied; no absence evidence is fabricated.

## Implemented and checked

- `physical_catalog.py` loads only deployable execution catalogues, map pixels and
  SDF world bytes. It does not read evaluator manifests, expected route IDs,
  ordered geometry or ground-truth semantic categories.
- Hash validation, four distinct side/ordinal alternatives, finite goal poses,
  stable route/terminal identities, strict field allowlists and protected partition
  rejection are enforced.
- Semantic route publishing and Nav2 goal lookup accept a `physical_catalog`
  parameter. Existing provider catalogue behavior remains available.
- Each base instruction publishes all four alternatives, sharing the chair region.
  Terminal categories must come from perception. Observation coverage defaults to
  zero rather than claiming a new-world detection/viewpoint measurement.
- The planner's route subscription retains ten proposals rather than two, so four
  alternatives fit in its queue.
- The combined live launch exposes `physical_catalog`; its legacy
  `semantic_catalog` argument is now optional.
- All 14 development/validation catalogues load: 56 alternative routes. Held-out
  catalogues were not loaded for development testing.
- 94 core tests pass. The three changed ROS packages build and test successfully;
  aggregate package result: seven tests, zero failures/errors/skips.

An isolated ROS-domain-85 transport check instantiated the actual semantic provider
and Nav2 adapter, published the base-r010 hypotheses and received all four route
IDs matching the adapter's goal dictionary. It started neither Gazebo nor Nav2 nor
a Research 2 monitor. This is contract verification, not navigation evidence.
The first fixture attempt failed: it republished the instruction on every executor
iteration and received only two unique proposals. A corrected fixture published
once after discovery and received all four. This establishes single-instruction
delivery, not sustained-load/message-flood resilience.

## Concurrent Research 2 work

Host inspection found the existing Research 2 campaign process PID 3976122 running
one worker with `--systems s3`. Available RAM was approximately 25 GiB and load
average approximately 2.8. Those readings support lightweight development work;
they do not establish that simultaneous simulator/GPU loads cannot perturb either
experiment's timing. Builds were sequential. No Research 2 processes, files or
settings were changed and no second Gazebo experiment was launched in this turn.

Use distinct ROS domains, Gazebo partitions and scoped worker cleanup for future
simulation, then check host CPU/GPU demand again. Prefer a quiet simulator window
for timing-sensitive measurements. Research 2 activity does not block coding,
unit tests or isolated lightweight ROS contract tests.

## Remaining stage 1 work

1. Exercise the new runner end-to-end in a controlled new-world development
   episode when resource isolation is suitable. Verify the camera/landmark
   producer's real observations, four-way planning and independent measurements.
2. Exercise real inspection completion and observation freshness, including lost
   detections and monitor-triggered stops. Identity bookkeeping tests do not
   establish a physical viewpoint change or calibrated temporal inference.
3. Review retained live evidence and repair integration issues before handing
   detector-performance measurement to stage 2. The legacy runner remains intact.

Detector-performance validation and calibration transfer are stage 2. No new-world
perception accuracy, ordered-instruction success or campaign readiness is claimed.
