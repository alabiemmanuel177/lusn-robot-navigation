# Late inspection preemption, 11 September 2026

Status: DONE_WITH_CONCERNS. Production callbacks are tested offline; physical
inspection and viewpoint quality still require a development run.

## Root cause and bounded correction

The earlier investigation skill traced two sequential integration problems.
Identified anchor observations were suppressed by zero regional search coverage;
the separate evidence fix makes direct blue-versus-green attribute conflict
eligible for INSPECT without inventing regional absence evidence. Then the Nav2
adapter ignored INSPECT whenever the instruction already had an active goal.
Retained non-protected dev10-v3 evidence has initial COMMIT at 13.203 simulated
seconds and first anchor-bearing candidate snapshot at 13.527 seconds. This
supports a genuine late-decision scenario, not a forced planner action.

The adapter now tracks each active action and queues one guarded INSPECT during
an active COMMIT. It requests cancellation, including when the request arrives
before the original goal is accepted. It dispatches no second goal until the old
action reports STATUS_CANCELED. Then it resubmits through ordinary route,
guard, server, inspection-budget and waypoint validation. Failed revalidation
ends in abstention; unconfirmed cancellation never starts inspection.

STOP removes the pending inspection and takes precedence, including when its
reason is empty or a success/cancel race occurs. Duplicate inspection messages
cannot create concurrent goals or repeated preemption requests. No changes were
made to waypoint selection, provider assets, evaluator answers or Research 2.

## Verification and limits

Production on_decision, goal-acceptance and goal-result methods are executed in
offline callback fixtures, not reimplemented mock policy. Eleven focused tests
(including the existing deadline tests) pass. Cases cover cancellation-before-
acceptance, confirmed-cancel-only dispatch, STOP precedence, rejection of missing
eligibility at resubmission and no preemption of a non-COMMIT action.
The full Python suite passes: 322 tests in 1.32 seconds.

This is not a live Nav2 acceptance result. The intended genuine live scenario is
`base-r010-attribute_corruption-s0` in the chair-present development world using
the existing camera profile: instruction requests green, detector observes blue.
Current path-midpoint inspection may face away from the chair; the existing
fresh-observation timeout remains active. That limitation was not optimized away
to obtain a passing example. Research 2 coexistence still requires the existing
resource guards and bounded development authorization.

Durable learning: validating a policy INSPECT decision is insufficient when the
executor has already committed. Test sensor-arrival timing against action
lifecycle transitions, and require acknowledged cancellation before replanning.

## Follow-up: cache invalidation and retained live outcome

A failing-before/passing-after callback regression exposed stale execution
authority: publishing a negative path assessment retained prior planned distance
and inspection pose. The central eligibility publication method now removes both
entries before publishing any unavailable/rejected/failed planner assessment.
This covers all negative paths, not only a returned planner failure. Other routes
are preserved. Ten preemption/cache callback tests pass.

Read-only audit of `r3-readable-inspect-dev10-20260911-v1` confirms real dispatch:
COMMIT at 11.808 s, INSPECT requested at 11.919 s, canceled COMMIT acknowledged at
11.931 s, then INSPECT dispatched at 11.931 s toward (4.6824, -0.1673).
The trace has no `inspection_completed` event. A monitor-driven STOP ended the
episode at 17.589 s because no route met the unchanged hard-risk constraint.
No collision, timeout or infrastructure failure was reported; navigation and
ordered completion are false, terminal identity unknown. Measured travel is
1.8688 m over 169 ground-truth samples.

INSPECT decisions contain 37 distinct anchor observation IDs, timestamps
11.4–15.0 s. This establishes newer anchor evidence during motion, not successful
post-inspection evidence: the waypoint was never completed and the post-completion
fresh-anchor gate therefore was not exercised. Repeated decisions are not
independent viewpoints. No thresholds, retained results or planner actions were
changed to turn this protected safety stop into a success.
