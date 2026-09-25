# Debug report: calibration freeze/release admission

- Symptom: historical failed-coverage output invited human freeze despite null
  class temperatures; evaluator expected status `approved`, but the accepted
  sealing workflow requires `approved_development_model_frozen`.
- Root cause: a generic next-action template ignored numerical eligibility, and
  independently implemented gate checks drifted between workflow stages.
- Fix: `scripts/fit_expansion_calibration.py` now requires coverage, exact class
  temperatures on the accepted grid, clean export blockers and development-only
  provenance before inviting freeze or accessing validation labels. Canonical
  human gate status, timezone and model/protocol hashes are checked first.
- Evidence: synthetic regression fixtures first failed without the new helpers;
  focused tests passed after the fix. Entrypoint tests prove a blocked candidate
  cannot reach the label loader and a correctly bound synthetic gate can reach
  the sentinel loader. The actual historical candidate remains ineligible.
- Regression: `tests/test_expansion_freeze_admission.py`; related encryption and
  classwise-temperature tests pass. Full suite at this checkpoint: 986 passed,
  one skipped, one pre-existing synthetic camera numerical warning.
- Related: protocol acceptance is not fitted-model approval. Historical files,
  human labels, encrypted returns, keys and protected evaluation were not changed
  or opened. Test approvals are synthetic and never written as production grants.
- Status: DONE for software admission; scientific calibration remains blocked.
