# Stage A complete: lighting/framing candidate fails feasibility

All 144 fixed design-only assignments are accounted for. The pilot produced
119 assigned emissions, 22 genuine nondetections, and three retained
infrastructure failures. No failed assignment was retried or replaced.
The primary candidate remains disabled. Calibration coverage is not complete.

## Confidence-support screen

The predeclared pilot gate requires at least two usable emissions per class in
each unchanged raw-confidence bin. It is not the primary minimum of five.

| Class | [0,.5) | [.5,.8) | [.8,1] | Pilot screen |
| --- | ---: | ---: | ---: | --- |
| Chair | 9 | 13 | 11 | Pass |
| Doorway | 4 | 18 | 6 | Pass |
| Laboratory entrance | 0 | 18 | 11 | Fail |
| Office entrance | 0 | 17 | 12 | Fail |

Consequently, no human observation review is requested for this panel. Labels
cannot populate confidence bins in which this experiment emitted no observations.
All pilot observations remain excluded from primary fitting and coverage quotas.

## Missing-capture sensitivity

The failures were environment/setup failures before usable capture: one missing
Research 1 Python package import path, followed by two launches through an older
R3 install overlay lacking the physical simulator launch file. Both environment
causes were corrected without editing R1/R2 or the frozen provider/core. The
subsequent 141 assignments produced audited synchronized frames.

Failures by assigned class: laboratory entrance 1, office entrance 1, doorway 1.
Even under the deliberately optimistic hypothetical assumption that each failed
entrance assignment would have emitted a low-confidence observation, each
entrance class would have only one, still below the pilot minimum of two.
These are sensitivity bounds, not imputed observations or labels. Thus the
three infrastructure failures alone cannot turn this pilot into a pass.

## Verification

- All 144 actual requests match their approved identities, poses, seed, FOV,
  profiles and lighting world paths; independent panel audit passed.
- All 141 completed captures pass frame synchronization, retained raw-byte
  checksum, provider completion and exact-target selection checks.
- All 119 emitted scores reconstruct from retained RGB-D and the frozen provider.
- Original instrumentation snapshot v8 remains unchanged. The lighting adapter
  and executor have a separate checked source binding.
- Full regression suite: 1,073 passed, 1 skipped; one existing numerical warning
  in the synthetic camera-model test.
- Complete RGB previews are lossless conversions without cropping or overlays.
  Image integrity is not human verification of category/instance correctness.

The investigation skill required reproducing the environment failures before
correction; the root causes and pre-dispatch checks are recorded in
`memory/2026-09-23-stage-a-launch-environment.md`.

## Evidence and reproducibility

- Approval: `reports/redesign_stage_a_approval_20260923.json`.
- Plan: `reports/calibration_redesign_20260923_v1/plan.json`.
- Results, source binding, starts/logs and audits:
  `reports/redesign_stage_a_20260923_v1/`.
- Raw episodes: `reports/physical_live_episodes/r3-redesign-v2-*`.
- Engineering archive: `reports/research3_redesign_stage_a_20260923_v1.zip`.
- Environment preflight: `scripts/launch_redesign_stage_a.sh`.

Do not replay a completed schedule. The launch wrapper resumes only unstarted
assignments and preserves historical results. No new primary, validation, or
protected campaign was launched. No human labels, model approval, or calibration
certification were generated. Research 1/2 files and source geometry remain
unchanged; no claim of zero shared-hardware interference is made.

## Next decision

Stop this candidate at the predeclared gate. Do not start the 2,016-attempt primary
matrix, expand this pilot post hoc, reduce coverage floors, or solicit another
large human-labeling round. Modest lighting/framing changes did not establish the
required score support for entrance categories in this fixed pilot.

Another explicit scientific design decision is required: authorize a separately
specified perception/collection redesign with new source/protocol bindings, or
revise the study scope and its claims. This result does not show that every
possible detector or acquisition design must fail; it rejects this candidate.
