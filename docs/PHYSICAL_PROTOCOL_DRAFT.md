# Physical-world comparative protocol: engineering draft

This document prepares Stage 3; it does **not** freeze a protocol, authorize
execution, validate calibration transfer, or report campaign results. Previous
graph and provider-world results remain historical evidence, not replacements
for the new physical-world campaign.

11 September update: absent-anchor runtime integration and a Research 3-owned
seeded Gazebo launch are now implemented and pass offline checks. All 112
non-protected world-condition inputs validate. Live acceptance, calibration and
design freeze remain open. The implementation limitations described below reflect
the earlier draft where explicitly superseded by this update. See
`OFFLINE_COMPLETION_20260911.md` and `OFFLINE_EXPERIMENT_DESIGN.md`.

## Matrix and ordering

The draft reserves 20 physical worlds: 10 development, 4 validation and 6 held-out.
Each has four route alternatives. Five systems (B1, B2, B4, B5, B6) share the same
eight existing corruption conditions. One existing instruction seed (`s0`) yields
400 development and 160 validation episodes, or 112 paired blocks of five systems.
The held-out reservation would add 240 episodes, but requires its own gated plan;
the preparation tool does not open held-out files or construct execution commands.

Execution-order seed 0 shuffles blocks and the initial system order. A cyclic
rotation counterbalances within-block system position to within one occurrence
across 112 blocks. This is position balancing, not a guarantee against every
carryover effect; reset simulation, monitor state and belief state between episodes.
Instruction seed, ordering seed and simulator random seed are distinct. Simulator
seed control remains unresolved. The one-seed matrix is an engineering draft,
not a statistically justified confirmatory sample size. Determine replication,
power and preregistered paired analysis before freezing or inspecting held-out live
outcomes. Worlds share a procedural family; 20 layouts are not 20 independent
real buildings and do not establish cross-template generalization.

## Conditions and missingness

Conditions are truthful original, truthful paraphrase, ambiguous reference,
missing landmark, attribute corruption, relation corruption, topology corruption,
and false inserted clause. Variant IDs reserve existing `base-condition-s0` IDs;
the runner must independently validate deployed text membership before execution.

Missing landmark is an environmental intervention, not dropped detector messages
or altered instruction text. Before execution, implement and audit removal of the
chair asset and the corresponding perception truth, preserving evaluator intent
and documenting occupancy-map treatment consistently across systems. Keep runtime
route hypotheses separate from evaluator truth. A failed detector is not a valid
substitute for physical absence. Validate every condition on development worlds
before freezing. The single-chair layouts may make the ambiguous-reference
condition weaker than its name suggests; document this construct limitation and
resolve any revised condition definition before freezing, never after held-out
outcome inspection.

The engineering runner explicitly refuses existing `missing_landmark-s0`
variants: original v1 worlds still contain the chair. Separate non-protected
derivatives now exist in `data/physical_absence_worlds_v1` (14 worlds). All pass
the independent SDF aperture, footprint connectivity and four-route ordering audit.
The builder removes exactly six chair models and the perception entity, and frees
the chair occupancy consistently for all systems. Other models, route goals,
terminal entities and canonical ordered reference planes are unchanged. Passing
the plane at the former chair location is not evidence of observing a chair.
Every derivative retains source/output hashes and a create-once intervention audit.
Original worlds were checked unchanged. These are draft interventions, not live
validation: runtime handling of an intentionally absent anchor still needs
integration, and the runner's refusal remains in place. Map/estimand treatment
must be accepted in the frozen protocol before comparative execution.

Regenerate into a new output directory using
`PYTHONPATH=src python3 scripts/build_physical_absence_worlds.py --output NEW_DIRECTORY`.
The builder never permits protected IDs and never overwrites existing output.

Retain every attempt with immutable IDs and raw evidence. Pre-dispatch setup
failures have no navigation outcome. Post-dispatch infrastructure interruption is
a retained infrastructure outcome, not a silent exclusion or automatically a
navigation failure. Missing trajectory, collision or terminal evidence is unknown,
not zero or success. Report scheduled, attempted, dispatched, evaluable, unknown
and infrastructure counts by system/condition. Keep known collisions and timeouts
as failures even if terminal evidence is missing. Any recovery attempt gets a
separate supplemental ID; it never replaces the original. Freeze the primary
estimand and sensitivity analysis for unknowns before execution, with paired-block
completeness and missingness disclosed.

## Mandatory gates before execution

- Stage 1 physical inspection, correct fresh-observation handling and goal checks.
- Detector coverage measured in new-world development/validation scenes, genuine
  human review where required, and revised calibration frozen without protected labels.
- Validated interventions and independent ordered/terminal/collision measurements.
- Immutable source, dirty-tree snapshot, assets, models, calibration and dependency
  hashes; a Git revision alone is insufficient for this dirty workspace.
- Research 2 isolation: distinct ROS domain and scoped worker/output paths, no
  global process cleanup or configuration changes, and measured resource headroom.
  Stop only Research 3's own processes if coexistence proves unsafe.
- Frozen protocol, simulator-seed policy, replication/sample-size justification,
  execution order, endpoints, paired analysis and missing-data policy.
- Explicit held-out evaluator access control and separate authorization gate.

All gate states in `configs/physical_campaign_draft_v1.yaml` are intentionally
pending. The generator remains non-executable even if someone marks them passed.
It reads only 14 non-protected execution catalogues and retains their hashes; this
is a draft-input audit, not a full source/asset freeze.

## Generate a create-once draft

With the project Python environment active:

```sh
PYTHONPATH=src python scripts/prepare_physical_comparison.py --output /tmp/research3-physical-comparison-draft.json
PYTHONPATH=src pytest -q tests/test_physical_comparison.py
```

An existing output is rejected. Generation launches no ROS/Gazebo process and does
not alter Research 1 or Research 2. Final reproducible release remains Stage 4 work
after genuine live evidence and its prespecified analysis are complete.
