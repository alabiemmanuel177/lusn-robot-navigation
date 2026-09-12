# Physical calibration evidence bridge

`scripts/validate_physical_calibration.py` closes the export-to-campaign artifact
interface. It does not fit a calibration, choose coverage minima, approve a policy,
authenticate a human, or create labels. No actual approved calibration artifact
has been produced for the current review packet.

Each accepted scene binding includes the full captured `provider_source_snapshot`
as well as the R3 source hashes. Missing/incomplete provider pins block admission;
the campaign recomputes the explicit provider source/build snapshot and requires
exact equality. This prevents labels from silently transferring to a changed
detector dependency. It is not a claim of complete ROS/model/environment closure.

Inputs are explicit `--inventory`, `--qa`, `--progress`, `--export-directory`,
`--evidence`, `--policy`, `--requirements`, `--calibration`, and `--approval`.
Here `--policy` is the approved joint-review rubric; `--requirements` is the
separate prespecified coverage policy. `--output` is create-once.
Missing inputs yield a blocked draft (exit 2); inconsistent/stale inputs are errors.
No protected files or global report directories are searched.

The bridge reruns the v2 joint human exporter against immutable
UI/QA/provider/media/reference-evidence/rubric bindings and compares all three
existing export files semantically. Pending reviews,
excluded observations and confidence/class coverage obey the supplied policy.
Calibration must pin the exact exported normalized sample bytes and have both
outcomes within its declared fitting partition. It must also contain the exact
revalidated `joint_review_contract`, binding category, stable entity association,
pose and the approved rubric/evidence. A legacy category-only calibrator cannot
be admitted, even if its sample checksum matches. Existing fitter metrics are
in-sample diagnostics, not independent efficacy validation.

The explicit approval schema is `research3-physical-calibration-approval/v2`:

- `status: approved_frozen`, `reviewer_type: human`, a named `approved_by`, and
  `authorization_scope: nonprotected_physical_calibration`.
- `input_sha256`: exact hashes keyed by `inventory_sha256`, `qa_sha256`,
  `progress_sha256`, `requirements_sha256`, `calibration_sha256`,
  `evidence_sha256`, `policy_sha256`,
  `reviewed_tasks.jsonl_sha256`, `calibration_samples.jsonl_sha256`, and
  `readiness.json_sha256`.
- Timezone-aware `coverage_policy_approved_at` preceding review and `approved_at`
  following the final review; this checks declared ordering, not timestamp authenticity.
- `accepted_scene_bindings` equal to the bridge's evidence-derived bindings;
  `fit_metrics_are_in_sample_only: true` acknowledges the inference limitation.

The joint rubric's own timezone-aware approval must precede every retained
dimension verdict. Coverage approval and final calibration approval are separate
requirements; none is generated automatically. See the
[joint target and rubric contract](PHYSICAL_JOINT_CALIBRATION.md).

```sh
PYTHONPATH=src python3 scripts/validate_physical_calibration.py \
  --inventory /path/to/consolidated_inventory.json \
  --qa /path/to/actual_machine_visual_qa.jsonl \
  --progress /path/to/joint_human_progress.jsonl \
  --evidence /path/to/joint_reference_evidence.json \
  --policy /path/to/approved_joint_review_policy.json \
  --export-directory /path/to/joint_export_directory \
  --requirements /path/to/prespecified_coverage_requirements.json \
  --calibration /path/to/joint_calibration_candidate.json \
  --approval /path/to/explicit_calibration_approval_v2.json \
  --output /path/to/new_calibration_validation.json
```

Each binding retains map, base-scene and adapted runtime-scene hashes, camera
profile hash, FOV, runtime-source hashes and contributing run/observation IDs.
Only runs with accepted binary human labels contribute. Missing exact bindings
block; adapted scene bytes are rehashed. No additional map, absence intervention,
camera profile or source revision is inferred covered. Deliberate colour-occlusion
stress examples do not estimate natural error prevalence. A policy accepting their
role must be externally justified; this script cannot supply that justification.

With every prerequisite satisfied, output implements
`research3-physical-calibration-validation/v1` with `passed`, `frozen`, and
`human_review_verified` true. These mean externally approved, structurally checked
scope only: `human_identity_authenticated` and `study_complete` remain false.
Consumers must match exact `scene_bindings`, not form Cartesian combinations of
the compatibility map/scene/profile lists. A base scene is not its palette-adapted
runtime scene. A separate scientific acceptance/efficacy gate remains necessary.

All tests use synthetic fixtures. The physical joint candidate fitter is
`scripts/fit_physical_joint_calibration.py`; it revalidates the genuine joint
export and preserves the target/rubric/evidence contract, with an explicitly
selected partition and minimum sample count. It does not grant deployment
approval. The historical generic freezer does not supply this joint contract and
is not this admission path. The bridge never runs a fitter or silently promotes
a blocked draft. See [joint calibration admission](PHYSICAL_JOINT_CALIBRATION.md).
