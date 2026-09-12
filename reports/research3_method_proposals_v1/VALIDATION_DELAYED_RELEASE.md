# Validation encryption and delayed release

Emmanuel is the primary reviewer and there is no independent validation custodian.
To prevent the fitting workflow from reading validation labels early, the reviewer
encrypts the validation return on his own device and retains the key there until
the development model and calibration protocol are frozen and approved.

Hashes bind bytes; they do not conceal labels. This implementation uses AES-256-GCM
authenticated encryption, a fresh random key and 96-bit nonce per envelope, and
authenticated metadata. The library documents its key/nonce requirements and
tamper detection at https://cryptography.io/en/41.0.7/hazmat/primitives/aead/.

This is NOT a cryptographic time lock. Anyone possessing the key can decrypt by
other means, and the reviewer can still communicate results from memory. The
protection is that the agent does not possess the key before release, combined
with separate packages, documented withholding and a pinned development freeze.
It is not independent blinding, a trusted timestamp service or identity certification.

## Reviewer workflow when new validation evidence is ready

No new validation labels exist yet. Do not run this on the accepted pilot return.

1. Use the validation-only expansion kit and complete the unchanged three-dimension
   human review. Validate and export the ordinary return locally, without sending
   its plaintext, notes, verdict counts or coverage summary to the fitting agent.
2. Install the Python `cryptography` dependency if needed. The code was tested on
   the workstation with version 41.0.7; final portable environment pinning remains
   a release preparation step, not an assertion that all platforms were tested.
3. From the validation-kit directory, run:

   ```sh
   python3 seal_validation_review.py seal \
     --return-zip my-review-return.zip --kit-manifest kit_manifest.json \
     --key-file ../validation-review.key \
     --output ../validation-return.sealed.json
   ```

4. Send ONLY `validation-return.sealed.json`. Keep `validation-review.key`, the
   plaintext return and local review journal private on your device. Do not put
   the key in a Git repository, shared folder, message or returned archive. Back
   it up privately; if lost, the encrypted data cannot be recovered without the
   original plaintext. The tool does not delete your original review files.
5. After the development model/protocol are fixed, inspect their hash-bound freeze
   and approve the release gate. Only then transmit the key through the agreed
   private channel. Do not disclose validation feedback to influence the freeze.

The seal tool checks the validation-only kit/return hash binding, member names and
size limits. It does not replace the original kit's scientific review validator.
The key file is create-once with mode 0600 on the tested Linux system; this is not
a portable guarantee against every local account or backup service.

## Release gate and agent workflow

The human release record uses schema `research3-validation-release-gate/v1` and
requires:

- `status: approved_development_model_frozen`, `reviewer_type: human`, a real
  `approved_by` name and timezone-aware `approved_at`;
- `validation_used_for_fitting_or_selection: false`;
- exact `sealed_validation_sha256`, `development_model_sha256` and
  `calibration_protocol_sha256` values.

Those fields are a declared human attestation, not an independently authenticated
signature. Do not synthesize or backdate them. The gate does not approve final
calibration efficacy or authorize a campaign.

After release, the receiving researcher runs:

```sh
python3 seal_validation_review.py open \
  --sealed validation-return.sealed.json --key-file validation-review.key \
  --release-gate approved-release.json --development-model frozen-model.json \
  --calibration-protocol approved-calibration-protocol.json \
  --output released-validation-return.zip
```

The command checks scope and model/protocol/ciphertext bindings before decryption,
then authenticates the envelope. Revalidate the decrypted return against the same
validation kit before analysis. Preserve the encrypted original, release decision,
model/protocol pins and validation analysis; do not tune the frozen model afterward.

Synthetic tests exercise encryption round-trip, absent gate, changed model, wrong
key, tampered ciphertext with a recomputed outer hash, partition rejection, fresh
keys/nonces and create-once private files. No actual validation return was encrypted
or opened during implementation. The workflow still needs a real validation kit
and a controlled end-to-end review/release rehearsal before scientific use.
