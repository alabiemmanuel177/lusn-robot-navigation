# Investigation report: four-class readiness

Status: DONE_WITH_CONCERNS — engineering readiness complete; no scientific model
or calibration admission. See docs/FOUR_CLASS_PERCEPTION_READINESS_20260924.md.

Authorization: user explicitly approved the authored sign-layout approach and
requested completion of four-class perception readiness. Recorded verbatim in
reports/world_specific_method_approval_20260924.json. Do not ask for that same
scope decision again or reinterpret it as human observation labels/model approval.

Symptoms/root causes:
- Small prior panel aliased chair views toward one off-centre angle.
- Even centred chair boxes included background depth. Gap clustering remained
  fragile when continuous samples connected chair and background ranges.
- Immediate zero-timeout TF lookup raced image arrival in fresh captures.

Changes/evidence:
- Complete 144-slot panel plus a fixed 80-slot ten-development-map panel.
- Separate v3 0.10 m supported near-depth band; all 40 broad map/class geometry
  checks pass. Fresh measured-TF captures support all four classes.
- Two repeated-entrance views show two same-class in-radius instance candidates
  in 12 LAB and 12 OFFICE frames; no verified human identity claim.
- Fixed-delay, frozen-frame collector: 20/20 exact TF, five exact independent
  truth comparisons pass. Old missing frames and failed alternatives preserved.
- Strict development adapter; runtime replay and independent association checks
  pass across 300 integrated frames and 849 hypotheses. Frozen v8 unchanged.
- Full suite 1,227 passed, 1 skipped. All owned jobs/processes finished.

The investigation skill drove full source/data tracing and fresh-view verification,
which caught the gap-based estimator's misleading broad-panel-only success.

Limits: geometry checks are necessary, not identity accuracy. No repeated-chair
live validation (one chair/world); repeated doorway simultaneous localization did
not pass. Runtime model inference was fresh-capture replay, not a moving robot
ROS publisher. No fitted joint model, coverage certification or held-out result.
Next step is an exact reviewed score-learning protocol and new genuine labels,
not another approval of the already accepted sign-layout prior.
