# Consolidated non-protected review handoff

`scripts/prepare_consolidated_review.py` is an offline, create-once inventory
backend. It reuses `join_physical_review_capture.py` unchanged for exact provider
task/media matching and integrity checks. It does not collect detections, display
a review UI, generate labels, freeze calibration, or declare research complete.

## Gates

Only the physical maps r001–r014 are eligible: r001–r010 development and r011–r014
validation. Partition and explicit non-protected declaration are checked before
capture/media access. Protected or uncertain scope is rejected, including a
protected map disguised as development. Duplicate run inputs/IDs are rejected.

Each retained provider row is inventoried, including rejected rows and their
reasons. Repeated IDs within a run are rejected by the exact-join audit. Identity
is scoped by `(run_id, observation_id)` because simulated clocks and provider IDs
can repeat between separate runs. Source-file hashes, source revision, map hash,
request hash, task-log hash, frame metadata hash, and canonical per-task hash are
retained. Missing map/source provenance prevents readiness.

An exact join is necessary but not sufficient. Every item additionally requires
an individual machine visual-QA attestation with this structure:

```json
{
  "schema_version": "research3-machine-visual-qa/v1",
  "run_id": "<actual run ID>",
  "observation_id": "<actual observation ID>",
  "task_sha256": "<canonical task hash from inventory>",
  "frame_sha256": "<exact frame metadata hash from inventory>",
  "request_sha256": "<exact request file hash from inventory>",
  "provider_tasks_sha256": "<exact provider task log hash from inventory>",
  "attested_by": "<agent/reviewer performing visual QA>",
  "full_frame_visible": true,
  "context_sufficient": true,
  "pixel_marker_verified": true,
  "identity_decidable": true
}
```

These attestations must result from actually viewing the exact marked source
frame and its wider context—not merely passing a schema test. The backend validates
binding and declarations; it cannot independently prove the claimed visual audit
happened. An attestation says the item is usable for human review, **not** that the
detector is correct. Stale bindings, duplicate attestations, failed checks, or
non-null correctness declarations reject the item. Unmatched QA rows are retained.
The output always keeps human correctness null and the human reviewer blank.

## Coverage and status

The default coverage grid is all fourteen non-protected maps crossed with chair,
doorway, office entrance and laboratory entrance. Missing class/map cells remain
explicit. A represented cell only means it contains a QA-ready unlabelled item;
it does not establish adequate sample size, naturally correct/incorrect coverage,
confidence calibration, recall, or independent viewpoints. Those remain separate
protocol gates. CLI scope overrides are recorded and must not be presented as full
fourteen-map validation.

With no live inputs, missing media, or no valid individual visual QA, status is
`blocked`. Some usable items produce `partial_human_review_handoff` when other
items, runs or coverage remain incomplete. Even `ready_for_human_review` is only
a handoff for genuine human review, not a completed study or validated detector.

```sh
python3 scripts/prepare_consolidated_review.py \
  --run reports/physical_live_episodes/ACTUAL_NONPROTECTED_RUN \
  --qa /tmp/actual_individual_visual_qa.jsonl \
  --output /tmp/consolidated_review_inventory.json
```

Omit `--qa` for a diagnostic inventory of missing attestations. Output must not
already exist. Tests use synthetic media and explicit synthetic attestations;
their passing results are software validation only, never live or human evidence.

The inventory's `ready_for_human_review` status is image-QA readiness only. The
current UI additionally requires `--evidence` and `--policy`; a draft permits
preview only, with saving disabled. Genuine review covers category, stable entity
association and pose separately. Follow
[PHYSICAL_REVIEW_UI.md](PHYSICAL_REVIEW_UI.md) rather than historical category-only
instructions.
