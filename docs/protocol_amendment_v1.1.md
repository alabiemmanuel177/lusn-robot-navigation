# Protocol 1.1 amendment: completed-platform reconciliation

Date: 30 August 2026

This amendment was made before any Research 3 live Gazebo execution or protected
Research 3 outcome access.

## Map identifier reconciliation

Research 3 originally reserved one-based terminal identifiers `dev_06`, `val_03` and
`test_03`. The completed Research 1 platform contains six zero-based development maps,
three zero-based validation maps and three zero-based protected test maps. The Research
3 split is therefore reconciled as follows:

- `dev_06` becomes `dev_00`;
- `val_03` becomes `val_00`;
- `test_03` becomes `test_00`.

All remaining identifiers are unchanged. No map changes partition. Each instruction
now records a `platform_route_id` that resolves to a frozen, clean-S0-verified Research
1 route. The compatibility audit verifies every development and validation reference.
Protected route contents and outcomes remain outside the audit.

## Research 2 staging

Research 3 development may use the explicit `NoOpFailureMonitor`, whose reason code is
`monitor_unavailable`. Such runs cannot support claims about early failure prediction,
combined-system safety or recovery. Research 2 remains required for the combined B6
failure-monitor evaluation; it is not silently replaced by a constant zero score.

## Evidence classes

The deterministic graph-world campaigns are engineering evidence for parsing,
grounding, contradiction updates and guarded policy behavior. They are not Gazebo,
physical-robot, perception-calibration or confirmatory evidence. Calibration parameters
must not be frozen from graph-world confidence values because those values are authored
fixtures rather than samples from the deployed landmark detector.

The held-out campaign command now requires an explicit `--allow-protected` flag. That
flag is not authorized until the live landmark contract, calibration and Research 2
gates required by the final combined evaluation have passed.
