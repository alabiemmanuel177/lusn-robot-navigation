# Fixed alternative-architecture feasibility

Development-only engineering, excluded from calibration and primary review.
Use original 24 source slots, 23 intact images, no replacements. This is an
adaptive development investigation after OWLv2's failure, not confirmatory evidence
or a fair benchmark of model accuracy. No validation or protected data access.

Grounding DINO tiny, official revision 25b0b43915cfc9e5dcb573031e99514eb7838d57,
safetensors only, local files, no remote code. Existing isolated CPU environment,
one thread, low priority and resource guard before each frame. Pin every model,
image, request, protocol and runner byte before execution.

Fixed ordered query string: `chair. doorway. laboratory entrance. office entrance.
sign. wall.` Box threshold strictly >0.1; token phrase threshold strictly >0.25.
No score transformation, prompt sweep, extra images or retried source failures.
Retain all raw token logits, predicted boxes and token IDs. No NMS or target-ID
filter. Preserve every phrase, including empty or mixed phrases; only exact
normalized full phrase matches receive one of the four navigation categories.
The broad `wall` query maps to background and is never a landmark hypothesis.

Raw max-token matching scores are not joint correctness probabilities. Higher
scores or more proposed boxes do not establish accuracy, calibration or meaningful
coverage. Do not select an admitted candidate based on these counts alone.
Reconstruct scores, boxes and token-derived labels from saved arrays before any
downstream use. Frozen R1/provider/camera/scene geometry is unchanged.

Sources: https://huggingface.co/IDEA-Research/grounding-dino-tiny/tree/25b0b43915cfc9e5dcb573031e99514eb7838d57
and https://huggingface.co/docs/transformers/v4.57.1/model_doc/grounding-dino
