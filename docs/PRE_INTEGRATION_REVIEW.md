# Research 3 pre-integration review — 10 September 2026

Follow-up: the [completed readiness pass](READINESS_PASS_20260910.md) resolves the
provider discovery/pin, repeated-evidence, monitor and measurement issues below.
This document preserves the initial findings; use the follow-up for current status.

Decision: proceed with runtime integration work, not with the full campaign yet.
Research 1's completion does not validate Research 3 on its new geometry.
This is a source/artifact review with core regression tests, not a new live test.

## Improvements made

- Route belief now uses route IDs instead of anchor entity IDs. Four alternatives
  sharing one chair previously collapsed into one dictionary entry. Physical
  anchor identities are unchanged. Probability dictionary consumers must now treat
  keys as route hypotheses, not landmark identities.
- B6's equal-risk commit tie prefers the clause-supported route, then a stable
  route ID. Lower risk retains priority; hard safety guards are unchanged.
- Duplicate route IDs are rejected; empty belief inputs abstain.
- Ordered scoring preserves known collision/timeout/wrong-terminal/forbidden-gate
  failures when terminal evidence is unknown. Duplicate required gates are rejected.
- Measured-live auditing rejects semantic completion claims without ordered geometry.

Verification: `PYTHONPATH=src python3 -m pytest` passes 82 tests, including all
24 permutations of four shared-anchor alternatives for B4/B5/B6. Prior result
files and archives were not changed or regenerated. They describe the prior code,
not the corrected policy. No held-out episodes were run for this review.

## Findings that must be handled during integration

1. **Provider compatibility is not currently green.** The current Research 1 HEAD
   is `3821eee3392dbfb6f99452e11233835f03c63c0a`; Research 3 still pins
   `697a7bc86fd2eca62866c614ef7b26b5d810cf84`. The compatibility command reports
   a `dev_60000` map-hash mismatch, which prevents the partition catalogue from
   loading and produces downstream unavailable-route/bridge messages. Those
   messages do not prove the old individual routes were deleted. Reconcile the
   exact consumed assets and catalogue discovery before recording a new verified
   pin. Do not modify completed Research 1 results or bypass hash verification.
2. **Live evidence must be event-backed.** B6 currently repeats authored absence
   and cross-clause updates; `step_index` is not proof of independent viewpoints.
   Runtime integration needs observation identity, deduplication and persistent
   belief state. Do not present these authored updates as measured new evidence.
3. **Monitoring needs fault-injection checks.** The bridge can retain its previous
   state after malformed warnings; readiness replay also needs validation against
   real predictor messages. The planner stale-input watchdog alone does not prove
   immediate malformed-input rejection.
4. **Measurement needs a stronger campaign contract.** Retain timestamped poses,
   sampling-gap checks, commanded goal, terminal outcome and sensor-contact evidence.
   Independently recompute goal error/navigation success, not just trajectory length
   and ordered gates. Define missing-evidence and infrastructure-failure treatment
   before the campaign. Keep failed and interrupted attempts.
5. **World/perception coverage remains unvalidated live.** Twenty physical worlds
   and eighty statically checked paths are preparation, not eighty live successes.
   The reference pilots distinguish doorway choices but include point-accuracy
   failures and interruptions. New visual geometry needs development/validation
   detector measurements; old human review remains valid only for its original
   coverage. Request additional human labels only after checking review usability.
6. **Protocol and release need a new freeze.** The old 560-case plan targets the
   old provider route IDs. Freeze the new map/split matrix, systems, seeds, scoring,
   exclusions, policy changes, calibration and exact source/asset hashes before
   held-out live execution. Disclose prior held-out graph access and the shared
   procedural world family; do not claim unseen-building generalization.

The previously observed unscoped Research 1 mechanism pilot is no longer running.
A Research 2 campaign remains active. Use scoped cleanup and isolated ROS/Gazebo
identities; disappearance of one process does not establish interference-free runs.

## Next-stage gates

1. Connect only the deployable four-route execution catalogues and perception
   outputs to runtime; keep expected answers and ordered geometry evaluator-only.
   Resolve provider compatibility, genuine observation updates and monitor faults.
2. Demonstrate correct and wrong-route controls in development, then measure
   detector coverage and calibrate using non-protected human-reviewed evidence.
3. Freeze the revised protocol and provenance; execute the paired comparative
   campaign, including held-out live evaluation, without outcome-driven reruns.
4. Audit and analyze retained evidence, report uncertainty and limitations, and
   package an independently reproducible release.

No new user decision is required to start these engineering steps. Campaign
readiness is not yet established, and final completion is not claimed.
