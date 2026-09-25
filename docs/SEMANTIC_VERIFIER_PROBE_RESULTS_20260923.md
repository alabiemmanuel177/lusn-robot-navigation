# Frozen-model exploratory semantic probe — complete

This separate CPU-only engineering probe evaluated 119 retained Stage A emissions
using two fixed views and six fixed class/background prompts (238 score vectors).
No new observations, labels, protected inputs or calibration rows were created.

Checkpoint: OpenCLIP ViT-B-32, `laion2b_s34b_b79k`; safetensors SHA-256
`ac4f8c4b88af6d963118cbf40ad93176d092abbedfcb752601ae1866352656e6`.
The new R3-only virtual environment does not modify Research 1/2 environments.
Inference was offline, one CPU thread, low priority; elapsed model evaluation
18.79 seconds. All 238 relative softmax vectors independently reconstruct.
Exact prompts, input hashes, environment versions and output bindings are in
`reports/semantic_verifier_probe_20260923_v1/`.

## What it establishes

The model executes reproducibly on these images. It does not establish semantic
accuracy: no human correctness labels were available for this probe. Prompt
softmax is relative to the supplied alternatives, not a calibrated probability
that the claimed navigation observation is jointly correct.

With fixed local context crops, the claimed category is the highest prompt score
for 9/33 chair, 0/28 doorway, 20/29 laboratory and 19/29 office emissions.
These are **agreement counts, not accuracy**. Full-frame results differ markedly;
the images can contain several objects, and doorway/entrance meanings overlap.
Accordingly this probe does not justify a drop-in verifier, any multiplication
into the existing confidence formula, or automatic negative labels. No prompt
tuning or checkpoint selection was performed after seeing these outputs.

Any future semantic channel needs an explicitly scoped method and genuine human
validation, including repeated-instance and metric consistency evaluation. The
current frozen provider and calibrated model admission gates remain unchanged.
