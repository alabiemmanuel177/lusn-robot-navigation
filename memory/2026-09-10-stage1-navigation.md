# Stage 1 live debug report

Status: DONE_WITH_CONCERNS. Three development attempts are retained. The fallback
bug is reproduced/fixed; new-world integration now runs, but physical inspection
validation and point-goal robustness are not complete.

## Symptoms and causes

`r3-stage1-physical-dev10-v1` entered left-first instead of right-second and later
stopped on monitor risk. Replaying its saved candidate set reproduces B6's wrong
commit: the requested alternative is Nav2-ineligible, but policy chooses another
safe route without an instruction basis. Reliable-clause commitment now requires
the supported route to be safe; otherwise abstain. Lower risk alone cannot justify
substituting a different doorway.

The adapter issued four ComputePathToPose requests concurrently. The first run
logged an aborted action handle and rejected right-second. Candidate checks are
now serialized; the scheduling regression verifies one active request at a time.
The third live run records all four assessments as eligible. This supports the
request-contention diagnosis without claiming the first action's internal abort
cause was independently instrumented.

There were no anchor observations in the first run. Five synchronized RGB-D frames
were retained in v2, with CameraInfo and TF/error metadata. The rendered chair is
visible; dominant blue pixels are about [45,60,107], unlike nominal [41,69,219].
A map-scoped development palette maps rendered colours at tolerance 10. This is
engineering colour mapping, not confidence calibration or human review. It does
not transfer to other scenes by assumption. v3 then recorded 15 distinct anchor
observation IDs and 263 terminal observation IDs in decisions; identities are not
accuracy labels or independent-viewpoint counts.

## Retained results

| Run suffix | Route | Ordered completion | Measured navigation success | Goal error | Collision |
| --- | --- | --- | --- | --- | --- |
| dev10-v1 | left-first | false | false | 0.732 m | false |
| dev10-v2 | right-second | true | true | 0.316 m | false |
| dev10-v3 | right-second | true | false | 0.390 m | false |

All run directories are under `reports/physical_live_episodes/` with prefix
`r3-stage1-physical-`. Independent audits are `reports/stage1_physical_dev10_audit_v{1,2,3}.json`.
v3 Nav2 reported success, but independent measurement failed the unchanged 0.35 m
point-goal criterion. No threshold was relaxed and no old attempt overwritten.
Ordered passage and entrance identity are separate criteria from point-goal error.
All are development runs, not comparative campaign or held-out evidence.

## Verification and scope

161 core tests pass. Changed ROS packages built and their tests passed (seven
aggregate package tests). Tests cover the semantic fallback, serialized action
scheduling and colour-only scene adaptation with stable geometry/associations.
R1 was read-only. Its two pre-existing modified files retain hashes
`f9195d8f71b26fe3207a88404fca6e7e199bdd1a8bd750d3a5d0103566057a82`
and `fbb29fc8a067e43bc87cbcba24b6f65fc08618f397b9066e50f71ebcb61ff150`.

Runs used domain 87, unique Gazebo partitions/worker IDs, lower CPU scheduling
priority and bounded numerical-library threads. Other research processes were
not stopped. Shared host scheduling remains a limitation; these runs do not
establish timing-comparable campaign conditions.

## Next work

Validate the physical inspection/new-observation path, investigate point-goal
robustness without changing scoring to erase failures, then hand off to stage 2
for measured detection coverage/human review/calibration. Keep the distinction
between newer detector frames, independent viewpoints and calibrated evidence.
