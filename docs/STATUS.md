# Research 3 status and handoff

Last verified: 31 August 2026

## Gate status

| Gate | State |
| --- | --- |
| Benchmark and split integrity | Passed. Twenty base instructions, three paraphrases each, eight corruption conditions, twelve disjoint map IDs. |
| Research 1 map/route alignment | Passed. 32 development and 18 validation routes verify; all Research 3 development/validation references resolve. |
| Core implementation | Passed. Parsing, grounding, belief updates, guarded policies, immutable logging, calibration utilities and evaluation metrics are implemented. |
| ROS 2 build and messaging | Passed. Five packages build; instruction, observation, belief, decision, route and monitor contracts are generated. |
| Live ROS core smoke | Passed. Instruction ID propagates through belief and safe abstention; duplicate observations are idempotent. |
| Synthetic full-contract ROS smoke | Passed. Landmark + terminal + route proposal + Nav2 eligibility produced a guarded B6 commit to `dev_00_r0`. Not research evidence. |
| Graph development campaign | Passed as engineering evidence: 400 episodes on 6 maps. |
| Graph validation campaign | Passed as engineering evidence: 160 episodes on 3 maps. |
| Landmark-instance perception | Provider delivered at Research 1 revision `70d8705`: opt-in RGB-D producer, 9 non-protected scene catalogues, 9 semantic-route catalogues, 14 routes and 98 stable instances. Combined six-package ROS build/test and all catalogue validators pass. |
| Live Gazebo language navigation | READY FOR NON-PROTECTED INTEGRATION SMOKE. Derivative visual-only worlds and the combined launch exist; no live result is claimed yet. |
| Research 3 calibration freeze | Blocked only by real live detections and human review. Graph fixture or catalogue truth is ineligible. |
| Research 2 combined monitor | In progress externally; `failure-monitor/v1` is not available. |
| Protected held-out execution | Sealed. CLI requires explicit authorization and no held-out run has been produced here. |

## Current deterministic result

The checksum-verified analysis is `reports/research3_graph_analysis_v1.0.json`. Across
the deterministic development campaign, B6 minus B2 completion difference is `+0.25`
with a route-level hierarchical bootstrap interval `[0.1591, 0.3523]`; critical-risk
difference is `-0.25` with interval `[-0.3472, -0.1625]`. Validation reproduces the
point differences (`+0.25` and `-0.25`) with wider intervals. The difference occurs in
attribute-corruption and missing-landmark fixtures.

These numbers demonstrate expected policy logic in the authored graph world. They do
not estimate performance on Research 1 Gazebo scenes or a physical robot.

## Remaining inputs that cannot be fabricated

1. Human review of real development/validation output from the delivered landmark bridge,
   including both correct and incorrect detections for calibration.
2. Live rosbag capture and non-protected Gazebo integration evidence using the delivered
   derivative worlds and semantic catalogues.
3. Research 2's reviewed thresholds, validated predictor and `failure-monitor/v1`
   publisher for the combined experiment.

Research 3-only Gazebo development/validation can now begin while Research 2 continues.
Item 3 is needed only for the planned combined monitor results. None of these remaining
evidence-producing steps may be replaced by synthetic labels or graph fixtures.
