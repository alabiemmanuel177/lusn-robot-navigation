# Offline analysis and release verification tooling

These tools prepare stages 3–4; they do not execute or certify a campaign. Their
tests use synthetic fixtures only. No new live or held-out results were opened
to implement or test them.

## Scheduled cohort analysis

`scripts/analyze_physical_campaign.py` accepts a JSON
`research3-physical-comparison-plan/v1` manifest with explicit `episodes`, and a
JSON list of `research3-physical-campaign-outcome/v1` records. Each outcome must
repeat the scheduled `episode_id`, `variant_id`, `system_id`, `partition`,
`base_instruction_id`, and integer `paired_block_index`. This draft tool accepts development/validation
only; held-out analysis needs a separately authorized evaluator extension.
When scheduled, `condition` must also be repeated exactly.

Each record must explicitly supply boolean `attempted`, `dispatched`, and
`infrastructure_failure`; plus boolean-or-null `navigation_success`,
`instruction_completion`, `terminal_identity_correct`, `collision`, and `timeout`.
No endpoint measurement is accepted for an undispatched episode. An absent record
remains missing, rather than becoming a success or a silently excluded attempt.
The analyzer rejects unknown episode IDs, duplicates and inconsistent identities.

Known collision or timeout makes navigation and instruction completion false even
when terminal identity is unknown. Otherwise missing safety evidence prevents
success claims; infrastructure failures remain explicit with unestablished
completion unknown. Original reported navigation/instruction fields are retained
alongside normalized endpoints. Unknown does not mean false.

System summaries retain the scheduled denominator, missing records, attempts,
dispatches, infrastructure failures, and endpoint true/false/unknown counts.
Paired descriptive differences are system minus baseline, only over observed
pairs with matching partition, block and instruction variant. Incomplete pairs
and unmatched scheduled blocks remain explicit. No confidence intervals,
significance claims or causal effects are fabricated. These records still require
independent trajectory/contact audits before scientific interpretation.

Instruction-completion sensitivity bounds retain unknown arms as [0,1] and hold
observed endpoints fixed. Contrasts are averaged across paired condition/seed slots
within each `base_instruction_id`, then equally across worlds (partition remains
part of world identity). The report supplies each world's bounds, number of worlds,
unknown-arm counts and overall lower/upper mean contrast. These are missing-outcome
bounds, not confidence intervals or an approved primary analysis. Unmatched
scheduled blocks are explicitly excluded and counted; missing outcome records in
otherwise scheduled pairs remain included in bounds.

```sh
PYTHONPATH=src python3 scripts/analyze_physical_campaign.py \
  --manifest /path/to/scheduled.json --outcomes /path/to/outcomes.json \
  --baseline B1 --output /path/to/new-analysis.json
```

Output creation is exclusive, inputs are SHA256-pinned, and status is always
`draft_not_final`. Setting manifest readiness flags does not promote it to a
final release. A frozen protocol, validated interventions/calibration, isolated
live execution and authorized held-out evaluation remain separate requirements.

## Local release integrity

`scripts/verify_physical_release.py` reads a dedicated staging directory and a
JSON `research3-local-file-manifest/v1` containing a `files` list of records:
`{"path": "relative/name", "sha256": "64 lowercase hex characters"}`.

It rejects duplicate paths/JSON keys and noncanonical or escaping paths; refuses
symlink members; and reports missing, changed and unexpected files. The input
manifest itself is exempt from unexpected-file detection when stored inside the
staging directory. Use a dedicated staging directory, not the working repository.
No archives are extracted, providers modified or external services contacted.

```sh
python3 scripts/verify_physical_release.py \
  --root /path/to/staging --manifest /path/to/staging/MANIFEST.json
```

Exit status is zero only when byte integrity and exact file inventory pass.
`scientific_release_complete` remains false: matching hashes prove neither valid
experiments nor full environmental reproducibility. The verifier checks a local
manifest, not the older pilot tarball manifest format. It cannot authenticate an
untrusted manifest or replace scientific gate review.
