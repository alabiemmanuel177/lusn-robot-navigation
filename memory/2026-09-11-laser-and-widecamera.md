# Laser/camera debug report — 11 September 2026

Status: DONE_WITH_CONCERNS. Wider-camera prototype verified; localization drift
mechanism remains under investigation. No scoring thresholds or AMCL settings changed.

## Symptom and hypothesis

Prior AMCL/ground-truth drift grew along the corridor and sometimes produced a
false Nav2 point-goal success. A large sensor-frame or physical-geometry mismatch
was a testable candidate. Bounded laser telemetry now retains at most 100 scans,
at least 0.5 seconds apart, with a ground-truth pose timestamp within 100 ms.
This is evaluator-only data and is never supplied to the planner.

`r3-scan-dev10-20260911-v1` retained 42 scans. The offline audit ray-casts through
the SDF visual boxes at laser height, using the provider's planar sensor offset.
Across individual scans, 94.7–100% of finite rays agree within 10 cm; the median
of per-scan median residuals is 0.00862 m. This weakens a large fixed sensor/world
frame-error hypothesis. It does not rule out occupancy-map versus scan-plane
differences, self-occlusion, filtering issues, motion effects or stochastic variation.
Max paired localization error was 0.345 m (previous run 0.580 m); final point error
0.24975 m. No navigation fix is claimed from this passing repeat.

External diagnostic cross-check used official Nav2 documentation/source, including
https://api.nav2.org/nav2-jazzy/html/amcl__node_8cpp_source.html and
https://docs.nav2.org/rolling/configuration_and_development/configuration_guide/others/configuring_amcl/.
Rolling documentation is not proof that this installed Jazzy build supports a
given parameter; no suggested parameter was blindly added.

## Camera cause and tested change

The original narrow field of view crops identity-defining chair features. An
explicit optional development-only 1.57-radian horizontal FOV modifies both RGB
and depth cameras in the R3-owned launch's temporary robot SDF. Provider files,
world geometry, camera pose and default configuration remain unchanged. Bounds
and exactly two matched camera fields are enforced, with regression tests.
Actual camera metadata continues to accompany images; no old calibration transfer.

`r3-widecamera-dev10-20260911-v1` yields five exact detector/media matches. All
five full frames were individually viewed: frames 000 and 001 show a recognizable
chair back/seat/legs with detector pixels on the seat; 002 remains cropped and
003/004 lack full doorway context. No human verdicts or full handoff approval were
generated. Entrance plaques still do not visually identify office/laboratory type.
Final point error 0.15957 m; ordered route and terminal correct.

## Verification and limits

292 tests pass, including ray-box cases and matched-camera FOV checks. Bringup
package builds. Both live runs had no collision, timeout or infrastructure failure;
independent audits are in `reports/scan_widecamera_independent_audit_20260911_v1.json`.
Peak recorded CPU pressure in wider-camera run: 5.11%. Both runs stopped; the
existing R2 campaign PID 2137648 remained active. No R1/R2 files changed and no
protected data used. This does not establish zero interference or final robustness.

Next: address doorway viewpoints and visible entrance identity, complete the
review presentation/QA for usable samples, and continue controlled localization
diagnostics. A wider FOV has not solved every class or finished perception validation.
