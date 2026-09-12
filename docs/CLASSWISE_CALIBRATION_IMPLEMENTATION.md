# Accepted P2 numerical implementation

`scripts/classwise_temperature_candidate.py` implements the numerical portion of
the P2 protocol accepted in Emmanuel's 12 September 2026 follow-up. The original
proposal bytes remain unchanged for historical hash verification.

Implemented and tested:

- Four separate class temperatures; exact deterministic grid including identity.
- Stable weighted binary cross-entropy and the prescribed numerical tie rule.
- Equal map, then represented view-group, then reviewed-emission weighting.
- Raw confidence retained; three half-open coverage bins with unchanged floors.
- Strict primary-expansion, human-binary, nonprotected partition admission.
- Leave-one-development-map-out fitting; every fold retained, including unfit folds.
- Weighted and unweighted Brier/ECE/MCE with ten equal-width evaluation bins.
- The exact conservative validation point-estimate admission comparisons.

The module is a pure numerical candidate, not an import path used by the live
provider, an authenticated human-label importer, a calibration release or a
deployment switch. Tests contain explicitly synthetic fixtures only. Human-type
fields are schema checks, not proof of authorship. Production inputs still need
the original journal/kit validator, hash-bound joins to exact observations,
prespecified map/view identities and complete scheduled-attempt accounting.

No-emission, ambiguous, infrastructure and unreviewable cases belong in the
attempt/exclusion ledger, not as binary calibration rows. The numerical module
refuses nonbinary labels rather than turning these cases into negatives. It cannot
certify full accounting from an emission table alone.

Still required before actual use: complete primary captures and genuine review;
bound ledger/export integration; development artifact creation with full source,
protocol, raw and label provenance; human development freeze; approved encrypted
validation release; validation analysis and human model acceptance; classwise
runtime consumption under a separate verified source pin. The historical pooled
calibration artifact is not silently repurposed as this classwise method.

No fitted Research 3 model, achieved calibration metric or downstream benefit is
claimed by the successful synthetic numerical tests.
