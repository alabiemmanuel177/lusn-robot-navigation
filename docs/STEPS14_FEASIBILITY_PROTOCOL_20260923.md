# Steps 1–4: bounded investigation protocol

Fixed before these new checks. Engineering only, not primary collection or human
review. No validation labels, validation captures, or reserved worlds are opened.
Keep the original 24-slot/23-frame development panel, including the historical
failure. No replacements, model downloads, or live ROS changes.

## Camera check

Use hash-checked depth, RGB, source-world manifest, and original capture request.
Run the existing floor/wall depth-plane consistency check, retaining every row.
Report all-axis translation support separately from the existing height-only
acceptance flag. Translation consistency requires x, y and height residuals each
at most 0.03 m. Wall assignment is model-initialized and conditioned on proximity;
this is a consistency check, not independent six-degree-of-freedom ground truth.
Report the discrepancy from recorded nominal TF. Do not silently correct or
promote the old transform or interpret agreement as landmark pose accuracy.

## Detector diagnostic

Hypothesis: long compound text queries may suppress doorway matching. Compare
the original stored outputs with exactly one short-query panel, using unchanged
model bytes and the original strict score >0.1 threshold. Fixed queries:
`a photo of a chair`, `a photo of a doorway`, `a photo of a laboratory entrance`,
`a photo of an office entrance`, `a photo of a sign`, `a photo of a wall`.
All images and queries are retained. No prompt search, best-frame selection,
threshold adjustment, winner promotion or correctness labels follow. Save raw
logits/boxes. Report both argmax display outputs and all-query maxima/counts so
query competition is distinguishable from absent threshold support.

This diagnostic is informed by the model's text-conditioned interface, not a
claim that simpler prompts are better:
https://huggingface.co/docs/transformers/model_doc/owlv2

## Score and protocol checks

Scores describe box/text matching, not the conjunction of correct category,
physical instance and reference-point location. Reconstruct raw bins and establish
whether the already accepted no-intercept temperature family can support the
candidate. Positive temperature cannot change which side of 0.5 a score occupies.
No labels, fitted joint model or new score definition will be fabricated.

If class, localization or score feasibility fails, prepare a clearly blocked
primary-protocol specification and exact remaining decisions, not a purported
scientific freeze. Preserve Coverage v2 and existing delayed-release requirements.
Full primary execution requires a supported observation method and prospective
approval of the exact new design; generic implementation authority is not approval
of unseen data or results.
