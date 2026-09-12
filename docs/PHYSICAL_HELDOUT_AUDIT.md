# Separately authorized physical held-out measurement audit

`scripts/audit_physical_heldout.py` is a default-deny **post-execution** evaluator.
It does not launch a simulator, expose protected images for calibration, fit on
test labels, or turn historical graph results into physical evidence.

The first input read is an explicit human authorization envelope using
`research3-physical-heldout-authorization/v1`, `status: approved_frozen`,
`authorization_scope: physical_heldout_measurement_audit`, `reviewer_type: human`,
named approver/time, pinned complete frozen design and non-protected calibration,
the exact schedule SHA-256 and `execution_source_sha256` covering the required
runtime sources. The actual loaded evaluator scripts/modules must match those
pins, including when auditing an alternate staging root; shadowed imports and
historical differing evaluators fail closed. A typed approver name is an external attestation,
not authenticated identity. Without this authorization, schedule, assignments,
worlds and outcomes are not opened.

The schedule schema is `research3-physical-heldout-schedule/v1`, evidence scope
`physical_world_heldout`; it pins design and calibration and enumerates unique
episode IDs, held-out map identities, systems, variants, frozen simulator seeds
and exact `asset_sha256` bindings for each scheduled world.
Assignments explicitly pin each request, summary, final measurements and sealed
pre-evaluation measurements file. Each list item has `episode_id` and the four
`{path, sha256}` references named `request`, `summary`, `measurements`, and
`sealed_measurements`. Paths are contained relative files; symlinks are rejected.
The sealed file is normally `measurements.pre_evaluation.json`, while final
measurements are `measurements.json`. Both use `research3-live-measurements/v2`.
The summary's `pre_evaluation_measurements_sha256` must match the seal, and its
`measurements_sha256` must match the final record. They are
not a recursive discovery of protected folders. Each audited result must match
its scheduled identity, exact source measurements and world assets; the physical
scorer checks that the supplied trajectory exactly matches the sealed record
before opening evaluator assets, then recomputes collision, trajectory, ordered gates, terminal identity and
navigation endpoints. Task failures are legitimate results. Missing assignments,
missing measurements, inconsistent summaries and unknown trajectories remain
unresolved, never manufactured successes or failures.

The audit constructs its evaluation context only after its own approval checks;
it does not require or reuse a live-launch approval as permission to evaluate.
The final measurements must exactly equal the sealed telemetry plus the
recomputed annotations. Required execution sources include the runtime helper's
`SOURCE_FILES`; current evaluator hashes and import locations must match before
protected access. Runtime admission separately checks Research 1 code/configuration
pins as described in [the runtime reference](PHYSICAL_HELDOUT_RUNTIME.md).

The output is `research3-physical-heldout-audit/v1`. `passed` means a complete valid
measurement audit, not that every robot succeeded. Inference and research release
are separate gates. A separate report-verification authorization can pin this
output for the scientific release checker without circularly requiring the audit
to pin its own output in advance.

```sh
PYTHONPATH=src python3 scripts/audit_physical_heldout.py \
  --approval /path/to/explicit-audit-authorization.json \
  --manifest /path/to/frozen-heldout-schedule.json \
  --assignments /path/to/explicit-measurement-assignments.json \
  --output /path/to/new-heldout-audit.json
```

Only synthetic fixtures have exercised this adapter during pre-review work. No
actual protected physical assets/results have been opened by that preparation.
The ordinary engineering CLI continues to reject held-out execution. The
separate [authorized runtime and derivative builder](PHYSICAL_HELDOUT_RUNTIME.md)
are now implemented and tested with synthetic fixtures; this audit neither
launches them nor grants their permissions. See
[the authorized workflow](howto-authorized-physical-heldout.md) for their commands.
