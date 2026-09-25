# Distance × lighting mechanism investigation

Status: DONE for diagnosis; new interaction experiment pending live verification.

- Symptom: Stage A produced no low-confidence entrance emissions.
- Evidence: all 58 emitted entrance observations have support exactly 1,
  with at least 72 pixels. All scores reproduce under the frozen provider.
- Root-cause hypothesis, confirmed for the recorded sample: lighting reduced
  colour agreement while close-range marker support remained saturated, keeping
  entrance scores above 0.5. Earlier distant nominal observations reduced support
  while colour agreement remained high. Neither experiment tested the joint
  reduction systematically.
- Implementation: new fixed 96-assignment distance × lighting exploratory panel,
  using development maps 1/6 and existing lighting assets. Midpoint/far poses,
  yaw offsets, lighting and seed are fixed before new capture outcomes. No
  provider change, confidence manipulation, old-panel extension or primary credit.
- Regression evidence: `tests/test_distance_lighting_pilot.py` checks recorded
  support saturation, score algebra, the complete factorial and capture-only scope.
- Limits: the algebra is conditional; distance can cause nondetection or
  unreviewability. No claim of negative-label coverage or calibration follows.
- Related: `docs/CALIBRATION_FEASIBILITY_INTERPRETATION_20260922.md` and
  `docs/REDESIGN_STAGE_A_RESULTS_20260923.md` preserve the prior failed candidates.
