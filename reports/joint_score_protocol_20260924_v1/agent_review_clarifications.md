# Agent clarifications — separate from the reviewer's verbatim decisions

All seven individual decisions are recorded as accept. The reviewer has not yet
supplied the separate overall_decision field. No execution or unseen-result
approval is inferred. Reviewer rationales have not been rewritten.

The hash-bound protocol, rather than shorthand in a rationale, specifies:

- P2 uses 1,001 log-spaced temperatures **plus exact T=1** (1,002 distinct
  candidates), not just the log-spaced grid.
- Delayed encrypted custody prevents the fitting workflow from accessing labels
  without the withheld key; it cannot guarantee no leakage through other channels
  or eliminate all human bias. Blinding scores reduces one source of review bias.
- Coverage/accounting and duplicate controls reduce specified selection and
  repetition risks; they do not establish that empirical metrics are free of all
  bias. Seeds do not establish independent samples; S and C share development maps.
- Matching/recognition scores must retain the exact pinned implementation's
  meaning. They are not established joint-correctness probabilities. A temperature
  has no separate distance/geometry input, though it may correct miscalibration
  already expressed through its scalar input; the stronger learner is not assured
  to succeed simply because it has additional features.
- The validation Brier/ECE/MCE screen compares temperature-calibrated joint scores
  against untempered joint scores. It does not, by itself, prove improvement over
  the old detector or establish downstream navigation benefit.
- Static pose/asset checks against the actual newly pinned execution inputs remain
  prelaunch gates, not completed checks implied by accepting the fixed budget.

These notes do not alter the proposal, schedule, review decisions or authority.

## Subsequent overall confirmation

The reviewer subsequently stated: "Yes i confirm overall accept". All seven
individual decisions and overall acceptance are finalized in
`review_decision_CONVERSATION_FINAL.json`. The preceding pending-overall note
describes the state before that confirmation. Execution and release restrictions
remain unchanged. A pre-existing `review_decision.json` was not overwritten.
