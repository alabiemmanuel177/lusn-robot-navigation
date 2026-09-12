# Proposed physical-study decisions, not approval

This document turns the existing draft's unresolved choices into a reviewable
proposal. It does not change configuration nulls, freeze a protocol, authorize
execution, replace human labels or inspect protected evidence.

## Recommended claim and contrast

Keep the study about the existing procedural corridor/doorway task. Preserve
the single-anchor ambiguous-reference variant and describe it as an underspecified
attribute, not competing-chair disambiguation. Do not add world families or
increase independent-world counts without an explicit design decision.

Propose **B6 minus B5** as the single primary contrast on independently measured
ordered completion. B5 is the calibrated fixed-policy comparator, so this focuses
on the contradiction-aware decision policy. Keep B6 versus B1/B2/B4 and safety,
navigation and efficiency endpoints descriptive/exploratory unless separately
approved as confirmatory. This avoids silently claiming four primary comparisons.

Use the draft's equal-world weighting, with equal weights over the eight scheduled
conditions and frozen simulator repetitions within each world. Pair systems by
world, condition and simulator seed. Report unknown-outcome bounds alongside point
estimates; complete-case analysis is sensitivity-only. Neither the observed graph
results nor the evolving physical engineering pilots select this primary contrast.

## Decisions still genuinely needed

- Approve the intended primary claim/contrast and whether other comparisons are
  exploratory or need a confirmatory multiplicity rule.
- Define a scientifically meaningful minimum effect. No particular improvement
  threshold is inferred from existing engineering outcomes.
- Approve inferential ambition, confidence/test method and error/power targets.
  The six reserved held-out worlds constrain precision; choosing a method by
  name does not validate its assumptions. A descriptive study with explicit
  limitations is an option, not an automatically equivalent confirmatory study.
- After non-protected paired nuisance estimation, approve the replication/seed
  count and feasibility/sample-size justification. Choose seeds before held-out
  access, not by favorable outcomes.
- Freeze the protocol and separately authorize controlled held-out evaluation.

The agent can prepare recommended settings, sensitivity calculations and resource
estimates before asking for this decision bundle. It cannot supply human approval,
define the user's meaningful effect or invent nuisance estimates. Baseline
completion, paired discordance and within-world dependence require non-protected
paired evidence; they are estimable inputs, not questions a human must guess.

## Safe tooling available now

`scripts/check_physical_design_readiness.py` inventories null/invalid choices and
nuisance inputs without reading experiment data. Even all-filled fields never
make it approve the study. `scripts/export_physical_campaign_outcomes.py` bridges
explicit scheduled assignments to the draft analyzer using independent v3-summary
audits. Assignments are a JSON list of `{ "episode_id": "...", "run_directory":
"..." }`. Request/summary identities must match the schedule. A recorded in-window
policy decision establishes instruction dispatch, not necessarily motion dispatch.
The protocol must accept this distinction before confirmatory use.

Unassigned scheduled episodes remain missing. Explicit pre-dispatch setup failures
have unknown endpoints. Ambiguous failures and interrupted measurements remain
unresolved; the tool refuses a standalone partial outcome list when any assigned
attempt cannot be audited. Stationary capture is not counted as a policy trial.

```sh
python3 scripts/check_physical_design_readiness.py
PYTHONPATH=src python3 scripts/export_physical_campaign_outcomes.py \
  --manifest /path/to/schedule.json --assignments /path/to/assignments.json \
  --report /path/to/new-export-report.json --outcomes-output /path/to/new-outcomes.json
```

These export tools do not launch a campaign or allow held-out partitions.
Fail-closed scheduled execution and interrupted-outcome auditing are now implemented
separately; see [executor contract](PHYSICAL_CAMPAIGN_EXECUTOR.md). They still need
genuine calibration, approved design and actual campaign evidence. Controlled
held-out authorization/evaluation and the final release remain outstanding.
