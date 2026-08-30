# Landmark producer handoff

Everything downstream of landmark perception is ready. Research 1 revision
`70d87054f4fd002a23311983a03b9810a038add6` now provides the opt-in producer at
`extensions/research3_landmark_bridge`. It publishes
`language_nav_interfaces/msg/SemanticObservation` on `/semantic_observations` using schema
version `semantic-observation/v1`.

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

## Build and non-protected launch

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
  scene:=/home/eao/risk-calibrated-nav/configs/landmark_bridge/scenes/dev_01.yaml \
  review_log:=/home/eao/risk-calibrated-nav/data/landmark_bridge/dev_01-review.jsonl
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

Run the bridge with a create-once `review_log`, inspect the timestamp-matched camera
recording, and human-verify each row as documented in Research 1
`data/landmark_bridge/README.md`. The final exporter emits one JSON object per labelled
landmark observation:

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
observations or grounding answers. Freeze the artifact with:

```bash
PYTHONPATH=src python3 scripts/freeze_landmark_calibration.py \
  --input data/landmark_calibration.jsonl \
  --output configs/landmark_calibration_v1.json
```

The command requires unique observations and both correct/incorrect samples, rejects
protected data, records the exact input SHA-256, fits temperature and isotonic models,
and never overwrites a differing artifact.

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
