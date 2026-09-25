# Investigation report — entrance reference and live pose

Status: DONE_WITH_CONCERNS for engineering; scientific admission remains gated.

Symptom: visually plausible openings/signs repeatedly fail entrance metric review.
Root cause established in source: the reference is an offset original sign, not
the opening or readable board. Broad language boxes also cover entire scenes.

Changes: new R3-only OCR/context experiments, a separately versioned authored
reference-conversion candidate, and evaluator-only source-bound live pose runs.
All failed alternatives retained. Frozen detector/provider/capture files unchanged.
The investigation skill directed source tracing and fresh reproduction rather
than threshold relaxation. More than five new files were needed across separate
experiments; this expanded scope was disclosed before implementation.

Evidence: ten text hypotheses pass the geometric radius after the declared source
template conversion; no identity labels inferred. Eleven independently synchronized
RGB-D/TF/simulator comparisons across four live views pass 3 cm / 1 degree; 69
other context frames lack exact truth or TF and remain missing evidence. V1 failed
instrumentation retained; V2 corrects frame budget and domain reuse only.

Regression tests: `test_entrance_context_candidate.py`,
`test_bound_pose_preflight.py`, `test_readable_sign_reference_candidate.py` plus
existing pose and joint-score tests. Full regression reports are under reports/.

Next scientific dependency: decide whether the primary observation model may use
the authored readable-sign-to-reference template. Do not silently deploy it,
transfer historical labels, fit real joint probabilities, or open validation.
General-purpose entrance localization and a fitted joint model remain unproven.
See docs/STEPS123_CONTINUATION_20260924.md for exact scope and evidence.
