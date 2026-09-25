# Offline semantic verifier probe — no runtime or calibration admission

The current provider detects catalogue colour signatures, not learned category
identity. This probe investigates a separate semantic-evidence channel without
editing that provider or altering any confidence already recorded.

Use the locally cached LAION CLIP ViT-B/32 checkpoint (revision
`1a25a446712ba5ee05982a381eed697ef9b435cf`), with its actual file SHA-256 recorded
before inference. Run OpenCLIP 3.2.0 in a new R3-only CPU environment, one thread,
low priority. Do not modify or borrow-write another project's environment. No
remote model code, checkpoint download, GPU work, training or temperature tuning.

Fixed input panel: all 119 assigned emissions of completed design-only Stage A,
not selected for confidence/correctness. Fixed prompt bank: chair, doorway,
laboratory entrance, office entrance, sign and background. Each receives the same
two views: a letterboxed full frame and a 256-pixel detector-centred context crop.
The claimed category and catalogue are not text inputs to the model. Raw frames
remain intact; preprocessing is only for inference and is explicitly recorded.

Output normalized image/text cosine similarities and relative prompt softmax
using the checkpoint's unchanged learned logit scale. These are **not calibrated
probabilities of correctness**, binary human verdicts, ground truth or additional
calibration rows. A prompt mismatch is disagreement with the colour provider,
not a proven perception error. Full-frame ranking can reflect another visible
object; proposal-centred evaluation is not independent detection/localization.
No product of verifier and provider scores is admitted as a joint probability.

New hypotheses need a prospective method, human correctness evidence and the
existing calibration/model/campaign gates before runtime integration. This probe
does not retroactively change the failed Stage A or current fixed live pilot.

Primary technical references: [OpenCLIP implementation](https://github.com/mlfoundations/open_clip/tree/v3.2.0),
[checkpoint model card](https://huggingface.co/laion/CLIP-ViT-B-32-laion2B-s34B-b79K),
[official CPU wheel version pairing](https://pytorch.org/get-started/previous-versions/#v280).
