# Debug report: known ordered failures became unknown

- Symptom: the generic campaign analyzer erased an independently measured false
  instruction-completion value if terminal identity was absent.
- Root cause: a terminal-identity prerequisite was applied to both establishing
  success and preserving established failure. The pinned live scorer correctly
  marks a trajectory missing required gates as false without terminal identity.
- Reproduction: the new measured-failure test returned None instead of False
  before the change. A separate infrastructure-failure fixture still returned
  None, as required.
- Fix: a narrow condition in `scripts/analyze_physical_campaign.py` preserves
  false under an otherwise measured, non-infrastructure record. Unknown terminal
  identity still cannot establish success. Unknown collision/timeout and genuine
  infrastructure failures remain conservative; the live scorer is unchanged.
- Evidence: 986 tests passed, one skipped, one existing numerical warning. All
  159 existing nonprotected measured summaries subsequently reproduced from
  telemetry with exact pinned evaluator sources. Thirteen had false completion
  with absent terminal identity. Corrected generic analysis agrees with separately
  calculated scheduled-cohort bounds [−.1625,−.0625].
- Regression: `tests/test_physical_campaign_analysis.py` and separate development
  audit/recomputation modules. No historical summary or raw telemetry was rewritten.
- Related concern: final release gating still rejects any unknown auxiliary
  endpoint. Ledger B10 records the need to align that gate with a frozen missingness
  policy, without bypassing it now.
- Status: DONE for analyzer correction; final protocol alignment remains open.
