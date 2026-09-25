# R3-only catalogue-blind visual evidence candidate v1

Authorized direction: Emmanuel's follow-up authorizes the recommended R3-only
method redesign and packet publication. It is not an observation label, admission
of this model, validation release or approval of unseen results. Original provider,
core snapshot, Research 1/2, calibration floors and protected gates remain intact.

## Fixed offline experiment

Use all 141 intact RGB frames from the completed 144-attempt Stage A panel,
including old-provider nondetections; retain its three infrastructure failures
in accounting. No camera view or frame is selected by model output. Earlier
development findings informed this exploratory design; it is not confirmation.
The camera poses themselves were catalogue-directed, so this tests catalogue-
blind **inference**, not an independently sampled visual dataset.

Each image provides its full frame and nine overlapping half-width/half-height
regions on a fixed 3×3 grid. Coordinates depend only on image dimensions—not
detector pixels, palette matches, expected categories, instance IDs or scene
catalogues. Use the already cached ViT-B-32 laion2b_s34b_b79k safetensors
checkpoint, its unchanged learned logit scale, and the six unchanged prompts
listed in the candidate source. Pin exact model, input and source bytes before
inference. No fitting, prompt selection, score tuning, retries or early stopping.
Run offline, CPU-only, one thread, low priority with the existing resource guard.

Expected budget: 141 images × 10 regions = 1,410 fixed score vectors. This is
existing development evidence reuse, not new primary/live/validation collection.
Missing/corrupt evidence fails the audit rather than silently reducing the panel.

## Observation meaning and downstream separation

Output `research3-visual-region-evidence-candidate/v1`, not
`semantic-observation/v1`. A region classifier does not locate an object merely
because it assigns a prompt score to a crop. Keep `object_localized=false`,
`entity_id=null`, `map_pose=null`, `calibration_eligible=false` and
`runtime_admitted=false`. Do not project a crop centre and call it landmark pose.
Do not copy the catalogue's category or identity into the visual prediction.

The prompt softmax is relative visual evidence, not the joint probability that
category, instance and metric pose are correct. Background/sign results are not
fabricated perception failures or human negative labels. Doorway and entrance
prompts overlap semantically; report that ambiguity, do not force a new ontology
by inspecting which interpretation best meets coverage.

## Required subsequent implementation

Before a runtime semantic observation is admissible, an independent object
localizer must supply supported image extent/depth evidence, projection must
carry measurement uncertainty, and association must expose unresolved instances
rather than borrowing the expected identity. Define the parent doorway versus
entrance-subtype semantics and joint-confidence meaning prospectively. Keep this
candidate alongside the immutable marker baseline; never silently replace it.

This run verifies a catalogue-blind data path and measures output behaviour only.
No correctness, localization accuracy, calibration or navigation benefit can be
estimated without the corresponding evidence and genuine review. The next gate
is a complete object-localization/association candidate contract, not another
bulk human labeling request for these region scores.
