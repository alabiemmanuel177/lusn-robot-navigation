# Live implementation and package handoff

Updated 8 September 2026.

## Implemented

- The planner selects B1, B2, B4, B5 or B6 through `system_id`. All use the same
  adapter and monitor freshness requirement; the variants' risk policies differ.
- Inspection chooses a distinct intermediate point on the successful Nav2 path,
  at least 0.5 m from both endpoints. After reaching it, the adapter allows a two
  second observation interval before another route-bearing decision. It permits
  one inspection per instruction and abstains if inspection remains necessary.
  A stop decision may end the trial immediately. Short paths without a distinct
  viewpoint cause abstention. This is a bounded heuristic, not an optimized
  information-gain viewpoint planner.
- The runner retains ground-truth positions, in-window predictions, decisions and
  provider terminal annotations in `measurements.json`, hash-linked from the v2
  summary. Ground truth is used by the evaluator, not the planner.
- Terminal identity is scored from the final measured position and stable provider
  entrance instances within 0.75 m. Multiple nearby terminal instances remain
  ambiguous. This measures proximity to a terminal entity, not all clauses of an
  instruction. Full instruction completion remains null.
- Exceptions after dispatch retain an infrastructure-failure summary. The campaign
  runner does not replace a trial once a summary exists. The new analyzer requires
  manual audit of incomplete evidence rather than silently excluding it.
- `scripts/analyze_measured_live.py` verifies measurement hashes, measured distance,
  sample counts, collision counts, prediction windows and terminal identity scores.
  It accepts collision/timeout records when their evidence is complete.

## Testing preparation

`reports/live_comparison_plan_v1.json` contains 560 unique diagnostic cases:
14 development/validation routes × eight instruction variants × five systems.
It is a preparation artifact; no 560-episode campaign has run. Generate a new
create-once copy with:

```bash
python3 scripts/prepare_live_comparison.py --output reports/live_comparison_plan_next.json
```

For an individual non-protected trial, source `scripts/ros_env.zsh`, use an isolated
ROS domain/Gazebo partition, and invoke `scripts/run_live_episode.py` with explicit
`--route-id`, `--variant-id`, `--system-id`, and a fresh `--run-id`. The runner sets
a per-run cleanup worker identifier unless the caller supplies one.

The inspection pilot is `reports/live_episodes/r3-inspection-dev00-v1`. Its trace
records an inspection goal at approximately (-0.467, -0.501), followed by inspection
completion and risk-driven abstention; the terminal route goal is (1.0, -0.5).
The audit is `reports/measured_live_inspection_v1.json`.

All five systems have a development smoke episode on `dev_00_r0`: B1/B2/B4/B5
reached the expected terminal instance; B6 inspected and abstained. Their combined
checksum/recomputation audit is `reports/measured_live_variants_v1.json`. These
single-route, truthful-instruction pilots do not establish comparative performance.
Verification: 71 Python tests passed, the three changed ROS packages built, and
their five package tests passed.

## Packaging

`scripts/package_research3.py --output reports/research3_engineering_snapshot_v1.tar.gz`
creates a local source/evidence archive and adjacent SHA-256 file. It includes
selected Research 1/2/3 source/configuration files, the verified frozen Research 2
checkpoint/calibrator, Research 3 calibration, prepared matrix, protected graph
results, and structured live evidence. `MANIFEST.json` contains a checksum for
every payload file and repository revision/dirty state. The packager reopens the
archive and verifies each member without extracting it.

This snapshots current files, including uncommitted work. It does not claim that
current sources were the exact historical graph execution sources. ROS/Gazebo,
complete Python environments, full map assets and large capture media are external
dependencies. It is an engineering handoff package, not a self-contained final
research release. No provider repository is modified and nothing is pushed.

## Still required before a research comparison

1. Independent annotations and evaluation for the ordered clauses of each
   instruction, including relations and doorway choices. Terminal proximity alone
   cannot validate them.
2. Live contact/failure-path validation, and complete evidence for infrastructure
   failures. Collision handling currently has synthetic audit coverage; the listed
   Gazebo pilots did not generate a collision.
3. Multiple meaningful candidate routes and live route-risk measurements. Current
   catalogues match an instruction to one platform route and provide a prior risk;
   this limits what comparisons of grounding choices can establish.
4. Freeze campaign ordering, source/environment dependencies, exclusion rules and
   analysis before executing the comparative study. The prepared matrix is not a
   finalized confirmatory protocol; protected graph outcomes have already been seen.
5. Provider test scene/semantic-route catalogues for a future held-out live study.

The human landmark review and frozen calibration remain complete.
