# R3 redesign: completed offline engineering evidence

Emmanuel authorized R3-only redesign and packet publication. The original marker
provider remains the baseline; no Research 1/2 source, protected outcome or
validation label was changed/read. The previously requested private GitHub
packets are published and their remote SHA-256 digests match local bytes.

## Catalogue-blind region path

All 141 intact Stage A development images were evaluated in ten fixed regions,
including images with no old-provider emission. All 1,410 outputs independently
reconstruct. Runtime: 91.34 seconds, one CPU thread. Top prompts: background
1,005; sign 233; office entrance 73; laboratory entrance 86; chair 13; doorway 0.
These are prompt counts, not accuracy or detected-object counts. Camera sampling
was historically catalogue-directed, although inference used RGB alone.

## Object localization path

The exact pinned OWLv2 checkpoint processed all 23 intact images in a fixed
24-source-slot panel; the historical missing slot was retained without replacement.
It returned 93 display-threshold boxes: 31 laboratory entrance, 43 office entrance,
9 background, 9 chair, 1 sign, 0 doorway. Five images had no display-threshold box.
All display outputs independently reconstruct from the retained raw arrays.
Mean per-frame time was 12.13 seconds on one CPU thread.

Eighteen raw predicted boxes extend beyond the real image boundary, which is
retained explicitly; the model pads inputs to a square. No box clipping, duplicate
suppression or selection by known catalogue proximity was applied to those
results. Multiple boxes need not be independent objects. There are no human
accuracy labels, verified instance associations or map-frame pose estimates.

Inspecting every query's retained scores—not just argmax displays—finds maximum
scores of 0.3191 (chair), 0.0541 (doorway), 0.2065 (laboratory entrance) and 0.2468
(office entrance). Thus missing doorway displays are not merely an argmax tie
with entrance prompts. These are detector matching scores, not an admitted joint
observation confidence channel. Do not silently rescale them or relax coverage
to declare calibration complete. The existing temperature-only family cannot
move p<0.5 above 0.5; no fitted model or primary gate follows from this probe.

## Implemented and tested next-layer contracts

- Depth helper: a fixed central predicted-box region gives visible-surface support
  and descriptive scatter, never a catalogue-centre guarantee or calibrated
  covariance. Missing/ambiguous depth stays explicit.
- Association helper: preassigned IDs and unlocalized inputs are rejected;
  competing same-class references remain ambiguous instead of nearest-ID truth.
- Candidate outputs remain separate from `semantic-observation/v1`; the live
  provider, calibration and campaign were not changed.

Full regression after the RGB/association implementation: 1,138 passed, one
skipped. Seven subsequent depth/postprocessing-focused tests passed. The original
v8 snapshot continues to validate at SHA-256
`6b7bc9e5dd4f5289af88ee4524db3544d277eeeb6a0685177b12c128ef6fb49a`.

## Remaining engineering and scientific work

Neither candidate is ready for primary calibration or bulk human review. Complete
the sensor-transform-bound box/depth/association integration and define the
doorway/entrance hierarchy plus observation confidence meaning before a fresh
runtime feasibility panel. Independent object localisation, visual class evidence,
geometric association and joint correctness probability must not be collapsed
into one unvalidated number. These development steps are covered by the redesign
authorization; a generic new "proceed" approval is not needed.

Only actual review can supply human labels, and actual calibrated-model/validation
results remain subject to their scientific gates. No research-completion claim,
automatic negative label or new review workload is created by this report.
