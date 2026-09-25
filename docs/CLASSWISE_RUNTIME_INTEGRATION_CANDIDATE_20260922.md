# Classwise runtime integration: offline candidate, not activation

The accepted P2 fit has four temperatures. The current frozen provider loader
accepts `landmark-calibration/v1` with one pooled temperature; the live and
held-out bridges call that loader. Passing the classwise fit output directly is
not supported. Averaging the four temperatures or writing a misleading pooled
artifact would change the accepted method and is not a solution.

## Implemented offline preparation

`scripts/classwise_observation_adapter_candidate.py` maps an already-associated
raw `SemanticObservationContract` with the exact accepted P2 probability function.
It preserves pose, covariance, category, attributes, IDs, timestamps, sequence and
order; only confidence changes. Raw and mapped records plus the candidate model
digest are retained separately. There is no refit, label generation, ROS publisher,
runtime authorization, model approval or source-freeze change.

Tests cover all four classes, numerical endpoints, exact family/grid admission,
unsupported classes, nondetections, identity/provenance preservation, no mutation,
and compatibility with belief-store and observation-ledger duplicate protections.
The receipt/wrapper distinguishes a mapping from a raw input; future runtime must
also enforce a single application through channel separation. Extracting the
mapped contract and falsely calling it raw is not detectable from the unchanged
message schema alone.

## Required integration once an actual model is admitted

1. Keep the provider's temperature at 1, preserving raw scores and association
   ordering. Do not calibrate before spatial association or alter raw coverage bins.
2. Add an explicit R3-only mapping stage with separate raw and calibrated topics.
   All confidence-consuming nodes must receive exactly one selected channel.
   Mixing raw and mapped messages under one observation ID causes duplicate/race
   rejection in current consumers and must be prohibited in launch tests.
3. Bind the final deployment artifact to the exact development model, protocol,
   human freeze, unchanged-temperature validation result and human model admission.
   Validate these before subscriptions start; unavailable/invalid models fail
   closed. A digest or numerical mapping alone is not admission.
4. Declare each baseline's calibrated/raw channel in the frozen comparative
   design. B5 and B6 must use the identical admitted mapping to isolate their
   decision-policy difference. Do not silently change B1/B2/B4 configurations.
5. Extend R3 launch/admission consumers and source snapshots under a scoped
   revision. Preserve Research 1 provider code, physical geometry and historical
   raw evidence. The existing pooled-schema held-out admission checks must not be
   bypassed or tricked with a schema rename.
6. Run synthetic end-to-end ROS message/launch tests, isolated nonprotected live
   preflight, raw/mapped count and ID parity, single-application and latency/freshness
   checks, then pin exact deployment sources before any campaign.

Until these gates are satisfied, this is a tested numerical/consumer-contract
candidate only. No real fitted model currently exists to deploy. Ledger B11
records the remaining integration and source-approval dependency.
