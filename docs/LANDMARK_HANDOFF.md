# Landmark producer handoff

Current physical-world work is summarized in [STATUS.md](STATUS.md). The new
readable-world capture/review workflow has separate evidence and must not inherit
calibration claims from the historical captures below. Downstream scientific
approval, calibration and the final physical campaign are not complete.

The historical provider handoff used Research 1 revision
`697a7bc86fd2eca62866c614ef7b26b5d810cf84` provides the opt-in producer at
`extensions/research3_landmark_bridge`. It publishes
`language_nav_interfaces/msg/SemanticObservation` on `/semantic_observations` using schema
version `semantic-observation/v1`.

The provider handoff was introduced at `70d87054f4fd002a23311983a03b9810a038add6`.
That historical pin is its descendant; the intervening commit changes publication
metadata only and leaves the provider subtree unchanged.

## Identity requirements

- `observation_id` is unique for one detection event and must remain unchanged during
  replay.
- `entity_id` identifies the same physical landmark across frames and revisits.
- `region_id` is a stable semantic region identifier used by the route catalogue.
- `sequence` is nondecreasing per `source`; multiple entities from one frame may share
  a sequence.
- `frame_id`, pose and covariance describe the landmark in a Research 1 TF frame.

Required deployed categories are `chair`, `door`, `doorway`, `glass_doors`, `sign`,
`laboratory_entrance`, and `office_entrance`. Chair observations used by the benchmark
also require a `color` attribute from the frozen ontology.

## Verified non-protected capture

Research 3 completed create-once live capture across all 14 provider route IDs and all
9 development/validation maps. The campaign manifest is
`reports/landmark_capture/campaign_manifest_v1.json`: 3,467 raw observations, 47 stable
entities, protected test data false, online ground truth false, and segmentation labels
false. Nine compact review-media bags contain RGB, depth, camera info, semantic
observations, TF, TF-static and clock.

The combined launch runs the unchanged provider under a multithreaded executor so image
processing cannot starve TF callbacks. A development-only camera-space palette profile
at `configs/landmark_capture_profile.yaml` compensates for headless Gazebo lighting; the
derived catalogues preserve every stable ID, region, pose and covariance.

Run another create-once non-protected capture with:

```bash
source scripts/ros_env.zsh
source /home/eao/risk-calibrated-nav/install/local_setup.zsh
source install/local_setup.zsh
python3 scripts/run_landmark_capture.py \
  --route-id dev_03_r0 --motion-seconds 6 --record-review-media
```

The runner revision-checks Research 1, refuses routes outside the provider's non-protected
plan, records per-file checksums, and writes bounded process logs and a summary. Direct
catalogue-derived viewpoints are available through `--view-entity`, `--view-side`, and
`--view-distance`; they do not use simulator labels or ground-truth localization.

## Manual build and launch

Build the bridge over the two existing workspaces:

```bash
source /opt/ros/jazzy/setup.zsh
source /home/eao/risk-calibrated-nav/install/local_setup.zsh
source /home/eao/lusn-robot-navigation/ros_ws/install/local_setup.zsh
cd /home/eao/risk-calibrated-nav
colcon build --base-paths extensions/research3_landmark_bridge --symlink-install
source install/local_setup.zsh
```

Generate a derivative world, launch Research 1 with its absolute path, then start the
Research 3 pipeline and create-once review log:

```bash
python3 scripts/make_landmark_world.py \
  --scene configs/landmark_bridge/scenes/dev_01.yaml \
  --output /tmp/dev_01-landmarks.sdf

ros2 launch simulation_worlds sim.launch.py \
  world:=dev_01 world_path:=/tmp/dev_01-landmarks.sdf

ros2 launch language_nav_bringup research1_landmarks.launch.py \
  scene:=/home/eao/lusn-robot-navigation/data/landmark_bridge/runtime_scenes/dev_01.yaml \
  review_log:=/home/eao/lusn-robot-navigation/data/landmark_bridge/dev_01-review.jsonl \
  color_tolerance:=18.0
```

These commands authorize development data collection only. They do not authorize a
protected test run.

## Semantic route catalogue

The ready catalogues are in Research 1 under
`configs/landmark_bridge/semantic_routes`. Validate any one with:

```bash
PYTHONPATH=src python3 scripts/validate_semantic_catalog.py \
  /home/eao/risk-calibrated-nav/configs/landmark_bridge/semantic_routes/dev_01.yaml
```

All nine catalogues currently pass. The validator resolves each `platform_route_id`
against Research 1's frozen route and map hash. It rejects evaluator-only fields,
duplicate route assignments, unresolved routes, placeholder region IDs and protected
catalogues unless explicitly authorized.

## Calibration sample format

The immutable review source is `data/landmark_bridge/human_review_queue_v1.jsonl`. The
editable worksheet is `data/landmark_bridge/human_review_queue_v1.reviewed.jsonl`, and
`reports/landmark_capture/review_index_v1.html` shows the 52 exact frames for its 60
tasks. For every row, a human must inspect the marked pixel and set only:

- `review_status` to `human_verified`;
- `reviewer_id` to a non-empty stable identifier; and
- `correct` to `1` only when category, stable entity association, and pose are acceptable,
  otherwise `0`.

Validate and freeze only after review:

```bash
python3 scripts/validate_landmark_human_review.py

python3 /home/eao/risk-calibrated-nav/scripts/finalize_landmark_calibration_samples.py \
  --reviewed data/landmark_bridge/human_review_queue_v1.reviewed.jsonl \
  --output data/landmark_bridge/validation_calibration_samples_v1.jsonl

PYTHONPATH=src python3 scripts/freeze_landmark_calibration.py \
  --input data/landmark_bridge/validation_calibration_samples_v1.jsonl \
  --output configs/landmark_calibration_v1.json \
  --partition validation --minimum-samples 20
```

The final exporter emits one JSON object per labelled landmark observation:

```json
{
  "schema_version": "landmark-calibration-sample/v1",
  "observation_id": "obs-0001",
  "partition": "validation",
  "category": "chair",
  "probability": 0.82,
  "correct": 1
}
```

Use detection correctness only; do not include navigation oracle routes, future
observations or grounding answers. The validator requires at least 20 human-verified
validation rows and both correct/incorrect outcomes. The freeze rejects protected data,
records the exact input SHA-256, fits temperature and isotonic models, and never
overwrites a differing artifact.

## v2 validation-expansion queue

The v1 review completed with every validation detection marked correct, which blocks
the freeze (calibration fitting needs both outcomes). `scripts/build_landmark_review_queue_v2.py`
created a create-once expansion queue of 40 additional validation-partition observations
(8 per category: the 5 lowest-probability plus a 3-point quantile spread, selection
label-independent) from the same verified media-backed captures, excluding every v1
observation. Frames were exported by `scripts/export_landmark_review_frames_v2.py`
(`review_index_v2.html`, `review_frame_manifest_v2.json`, `campaign_manifest_v2.json`).

Review the v2 worksheet `data/landmark_bridge/human_review_queue_v2.reviewed.jsonl`
the same way (the interactive tool `scripts/serve_landmark_review.py --worksheet v2`
records verdicts in place), then validate v1+v2 jointly and freeze from the
concatenation of both reviewed worksheets:

```bash
python3 scripts/validate_landmark_human_review_v2.py

cat data/landmark_bridge/human_review_queue_v1.reviewed.jsonl \
    data/landmark_bridge/human_review_queue_v2.reviewed.jsonl \
    > data/landmark_bridge/human_review_queue_combined.reviewed.jsonl

python3 /home/eao/risk-calibrated-nav/scripts/finalize_landmark_calibration_samples.py \
  --reviewed data/landmark_bridge/human_review_queue_combined.reviewed.jsonl \
  --output data/landmark_bridge/validation_calibration_samples_v1.jsonl

PYTHONPATH=src python3 scripts/freeze_landmark_calibration.py \
  --input data/landmark_bridge/validation_calibration_samples_v1.jsonl \
  --output configs/landmark_calibration_v1.json \
  --partition validation --minimum-samples 20
```

The completed v2 review also yielded no incorrect labels: v1+v2 now contain 100
human-verified rows, including 65/65 correct validation detections. Reviewing more of
the same post-association pool would repeat a structurally filtered true-positive set,
so no further natural-pool expansion was made.

## v5 sphere-identity challenge queue

The v3 rectangular-swatch queue is rejected because both the distractors and provider
landmarks appeared as rectangles/cuboids, making semantic object identity unjudgeable.
Its source, frames and submitted labels remain preserved for audit but are explicitly
excluded from validation and calibration. The v4 sphere pilot is also excluded: a
pre-review visual audit found the sign sphere clipped at the image edge.

The final create-once v5 campaign lowers each coloured sphere into full view and uses a
0.60 m neutral screen, retaining substantially more floor, wall, opening and neighboring
geometry. The seven selected capture bags contain 136 observations. The label-independent
worksheet selects the minimum-, median- and maximum-probability target observation for
each of chair, door, doorway, glass doors, sign, laboratory entrance and office entrance.
All 21 exact frames passed a pre-review visual audit for curved-sphere identity and wider
scene context. Checksums are in `review_frame_manifest_v5.json`; capture and exclusion
provenance is in `campaign_manifest_v5.json`.

Review only the marked detection and judge object identity, not colour. A coloured sphere
is not a door, chair, doorway, sign or entrance. The challenge itself supplies no saved
verdict; a human must still record whether the claimed semantic category is correct.

```bash
python3 scripts/serve_landmark_review.py --worksheet v5

python3 scripts/validate_landmark_human_review_v5.py

source scripts/ros_env.zsh
source /home/eao/risk-calibrated-nav/install/local_setup.zsh
source install/local_setup.zsh
python3 scripts/finalize_landmark_calibration_v5.py
```

The final command refuses pending, non-human, one-class, protected, duplicated or
mutated evidence. On success it create-once writes the combined v1+v2+v5 reviewed rows,
normalized samples and `configs/landmark_calibration_v1.json`. It refuses v3 and v4.
Because the v5 conditions deliberately enrich difficult cases, the resulting fit is
challenge-augmented and must not be presented as an estimate of natural deployment
error prevalence.

The review and freeze completed on 31 August 2026. Every one of the 21 v5 crosshairs was
independently inspected and confirmed to lie on the coloured sphere; pixel-level checks
matched the intended sphere palette. All were recorded as incorrect by reviewer `eao`.
The joint validator passes with 121/121 human-verified rows and 86 validation samples:
65 correct natural detections and 21 incorrect challenge detections. The create-once
artifact is `configs/landmark_calibration_v1.json`; final checksums and exclusions are in
`reports/landmark_capture/calibration_freeze_v1.json`.

## Runtime join

The high-level planner consumes:

- `/language_hypotheses`;
- `/belief_graph` derived from the landmark observations;
- `/language_nav/route_proposals` (`semantic-route-proposal/v1`);
- `/language_nav/route_eligibility` (`route-eligibility/v1`).

It publishes `/language_nav/decision`. A route can be committed only when the semantic
evidence is present, traversability was observed, Nav2 marked the route eligible and
the combined risk is below the hard guard. Research 2 may remain unavailable during
this Research 3-only development path; its score stays explicitly unavailable rather
than being presented as monitor evidence.
