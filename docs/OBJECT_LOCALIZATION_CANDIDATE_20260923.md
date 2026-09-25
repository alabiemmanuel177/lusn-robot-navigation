# Catalogue-blind object localization candidate: fixed offline feasibility

Candidate only, under the authorized R3-only redesign. Preserve the marker
baseline, all historical results, Research 1/2 and scientific admission gates.

Model: Google's OWLv2 base-patch16 ensemble, exact revision
`57beb61adb5abda3de4a9796bc35ae60bc4b9802`, safetensors only, no remote code.
Official references: https://huggingface.co/google/owlv2-base-patch16-ensemble
and https://huggingface.co/docs/transformers/model_doc/owlv2 . This family returns
text-conditioned image boxes and scores; that does not establish performance in
these simulated scenes. A separate CPU-only environment pins torch 2.8.0+cpu,
torchvision 0.23.0+cpu and transformers 4.57.1. Archive dependency versions.

Before inference, fix 24 scheduled source slots: every sixth assignment (indices
0,6,...,138) in the complete original 144-row Stage A audit. Keep any original
infrastructure failures as unavailable source slots; do not substitute frames.
Use all intact selected full RGB images, including original nondetections. Do
not inspect labels, protected worlds or validation outcomes. Sampling was
catalogue-directed historically; candidate inference is not given catalogue
colours, old detections, pixels, categories, target IDs or coordinates.

Use the same six text prompts already fixed in `catalogue_blind_regions.py`.
Retain full raw logits and normalized predicted boxes. For display only, apply
the library's score threshold 0.1 with no outcome-based adjustment, NMS tuning
or per-class thresholds. Retain overlapping outputs and label indices; do not
quietly pick the observation nearest a known target. Exact model/input/source
hashes must verify before inference. Fixed budget, no retries or early stopping.

Run serially, CPU-only, one thread, low priority, checking existing hardware
guards before each image. Record wall time and counts; these are engineering
measurements, not achieved accuracy. No download of private research data or
upload of any source images to a model service is needed.

Output candidate image boxes with uncalibrated detector scores. Keep entity ID,
map pose and joint correctness probability null. A predicted box is not a human-
verified object identity or metric reference point. The separate association
candidate only accepts localized inputs and preserves all same-class references
within the fixed radius; multiple candidates remain ambiguous, not nearest-ID
truth. Depth support, projection uncertainty and the parent doorway/subtype
ontology still need an explicit contract before runtime integration.

No frames from this exploratory exercise enter fitting or primary quotas. Do not
request bulk human labels or claim calibration simply because boxes exist.
