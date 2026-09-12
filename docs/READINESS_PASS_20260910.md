# Readiness pass, 10 September 2026

Status: DONE_WITH_CONCERNS. The bounded readiness pass is complete. Stage 1 can
start without a new user decision. This is not full campaign clearance.

## Results

| Readiness check | Result |
| --- | --- |
| Research 1 reconciliation | Compatibility audit has zero blockers at `3821eee3392dbfb6f99452e11233835f03c63c0a`. Both local extension hashes are pinned and checked. |
| Route-keyed belief consumers | Source references traced through variants, belief updates and trace serialization. ROS publishes route candidates/costs, not an entity-keyed probability lookup. Four-alternative permutation tests pass. |
| Repeated evidence | Removed synthetic repeated absence/cross-clause updates. `step_index` alone no longer changes belief. Shared-anchor support changes clause reliability once per anchor, not once per route. |
| Unresolved inspection | The graph runner now abstains instead of executing a terminal route while its decision is still INSPECT. |
| Monitor faults | Seven checks passed over real, isolated ROS messaging. Malformed/replayed/future warnings stop motion; readiness cannot clear a fault; a newer valid prediction recovers; silence triggers the watchdog. |
| Measurements | New v3 summaries retain paired source timestamps, goal/tolerance, timeout and Nav2 outcome in checksummed v2 measurement evidence. The auditor recomputes navigation outcomes and sampling validity. |
| Build and tests | 86 core tests passed. Six ROS packages built. Seven package tests passed, zero errors/failures/skips. Python compilation and tracked diff whitespace checks passed. |
| Development smoke | Real Gazebo/Nav2 B1 run completed and its v3 summary passed independent audit. No held-out live runs were executed. |

## Development smoke evidence

Run: `reports/live_episodes/r3-readiness-dev00-v1/`.

- Existing development route `dev_00_r0`, truthful instruction, system B1.
- 243 timestamped poses, 2.8045014314 m measured distance.
- Final goal error 0.1979611951 m against 0.35 m tolerance.
- Maximum sampling gap 0.036 s; maximum pose step 0.0126374378 m.
- Seven Research 2 predictions; no recorded collision or timeout.
- Independent terminal identity matched. Full ordered-instruction completion is
  unknown because this legacy world has no supplied ordered geometry annotation.
- Summary SHA-256:
  `0e6ff52f7d74234a604bc4b0b6a5974e108064ae3c9d4e0cee4148876fede5bb`.
- Raw measurement SHA-256:
  `1db8fee6dcf7c029bb7279e3ed7a9b7e5f2447480c818b3d90a8147e304f16a1`.
- Analysis: `reports/readiness_live_audit_20260910_v1.json`.
- Fault checks: `reports/readiness_fault_smoke_20260910_v1.json`.

The Gazebo run used ROS domain 83 and a dedicated Gazebo partition/worker marker;
the synthetic fault test used domain 84. Other researchers' processes were not
stopped. The fault fixture is explicitly not research evidence.

## Root causes and changes

The provider loader was scanning every partition-prefixed manifest, including new
follow-up experiments (`dev_60000`) outside this study. It now defaults to this
benchmark's map IDs. Semantic catalogues request their exact map explicitly.
Selected map hashes are still verified, protected partition access remains gated,
and unmatched benchmark routes are still reported. No Research 1 artifacts were
edited in this pass. Its pre-existing two local bridge patches remain disclosed.

The previous B6 recovery fixture depended on repeated applications of one snapshot.
That was not new evidence. Correcting it removes the fixture's assumed completion
advantage; tests now verify abstention rather than manufactured recovery. Old graph
reports and archives are unchanged and must not be used to claim performance of
the corrected policy. New graph records include `engineering-readiness-20260910`
in their configuration and run identity; this is not the next experiment freeze.

The monitor bridge previously only logged invalid messages and let readiness replay
overwrite current risk. A stream guard now closes motion on faults and only accepts
strictly newer, fresh predictions for recovery. Readiness is consumed at most once.

The provider's position list omitted per-sample timestamps. A Research 3 subclass
now captures source timestamps for exactly its accepted positions, without editing
the provider. Sampling checks include episode endpoints, ordering, finite 2D
coordinates, gaps and pose jumps. Engineering limits are currently 1 s / 0.5 m;
these must be justified or revised on development data before protocol freeze.
Invalid sampling cannot yield navigation/semantic success. Historical v2 summaries
remain readable but lack these stronger navigation/timing guarantees.

## Concerns that belong to the four stages

- Stage 1 must connect the four-alternative physical catalogues, keep evaluator
  answers out of runtime, and implement genuine event-backed inspection updates.
  The current core is snapshot-based and idempotent; this pass does not claim
  persistent multi-view belief accumulation. Unresolved inspection safely stops.
- The smoke exercised the existing development pipeline. It does not establish
  new-world reachability, perception accuracy or B6 performance there.
- New-world detector coverage, calibration, sensor health/completeness rules and
  the amended experiment protocol remain development/validation work before the
  comparative campaign. Prior human labels are not automatically transferable.
- The ROS build reports an existing interface-package underlay override warning.
  The source `.msg` definitions match the provider's installed definitions, and
  real ROS messaging passed. Clean source/environment packaging remains stage 4.
- All earlier outputs are retained. No historical calibration, result file,
  protected graph campaign or archive was overwritten. No publication/commit/push
  was performed.

Durable lessons from the investigate workflow: scope provider discovery to consumed
assets; a loop counter is not an observation; an INSPECT action is not terminal-goal
authorization; invalid monitor data must actively revoke motion permission.
