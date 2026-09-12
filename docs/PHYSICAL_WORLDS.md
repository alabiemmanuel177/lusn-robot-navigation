# Research 3 physical doorway worlds

Created 8 September 2026 following authorization to preserve the original doorway
navigation task. Research 1 geometry is unchanged.

## Assets and semantics

`data/physical_worlds_v1` contains 20 new Research 3 worlds: ten development, four
validation and six held-out. Each has a distinct collision layout, one physical
chair, a corridor, two physical doorway openings on each side, and four enclosed
rooms. The chair color, requested side and terminal category preserve the canonical
instruction. Room entrances have category-colored signs. Both same-side rooms share
the terminal category, so recognizing that category alone cannot select the correct
ordinal. All 80 candidate routes are footprint-reachable on their occupancy maps.

Each world directory contains:

- `world.sdf`: actual collision walls, jambs, lintels and chair, with simulator sensors.
- `map.pgm` and `map.yaml`: corresponding Nav2 occupancy map and coordinate metadata.
- `execution_catalog.json`: all four route alternatives, without the expected answer.
- `landmark_scene.yaml`: stable chair, doorway and entrance instances for perception
  integration. This is geometry-derived; it has not undergone live detector capture.
- `manifest.json`: evaluator metadata, expected route and source hashes. This file
  must not be supplied as a language-policy observation.
- `verified_ordered_geometry.json`: directed corridor, chair-passing and requested
  doorway gates. Entering another doorway is a forbidden crossing, even if the
  robot later reaches the requested entrance.
- `geometry_audit.json`: independently reconstructed footprint-feasible paths and
  scores for all four choices, plus physical aperture/jamb checks against the SDF.

The annotation checks are automated geometric proofs of the generated layout, not
human perception labels. They do not claim that a detector recognizes the objects.
The reference evaluator defines "near the entrance" as a unique matching stable
entrance instance within 1.0 m. Positional waypoint accuracy at 0.35 m is reported
separately and is not substituted for passage or terminal identity.

## Verification and evidence limits

All 20 worlds passed the static SDF/occupancy audit: 80 reachable candidate routes,
with exactly the specified route satisfying the ordered task. The validator uses
a conservative 0.30 m footprint radius. Tests cover both doorway directions, wrong
ordinals, wrong terminal identity and forbidden doorway crossings.

The prototype world `data/physical_worlds_pilot_v1/base-r010` has identical SDF/map
geometry to the finalized `base-r010` world. Its fourth reference attempt physically
crossed all three required gates and reached the correct entrance without collision,
but finished 0.509 m from the requested waypoint and failed the original additional
0.35 m point check. That failure is retained. The reference validation now reports
ordered entrance completion and waypoint accuracy separately, matching the task's
"stop near the entrance" wording. This is a disclosed development-stage criterion
clarification before comparative policy execution, not a rewritten old result.

Earlier failed attempts are also retained: one AMCL integer/double parameter error
and two simulation-clock/transform-history races. The validator now converts pose
parameters to floats and waits for three seconds of simulated transform history.

`scripts/validate_physical_navigation.py` uses an evaluator-selected Nav2 goal to
test passage geometry. It is not B1–B6 policy evaluation and does not establish
language navigation accuracy. Reports and full trajectories are retained under
`reports/physical_navigation`. The validator denies held-out live execution.

The finalized-world negative control `r3-physical-wrong-first-v2` passed validation:
Nav2 reached the first right-hand room without collision, while the ordered scorer
correctly rejected instruction completion and recorded the forbidden first-doorway
crossing. Its waypoint error was 0.473 m, separately recorded as a point-accuracy
failure. Together with the positive prototype traversal, this verifies that the
scorer distinguishes the two actual passage choices rather than only arrival.

The later positive repetition `r3-physical-correct-v5` was interrupted mid-travel by
SIGKILL of simulator/Nav2 processes and is retained as a failed trial. Other runs
were also interrupted. A concurrent Research 1 mechanism pilot was observed without
`RCN_WORKER_ID`; its legacy cleanup code kills all matching Gazebo/Nav2 processes.
This is a supported interference diagnosis, not proof of the sender of each signal.
That other experiment was left untouched. The superseded first negative attempt was
interrupted after its replacement completed. Coordinate isolated cleanup before
running the full comparative campaign.

The superseded negative attempt was interrupted during teardown before the old
validator persisted its terminal report. Its logs and an explicit interruption
ledger remain; no outcome is reconstructed or counted as success. The validator
now writes its measurement report before teardown to prevent this loss mode.

Current software verification: all 75 Research 3 Python tests pass. All 20 world
audits pass. The illustrated layout is `reports/physical_world_pilot_v1.png`.

## Protocol consequences and next integration work

These are new world IDs and a new geometry dataset. Research 1's previous clean-route
verification, calibration coverage and the earlier graph/live scores do not transfer
automatically. The original instruction split is retained, but the geometry set now
has one world per base instruction, not the former twelve provider maps. Prior
protected graph access is disclosed. No held-out live episode has run here.

Before the full comparative campaign, the live runtime must consume this new
four-alternative catalogue/map format, validate perception in these worlds, and freeze
the revised protocol and complete campaign provenance. The old 560-case plan points
to Research 1 route IDs and cannot be executed unchanged against this dataset.

Generation and static verification commands:

```bash
PYTHONPATH=src python3 scripts/build_physical_worlds.py --output data/physical_worlds_next --allow-protected
PYTHONPATH=src python3 scripts/verify_physical_world.py --world data/physical_worlds_next/base-r010
```

For a development reference run, source `scripts/ros_env.zsh`, select isolated
`ROS_DOMAIN_ID`/`GZ_PARTITION` values and invoke `scripts/validate_physical_navigation.py`
with `--world` and a fresh `--run-id`. All output paths are create-once.
