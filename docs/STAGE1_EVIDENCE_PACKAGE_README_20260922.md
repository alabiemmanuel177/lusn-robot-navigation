# Engineering evidence package — not a calibration review request

This package records the completed fixed 80-view development feasibility panel:
49 assigned detections, 26 nondetections and five retained infrastructure failures.
It is not a scientific-release certificate, an approved calibrated model, or a
request to supply 49 labels in order to bypass missing calibration coverage.

Start with:

1. `docs/STAGE1_FEASIBILITY_RESULTS_20260922.md` for the results and limitations.
2. `docs/RESEARCH3_BLOCKER_LEDGER_20260922.md` for remaining scientific gates.
3. `reports/stage1_two_workers_20260922_v4/summary.json` for all 80 assignments.
4. `reports/stage1_frame_previews_20260922_v1/index.json` and its 75 PNG files for
   optional full-scene inspection. These are verified lossless RGB conversions:
   no crop, added crosshair, recolouring or synthetic image generation. They are
   not semantic-correctness attestations. Missing previews correspond to the five
   infrastructure failures; raw partial evidence remains archived where retained.
5. `reports/stage1_design_score_support_20260922_v1.json` for reconstruction of all
   49 assigned scores from the frozen detector. Numerical pose consistency is not
   proof of category or instance correctness.

## Verify without running simulations

After obtaining the archive and verifier, use Python 3:

```sh
python3 scripts/verify_stage1_bundle.py /path/to/research3_stage1_evidence_20260922_v2.zip --expected-sha256 DIGEST_FROM_VERIFICATION_REPORT
```

The verifier uses only the Python standard library and its bundled
`scripts/verify_physical_release.py` helper. It does not extract files, access
the network, decrypt reviews, or launch ROS. It checks the outer digest when
provided, exact member inventory, safe names and each member's size/SHA-256.
Checksums establish byte consistency, not scientific validity or human identity.

The archive preserves source snapshots v7/v8, exact capture request/evidence
records, execution plans and ten development-world assets. The original v7
resource-guard source is reconstructed by reversing the single approved change
and verified against its historical hash; this provenance is explicit in the
manifest. Other source files match snapshot v8, and provider/build hashes are
retained. R1/R2/ROS and system dependencies are not bundled: this is an evidence
archive, not a complete installable simulator environment. Original capture
request paths are retained for provenance, so full pipeline replay needs the
recorded environment/path configuration, not just ZIP extraction.

No protected worlds, validation labels, validation key or plaintext validation
return is included. No human labels or approvals have been generated.

## Current decision boundary

The panel still has no low-confidence doorway or entrance emissions. Labeling
these images cannot fill empty confidence bins. The existing primary development
data also lack negative outcomes. Resolve the prospective design/scope question
before requesting another primary collection or a large human review.
