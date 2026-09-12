# Physical-world detector validation preparation

This is stage 2 preparation, not a detector validation result or a request for
human review. The original calibration does not establish coverage in these new
worlds. No old labels, confidence freeze, or protected review data are reused here.

## Three retained development pilots

The offline auditor `scripts/prepare_physical_detector_review.py` verifies retained
media hashes, scopes every run by map ID/hash and scene/profile hashes, deduplicates
repeated decision candidates, and demands exact observation/RGB timestamps.
It creates its diagnostic manifest once and never produces labels or a review UI.

| Run suffix | RGB-D frames | Unique observation IDs | Exact RGB matches |
| --- | ---: | ---: | ---: |
| dev10-v1 | 0 | 0 | 0 |
| dev10-v2 | 5 | 0 | 0 |
| dev10-v3 | 5 | 278 | 0 |

The v3 IDs comprise 15 claimed chairs, 127 claimed laboratory entrances and 136
claimed office entrances. These are neither verified objects nor independent
viewpoints. Only one of five frames in each of v2/v3 has retained map TF. Camera
diagnostics were exhausted before the detector started. Decision snapshots also
omit the pixel/depth localization needed to show what the detector actually saw.
Consequently all three pilots are **not reviewable for detector correctness**.
Nearest-frame matching, ground-truth object projection, or a sphere-only review
would not repair this association gap.

## Capture repair and remaining gates

The R1 provider already supports a create-once `review_log` containing observation
IDs, exact RGB timestamps, detector pixel/depth, probability and pending/null human
verdicts. Use that interface without changing Research 1 sources. Pair it with the
Research 3 capture's opt-in `observation_triggered=True`: it waits for observations,
retains only an exact RGB timestamp match, bounded synchronized depth, CameraInfo,
TF/error metadata and triggering observation metadata. Buffers and sample count
are bounded. Missing matches are reported; the recorder does not substitute nearby
RGB frames. This is diagnostic sampling, not a complete coverage dataset.

Before asking a person to review anything:

1. Join raw provider review rows to exact retained media, verify hashes and the
   actual detector pixel, and reject missing/ambiguous matches. Capture optical
   calibration and TF at the image time, with explicit failures.
2. Render full frames and a contextual zoom with an unambiguous detector marker.
   Visually audit every offered item; the auditor here deliberately does not
   certify that a newly captured item is review-ready.
3. Prespecify development/validation map and class strata, viewpoints, lighting,
   occlusion, distances and confidence sampling. The base-r010 palette is scoped
   to that map; do not silently transfer it to the other thirteen non-protected
   maps. Freeze detector configuration before validation collection.
4. Retain naturally correct and incorrect predictions classwise, including
   same-colour confusers and natural non-landmarks with context. Report missing
   strata honestly; synthetic sphere challenges alone do not establish natural
   error prevalence. Do not manufacture human verdicts or cherry-pick confidence.
5. Independently annotate eligible objects in sampled full frames to measure
   missed detections/recall. Observation-triggered positive frames alone cannot
   measure false negatives; include a prespecified observation-independent sample.
6. Separate semantic identity, stable-instance association, position error and
   confidence calibration. Doorways and entrance types must be visually decidable;
   plain coloured plaques do not alone establish office versus laboratory identity.
   If still ambiguous, retain an unreviewable verdict instead of forcing a label.
7. Keep held-out assets out of review/tuning. Only after non-protected collection
   and genuine human review should calibration be fitted/frozen and the revised
   experiment protocol signed off. Do not reinterpret historical pilot failures.

Example diagnostic audit (output must not already exist):

```sh
python3 scripts/prepare_physical_detector_review.py \
  --run reports/physical_live_episodes/r3-stage1-physical-dev10-v3 \
  --output /tmp/physical_detector_review_preparation.json
```

No ROS/Gazebo process is launched by the preparation script or its tests. Existing
Research 1/2 assets and all historical evidence remain untouched.

## Exact provider/media join implemented

The runner also supports `--capture-context`, separately or together with
`--capture-review`. It starts an independently named camera subscriber after
localization/provider readiness, immediately before instruction dispatch, and
retains at most 20 full RGB-D frames spaced by at least two simulated seconds in
`context_capture/`. Selection does not subscribe to or depend on detections.
Early episode termination and missing synchronization can yield fewer frames;
retain the summary and actual timestamps. This bounded engineering sample is
not yet the prespecified multi-world recall dataset. Independent object annotation
and detection matching are still required to calculate recall. The request pins
the capture implementation, launch file and resource guard hashes.

After a new `--capture-review` run, use:

```sh
python3 scripts/join_physical_review_capture.py --run reports/physical_live_episodes/NEW_RUN_ID --output /tmp/NEW_RUN_ID-exact-join.json
```

The output is create-once and not authorized for human review. It verifies the
non-protected map split before opening capture data; demands one exact RGB frame
and matching triggering observation; checks provider identity/confidence, pixel
bounds, positive depth, RGB/depth byte hashes and layouts, bounded depth time
offset, and presence of camera geometry. Missing files or malformed structures
fail closed. It rejects duplicate observation IDs and previously labelled tasks.
Valid joins remain `awaiting_individual_visual_qa`; camera geometry presence does
not certify calibration accuracy. The conservative trigger check can reject other
detections from an already captured frame if their trigger metadata was not saved.
Rejected rows are retained, not silently dropped. No real new capture has passed
this gate yet. Eleven synthetic regression tests cover the join, not live accuracy.
