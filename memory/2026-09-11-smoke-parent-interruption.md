# Smoke executor interruption and safe resumption

This note records an orchestration incident, not a navigation or perception
result. Frozen runtime sources were not modified by the executor correction.

## Observations and limits

Root reported batch v1 and batch v2 tool sessions ending with status 143. The
origin of the external SIGTERM is unknown; no timeout mechanism, actor or system
component is established as the cause. Batch v1 retained completed truthful
original/paraphrase runs. Batch v2's topology runner survived its parent session
and eventually wrote a complete summary and independently auditable measurements.

Root then submitted a process inspection and batch v3 launch without first
reviewing the inspection result. On seeing the survivor, root immediately
interrupted batch v3. Its false-inserted-clause attempt retains `request.json`,
logs and `failure.json` with `error_type=KeyboardInterrupt`, `dispatched=false`.
There is no summary or measurements file for that original attempt. It is an
interrupted setup, not a measured navigation success/failure. Zero overlap between
Research 3 processes during this incident cannot be claimed, nor can unchanged
Research 2 performance be proved from available resource samples.

The topology original remains a completed measured failure: it crossed the first
right doorway rather than the intended second, its terminal identity was wrong,
and true point-goal error was 1.6341206764030198 m despite Nav2 reporting success.
It must not be rerun to replace that result.

## Established orchestration flaw

The original serial batch owned its child process group for cleanup while the
parent was alive, but did not maintain an execution lock inherited by the actual
runner. Killing only the parent could leave its child alive. A subsequent parent
could then start another run. This explanation concerns missing lifetime
coordination; it does not identify why the external parent SIGTERM occurred.

## Corrective scope and regression checks

Only `scripts/physical_engineering_smoke.py` and its tests changed:

- A nonblocking `flock` is inherited by the actual runner through `pass_fds`.
  Closing or killing the parent cannot release the child's shared lock.
- Exact `/proc` argument matching rejects existing owned Research 3 live runners
  before a new dispatch, without matching shell inspection text or touching R2.
- The default is one new case per invocation. All eleven original matrix entries
  remain represented; an optional explicit case filter bounds work further.
- An incomplete interrupted attempt requires a distinct explicit retry ID.
  Retry records identify their original case and supplemental status. Completed
  original outcomes cannot be replaced, and existing files are never overwritten.
- Cleanup is restricted to the newly created process group. Resource checks,
  runtime source/asset pins and risk/STOP thresholds remain unchanged.

Focused regressions passed (16 tests), including a benign child process that
continued holding a lock after its parent descriptor closed, actual launch
`pass_fds` wiring, exact-argv survivor detection, explicit retry naming and refusal
to replace completed outcomes. The full suite then passed 566 tests with one skip.
These tests launched no Gazebo process and produced no human labels.

## Attempt accounting

The false-inserted original ID is
`r3-eng-smoke-dev10-b6-false_inserted_clause-sim1-v1`.
Its authorized supplemental retry is the distinct ID ending `-retry-a`.
The final audit must list both; completion of the retry cannot turn the original
interrupted attempt into a completed original run. Batch skip records likewise
are not fresh runs or success evidence.

Evidence directories: `reports/physical_engineering_smoke_batch_v1`, `_v2`, `_v3`,
and the corresponding immutable run directories under
`reports/physical_live_episodes`. The final independent audit is written separately
after remaining baseline runs are available. No scientific campaign or statistical
performance claim follows from these single-layout engineering checks.
