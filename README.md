# Language as an Uncertain Sensor for Robot Navigation

This repository is the executable research artefact for Protocol 1.0. Research 1's
Gazebo/Nav2 platform is complete and its frozen development and validation routes can
now be verified and loaded here. Deterministic topological graph-world evaluation
remains available for development. The same typed boundaries are implemented by
graph-world, ROS-message, rosbag replay, Nav2, and failure-monitor adapters. Nav2
remains the sole owner of path feasibility, collision checking, and motion.

## Run the first paired trace

```bash
PYTHONPATH=src python3 -m language_nav.benchmark.paired_trace
```

The trace compares a deterministic waypoint policy with the uncertainty-aware
policy on the same false-landmark instruction and observations. It writes no
protected evaluator labels into deployed inputs.

## Run checks

```bash
PYTHONPATH=src python3 -m pytest
```

## Build the benchmark

```bash
PYTHONPATH=src python3 scripts/build_benchmark_manifest.py
```

The generated evaluator bundle contains 20 base routes across 12 Research 1-aligned map
IDs, three protected paraphrases per route, all eight instruction conditions,
exact edit/environment manifests, and explicit ambiguous-grounding annotations.
The `deployed_variants` and `evaluator_only` namespaces are intentionally
separate.

## Run a paired graph-world campaign

```bash
PYTHONPATH=src python3 scripts/run_graph_campaign.py \
  --partition development \
  --routes 2 \
  --seeds 2 \
  --output reports/my_graph_smoke.jsonl
```

The output path is create-once. Each record has a checksum, the complete JSONL
file has a sidecar SHA-256 checksum, and rerunning against an existing path is
rejected. The summary always reports completion and critical-failure rates
together. These graph-world numbers are development diagnostics, not evidence
for confirmatory robot-navigation claims.

The completed non-protected deterministic campaigns and their checksum-verified paired
analysis are recorded in `reports/graph_development_v1.0.jsonl`,
`reports/graph_validation_v1.0.jsonl`, and
`reports/research3_graph_analysis_v1.0.json`. See `docs/STATUS.md` for the exact gate
state and `docs/protocol_amendment_v1.1.md` for the pre-execution map reconciliation.

## Implemented scope

- deterministic parsing of movement, landmark, turn, topology, and terminal clauses;
- top-K semantic grounding with a language-only predicted hypothesis;
- capped log-odds evidence updates and clause reliability;
- graph corridors, junctions, landmarks, visibility, blocked edges, and guarded traversal;
- B1, B2, B4, B5, and B6 system variants on one deployable input contract;
- seeded corruptions and protected instruction/split manifests;
- inspect, ignore, commit, and abstain decisions behind an explicit route guard;
- immutable paired logging, replay equivalence, and intervention budgets;
- temperature and isotonic calibration, reliability/risk-coverage curves,
  SPL, route fidelity, paired risk difference, contradiction recovery, and
  hierarchical bootstrap;
- ROS 2 messages, nodes, QoS, launch scaffolding, and graph/live/replay adapters;
- evaluator-only field denylisting and regression tests.

## ROS 2 integration boundary

The ROS workspace is under `ros_ws/src`. Source the repository environment so the
core Python package is visible and CycloneDDS uses the host-local unicast settings
validated by Research 1, then build and test it on ROS 2 Jazzy:

```bash
source scripts/ros_env.zsh
cd ros_ws
colcon build --symlink-install
source install/local_setup.zsh
colcon test
colcon test-result --verbose
```

The planner deliberately emits `stop_and_abstain` until a semantic target has a Nav2
route-eligibility result. Research 2 must still implement `failure-monitor/v1`. The
canonical repository paths, completion status, and roles are recorded in
`configs/research_dependencies.yaml`.

The landmark provider is now available at pinned Research 1 revision `70d8705`. The
ready-to-ingest contract, catalogue validation, human-review calibration format, and
runtime topics are documented in `docs/LANDMARK_HANDOFF.md`. This is provider readiness,
not live Gazebo evidence or a completed calibration freeze.

## Research 1 compatibility audit

```bash
PYTHONPATH=src python3 scripts/check_research1_integration.py
```

The audit independently verifies Research 1's frozen development/validation map
hashes and clean-S0 route status. It denies protected test routes unless a caller
explicitly opts in. It now verifies the separate landmark producer and its non-protected
scene/semantic catalogues and exits successfully when the pinned provider is intact.

## Remaining external blockers

- **Landmark evidence:** the Research 1 bridge, derivative worlds and catalogues now exist.
  Research 3 still needs non-protected live capture, human-reviewed correct/incorrect
  detections, and a frozen confidence-calibration artifact. Catalogue truth and graph
  fixture confidence cannot substitute for that evidence.
- **Research 2 monitor:** combined-system experiments still require
  `failure-monitor/v1`, frozen operating thresholds and recovery triggers.
- **Live evidence:** landmark-confidence calibration, rosbag2 paired campaigns and the
  final freeze require observations from the delivered provider plus the still-pending
  Research 2 monitor for combined-system claims.

Research 1's maps, Nav2 execution behavior and Gazebo platform are no longer listed as
blockers. Nothing in the existing graph-world campaign should be presented as a Gazebo
or physical-robot result.
