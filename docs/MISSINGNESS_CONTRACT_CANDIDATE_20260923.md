# D2-compatible missingness contract — offline candidate

The existing held-out audit correctly checks source/measurement provenance but
also requires every auxiliary endpoint to be boolean and infrastructure_failure
to be false. That is stricter than the accepted D2 instruction to retain unknown
outcomes and report best/worst sensitivity rather than delete incomplete cases.

`scripts/missingness_contract_candidate.py` implements the accounting distinction
without modifying or weakening the active held-out audit or capture sources:

- An explicit unknown auxiliary value does not erase independently measured
  ordered completion, including a known failure.
- Unknown primary arms remain in all scheduled pair denominators, bounded [0,1].
- Missing assignments stay in accounting and still block evidence completeness.
- Infrastructure failure needs an independently verified failure record; known
  values need recomputed measurement evidence. Bad integrity is a hard error,
  not a benign missingness designation.
- Compute B6−B5 bounds with equal world, then condition, then seed-pair weights.
  These identification/sensitivity bounds are not confidence intervals.

Only synthetic fixtures are used. Verification booleans are an interface contract
for a future independent auditor, not authentication and not a substitute for
checking raw bytes. The eventual adapter must derive them, never trust claims in
an imported return. No protected outcomes, files or labels are opened.

Activation requires the final frozen design's explicit missingness contract,
independent audit integration, source repinning, tests against authorized
nonprotected telemetry, and separate campaign/release admission. The candidate
does not approve a sample size, model, held-out execution or final release.
