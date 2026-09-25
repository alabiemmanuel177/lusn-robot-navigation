# External simulator admission and resource stop

Status: DONE_WITH_CONCERNS for read-only detection; collection BLOCKED pending
external campaign idleness and explicit disposition of the new infrastructure stop.

Symptom: four map-6 attempts were stopped by the unchanged whole-host load limit
at load1=19.35400390625, above .8*24=19.2. Resource samples also reported CPU
pressure 6.02–7.29 and over 22 GiB available RAM. This is a safeguard stop, not
proof of memory exhaustion or GPU saturation.

Investigation found a concurrent SCRA campaign with cwd
`/home/eao/scra-robot-navigation`: run_campaign_worker.py PID 744945 and Gazebo
PID 791308 at inspection. Neither was modified or stopped. Their contribution to
the threshold crossing cannot be separated from R3 using the retained samples.
No claim of zero performance impact on the other campaign is supported.

Root cause of missed simulator detection: Gazebo rewrote argv[0] to the full
`gz sim -r -s ...` display title and blanked subsequent argv slots. The historical
scanner expected separate `gz` and `sim` tokens. A deterministic regression covers
both layouts, plus shell-text false positives. A new read-only scanner also
recognizes this campaign's parent between individual simulations.

Implementation: `scripts/inspect_simulator_workloads.py`; tests:
`tests/test_simulator_workload_inspection.py`. Fresh host verification detected
both actual external processes. Its first host check failed closed on unrelated
PID 1 cwd permissions; it now reads cwd only for simulator/campaign candidates,
while still failing closed if a candidate cannot be inspected.

The historical/resume capture executors and their pins were not modified by this
scanner preparation. Future resume must integrate and bind this check, wait for
external campaign idleness, retain all five failed assignments without replay,
and obtain the required failure disposition. Two workers are the conservative
proposal; no threshold increase or protected execution is proposed.
