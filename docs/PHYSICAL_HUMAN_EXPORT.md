# Physical human-review export

`scripts/export_physical_human_review.py` consumes an existing physical review
progress journal, consolidated inventory and its exact QA input. It opens
`ReviewStore(..., resume=True)` to revalidate the header, non-protected source
joins and individual visual-QA bindings without writing progress or creating
missing human review files. Binary physical calibration export now requires
joint v2 review plus explicit `--evidence` and `--policy` inputs. The policy is the
approved joint-review rubric, not the separate coverage `--requirements`.

Every historical event must have the exact supported field set, matching
run/observation/task/frame bindings, a named reviewer, an explicit verdict,
consistent boolean/null correctness and review status, and ordered timezone-aware
timestamps. Duplicate events, timestamp conflicts, explicit synthetic/agent
reviewer identities, and stale evidence are rejected. Legitimate later corrections
supersede earlier decisions only for export; the append-only journal is preserved.

Only latest joint v2 Correct and Incorrect decisions export as `landmark-review-task/v1`
rows with the original provider fields unchanged except `review_status`,
`reviewer_id`, and `correct`. The latter becomes integer 1/0. Normalized
`landmark-calibration-sample/v1` rows match the Research 1 provider's
`finalize_human_calibration_rows` output: observation ID, non-protected partition,
category, probability and binary correctness. Provider observation IDs must be
globally unique; cross-run collisions are rejected, not silently renamed.

Joint events use `research3-physical-human-review-audit/v2` and explicitly record
`category`, `entity_association`, and `pose` in `dimension_verdicts`, bound to the
reference-evidence, rubric and individual evidence-row hashes. All three correct
gives label 1; any incorrect gives label 0; otherwise an unreviewable dimension
keeps the item excluded. The exporter recomputes that aggregate, rejects missing
dimensions or conflicting verdicts, and requires rubric approval before every
event. Pose tolerance and treatment of catalogue-supplied yaw require genuine
human-approved rules; the exporter does not select them.

Legacy v1 category-only journals remain readable, but their binary judgments are
excluded with `legacy_category_only_not_joint_review`, including old Correct
judgments. They never silently become joint positives or negatives. Preserve old
logs and artifacts; conduct joint review in a new create-once journal. See the
[joint review interface](PHYSICAL_JOINT_REVIEW.md) and
[joint calibration contract](PHYSICAL_JOINT_CALIBRATION.md).

Unreviewable items retain null correctness and are listed separately with pending
items and exclusion counts. They never become incorrect examples. The tool does
not infer labels from geometry, confidence, colours, machine QA, or test results.
It can reject explicit fake provenance but cannot prove a typed name belongs to
a human: `human_identity_authenticated` remains false. Genuine user review is an
external provenance requirement, not something software can honestly manufacture.

```sh
PYTHONPATH=src python3 scripts/export_physical_human_review.py \
  --inventory /path/to/consolidated_inventory.json \
  --qa /path/to/actual_machine_visual_qa.jsonl \
  --progress /path/to/joint_human_progress.jsonl \
  --evidence /path/to/joint_reference_evidence.json \
  --policy /path/to/approved_joint_review_policy.json \
  --requirements /path/to/prespecified_coverage_requirements.json \
  --output /path/to/new_export_directory
```

The output directory must not exist. It contains `reviewed_tasks.jsonl`,
`calibration_samples.jsonl`, and `readiness.json`, with source hashes and exclusions.
Readiness uses `research3-physical-human-export/v2` and includes the separate
`research3-joint-calibration-label-contract/v1` target, dimension and accepted-label
bindings. The provider and normalized-sample v1 formats remain unchanged; their
binary target is established by this additional contract.
Nothing is fitted or frozen by this command, even when labels are exportable.

Coverage requirements are explicit, not invented after looking at results:

```json
{
  "schema_version": "research3-physical-calibration-coverage/v1",
  "minimum_per_map_class_outcome": 5,
  "minimum_per_class_confidence_bin": 5,
  "confidence_bin_edges": [0, 0.5, 0.8, 1]
}
```

These numbers are schema examples, not an approved research protocol. Requirements
must be prespecified for the study. Under schema v1, every inventory-required map/class must meet
both correct and incorrect minima, and every class/confidence bin must meet its
minimum. Bins are left-inclusive/right-exclusive except the last includes 1.
Missing requirements, absent genuine binary labels, incomplete strata, pending
or unreviewable items all keep the readiness report blocked. Passing these checks
means only `ready_for_calibration_protocol_review`, never automatic permission to
fit/freeze. Natural-error prevalence, independent viewpoints and recall coverage
still require separate protocol checks. All exporter tests use isolated synthetic
fixtures and are not human calibration evidence.

## Coverage schema v2: explicit outcome scope and exclusions

Coverage schema v1 remains supported with its original behavior: both outcomes in every
map/class, and all unreviewable items blocking readiness. That is one possible
protocol, not a universal scientific requirement. This coverage-schema support
does not make legacy v1 category-only review events eligible for joint export.

Schema `research3-physical-calibration-coverage/v2` instead requires these explicit
fields; no actual study values or policy choice are selected by the exporter:

- `outcome_coverage_scope`: `global_class` pools binary outcomes across required
  maps per class; `map_class` checks the binary threshold separately in every
  required map/class.
- `minimum_per_map_class_total`: positive minimum accepted binary labels per
  map/class under either scope. Unreviewable cases do not count toward this total.
- `minimum_per_class_outcome`: positive minimum for each binary outcome at the
  selected outcome scope above.
- `minimum_per_class_confidence_bin` and `confidence_bin_edges`: unchanged positive
  per-class confidence coverage requirements.
- `unreviewable_exclusion_policy`: `allow_with_counts` excludes genuinely
  unreviewable items from fitting while retaining their counts/reasons, or `block`
  retains them as readiness blockers. Pending human reviews always block.

The chosen policy and its canonical SHA-256 are retained in the readiness report.
Specify and freeze these decisions before collecting/evaluating the relevant
labels. Do not switch from map-level to pooled coverage, or permit exclusions,
after seeing inconvenient results merely to pass readiness. Passing v2 still
means only `ready_for_calibration_protocol_review`; no fitting or freezing occurs.
