# Scientific release readiness gate

`scripts/check_physical_release_readiness.py` is separate from the engineering
archive and `verify_physical_release.py`. Byte integrity is necessary, but does
not establish scientific completion. This gate does not approve a study, fit
calibration, choose an inference method, authenticate a reviewer, or run jobs.
All passing examples in its tests are synthetic, not real approvals/results.

## Explicit pinned inputs

The candidate JSON uses schema `research3-scientific-release-candidate/v1` and
an `inputs` object. Each of the following keys is a `{path, sha256}` reference
relative to an explicit final staging directory. Symlinks, path escapes and
changed bytes are rejected.

- `calibration`: exact frozen calibration bytes.
- `calibration_validation`: existing
  `research3-physical-calibration-validation/v1`, passed/frozen/human-review
  verified, no protected labels, matching calibration SHA.
- `design`: complete frozen physical design accepted by the existing design
  checker; no scientific choices are supplied by this gate.
- `design_approval`: existing physical execution approval, human
  `approved_frozen`, nonprotected campaign scope, pinned design, calibration,
  validation and scheduled manifest.
- `schedule`: existing physical comparison plan. Identity/duplicate/partition
  checks run before outcomes are read. At least two systems are required.
- `outcomes`: JSON list of existing campaign-outcome/v1 rows, each additionally
  carrying `evaluation_mode: physical_live`. Every scheduled row must appear
  once with matching identity, attempted/dispatched true, infrastructure failure
  false, and known boolean navigation, ordered completion, terminal identity,
  collision and timeout endpoints. This is a conservative completion gate, not
  permission to discard failed or unknown attempts. Navigation failure is valid
  evidence; missing/infrastructure/unknown results do not become success.
- `inference`: `research3-physical-final-inference/v1`, human approved_frozen,
  physical_live, pinned design/schedule/outcomes/heldout-report SHA values,
  `primary_contrast`, `multiplicity_policy` and
  `confirmatory_inference_method` exactly matching the approved design,
  `scheduled_missingness_accounted: true`, `full_schedule_analyzed: true`,
  nonempty `results` and `limitations`. The gate checks consistency, not the
  mathematical validity of those results or the chosen inference method.
- `heldout_authorization`: a separate
  `research3-physical-heldout-authorization/v1` with human approved_frozen,
  `authorization_scope: physical_heldout_report_verification`, pinned
  `heldout_report`, design/calibration SHA values and unique nonempty
  `scheduled_episode_ids`. This is separate from authorization to run a heldout
  measurement audit and avoids a circular report/authorization hash.
- `heldout_report`: `research3-physical-heldout-audit/v1`, passed/complete/
  authorized/independent_measurement_verified true,
  `evidence_scope: physical_world_heldout`, matching design/calibration,
  and exact audited IDs/counts covering the separately authorized schedule.
  The `unresolved` list must be present and empty.
  `passed` means measurement audit validity, not universal navigation success.
- `inventory`: existing `research3-local-file-manifest/v1` covering every pinned
  scientific input and all other staging members, with exact checksums and no
  unexpected files. The inventory itself is the only implicit exclusion.

Keep the candidate and output report outside the staging directory unless they
are explicitly inventoried. Put original source/model/asset/environment and
run-level evidence into that inventory: checking the report attestations does
not reconstruct historical sources or substitute for their release inclusion.

## Default-deny access and execution

Without `--allow-authorized-heldout-report`, the checker returns blocked and
does not open the heldout authorization, report or final inventory members.
Even with that flag, all nonprotected prerequisite gates must first pass; then
the separately pinned human report-verification authorization is checked before
the report is opened. The flag alone is not authorization. There is no live
execution, archive extraction, broad evidence discovery or hidden heldout read.

An empty candidate (`inputs: {}`) safely enumerates missing gates without
reading any evidence. `--output` is create-once; exit status is 1 while blocked.
The current engineering review packet, smoke runs, and archive cannot satisfy
this scientific gate. A future producer must supply real approved inference
and independently audited full comparative and physical heldout evidence.
The protected runtime integration is a separate prerequisite, not provided by
this checker. No real protected data were used to implement or test it.
