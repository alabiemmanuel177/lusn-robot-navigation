# Resource-guard process-exit race

Status: BLOCKED on scoped frozen-source approval; cause reproduced, candidate
tested in memory, no patch applied to the runtime.

Symptom: fixed 80-view development feasibility collection stopped after batch 6.
Attempt `r3-recovery-feas-r003-laboratory_entrance-v0` exited 1 with
`ProcessLookupError: [Errno 3] No such process` and no expansion attempt record.
The retained failure is infrastructure, not nondetection or an incorrect label.

Root cause: `research2_execution_pids` in `src/language_nav/live_resources.py`
reads `/proc/<pid>/cmdline` after enumerating PIDs. A process can vanish between
enumeration, open and read. The guard catches FileNotFoundError but not
ProcessLookupError. The traceback identifies this read inside the capture loop's
resource check; no GPU saturation or live scientific outcome caused this stop.

Candidate fix: catch `(FileNotFoundError, ProcessLookupError)` at that specific
read. PermissionError still fails closed; active Research 2 driver detection
remains unchanged. This does not permit running alongside protected jobs.

Evidence: `scripts/probe_resource_guard_race.py` deterministically reproduces the
original exception and tests the candidate in memory without editing the frozen
source. `tests/test_resource_guard_race_proposal.py` is the regression probe.
Ten focused tests passed. The first probe harness needed a local Path adapter;
that harness error was corrected before validating the race hypothesis.

Proposal hashes and results: `reports/resource_guard_race_proposal_20260922.json`.
The existing snapshot generator rejects changes outside the historical authorized
capture-runner scope. Applying this guard fix therefore needs a bound new source
approval and a new snapshot, not silent rewriting of historical pins.

Disposition: preserve all 24 attempted assignments, including the failed one;
seek authorization to apply/repin the minimal guard fix and resume the 56 untouched
assignments. No automatic replacement or repeated failed observation. Completion
of calibration, validation and campaign gates is not granted by this repair.
