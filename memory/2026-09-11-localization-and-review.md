# Debug report: guarded localization and review continuation

Status: DONE_WITH_CONCERNS — diagnostic instrumentation verified live; navigation
root mechanism remains open. Two serial development runs completed, no R1/R2 edits.

## Symptom and root-cause investigation

Nav2 reports success while independent point-goal scoring fails. Prior run error
was 0.4494 m against an unchanged 0.35 m criterion. The retained prior evidence
lacked time-paired AMCL poses, so a localization-disagreement hypothesis could not
be tested honestly from that run. R3's monitor now retains at most 2048 AMCL/GT
pairs with explicit timestamps, using a maximum 100 ms pairing gap and null for
unmatched truth. It does not feed evaluator truth to the navigation policy.

Diagnostic run `r3-localization-dev10-20260911-v1` retained 33 pairs. Error between
AMCL and matched truth grew from 0.0131 m to 0.5801 m. The last estimate was
0.3430 m from the commanded goal while its time-matched physical position was
0.7509 m away. This sample preceded episode end by 0.618 s; it is not the exact
Nav2 goal-checking pose. Final physical point error was 0.61294 m. Localization
disagreement is a demonstrated contributor, not yet an explanation of its filter,
sensor or geometry cause. No threshold or AMCL setting was tuned to mask failure.
Ordered route and terminal passed; collision/timeout/infrastructure failure false.

## Review inspection

All five previously exact-matched full RGB frames were decoded without alteration
and viewed individually. None was approved for human handoff: cropped chair views,
an edge-clipped plaque with no laboratory identifier, and incomplete doorway
context. Usability findings (not human correctness labels) are retained in
`reports/coexist_dev10_visual_inspection_20260911_v1.json`.

The relative-path join failure was independently reproduced by a new regression
test: resolved absolute frame paths were relativized against an unresolved run
directory. Resolving the input directory fixes the actual cause. The test failed
before and passed after; rerunning the actual relative-path command produced
byte-identical v1/v2 join reports with unchanged media and no new review approvals.

## Separate absent-chair integration check

`r3-absence-dev10-20260911-v1` used the audited absent-chair derivative, unchanged
seed 1 and B6. Point-goal error 0.26735 m, correct ordered route and terminal,
no collision/timeout/infrastructure failure. Zero anchor observation IDs appeared
in decision candidates. Progress past the former chair plane does not imply
observing an absent chair. This is one engineering integration case, not detector
calibration or a comparative campaign result.

## Verification and resource boundary

286 Python tests passed. New tests cover bounded timestamp-paired telemetry and
relative-path equivalence. Both runs were low priority and serial on domain 89,
with unique Gazebo partitions. Recorded peak CPU pressure: 5.94% diagnostic,
4.73% absence; minimum available RAM above 23 GiB. Both shut down; existing R2
campaign PID 2137648 remained active. This does not prove unchanged R2 performance
or GPU headroom. Independent audit reports retain both success and failure.

Next: determine localization drift mechanism, improve capture viewpoints and
visible entrance semantics before human review, and validate genuine physical
inspection behavior. No more capture volume is claimed to solve undecidable images.
