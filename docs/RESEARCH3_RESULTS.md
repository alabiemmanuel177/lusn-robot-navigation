# Research 3 evidence report

Updated 8 September 2026. Research 3 is not yet a completed live comparative study.

## Authorized held-out graph campaign

The authorized create-once campaign produced 240 records: six routes on three test
maps, eight conditions, five systems and one seed. The raw campaign and every record
passed SHA-256 verification. Independent matrix checks found 240 unique run IDs,
48 complete five-system blocks, and identical eight-condition coverage per route.
The protected graph partition has now been accessed; it must not be described as
sealed or reused for tuning followed by another confirmatory claim.

| System | Episodes | Instruction completions | Critical failures |
| --- | ---: | ---: | ---: |
| B1 | 48 | 48 | 0 |
| B2 | 48 | 36 | 12 |
| B4 | 48 | 36 | 12 |
| B5 | 48 | 36 | 12 |
| B6 | 48 | 48 | 0 |

B6 minus B2 completion is +25 percentage points, with a hierarchical bootstrap
95% interval of +12.5 to +37.5 points. Critical failure difference is -25 points,
with an interval of -37.5 to -12.5 points (5,000 resamples; analysis seed 303).
These intervals describe the authored graph cases, with only three map clusters and
one execution seed. B1 also completes every case; these results do not demonstrate
that B6 improves completion over B1. B4 and B5 match B2 on these aggregate outcomes.

Artifacts:

- `reports/graph_heldout_v1.0.jsonl`, SHA-256 `432380ae41f3f605c23bf953f5172780a1656c5f50df5565e051757d1a2c73fe`.
- `reports/research3_graph_heldout_analysis_v1.0.json`, SHA-256 `75d14233d909b19c9e38ce646d6c82ebd1226360b99e33849ae46988038e03e0`.

The analysis and campaign configuration declare protocol 1.1, while raw episode
records declare 1.0. This metadata inconsistency is retained and disclosed; the
original evidence has not been rewritten. The graph observations are authored
fixtures, not deployed detector observations or Gazebo performance measurements.

## Live integration evidence and measurement limitations

The existing non-protected campaign records 14 terminal outcomes: five Nav2
successes and nine monitor-driven abstentions. All 14 consumed frozen Research 2
predictions. Its sidecars contain 483 predictor decisions and 13 alarms, including
decisions during teardown; these counts are not restricted to robot motion.

The live adapter used by v2 sets collision and wrong-goal fields to false, equates
instruction completion with Nav2 success, and records planned distance rather than
distance travelled. The v2 runner checks a separate collision monitor while waiting,
but never calls its `start()` method, so it does not accumulate active-episode
measurements. It also raises on collision or timeout without a terminal summary; the
campaign analyzer rejects collision episodes. Consequently the reported zero
collisions cannot establish an unbiased collision rate. All initial actions were
`inspect`, which currently dispatches a terminal navigation goal rather than a
distinct inspection viewpoint. Route eligibility uses a catalogue risk prior.

These facts limit the campaign to integration evidence. The immutable v2 records
and their analysis are preserved; this report qualifies their interpretation.

## Measurement repair verification, 8 September

The updated runner activates and stops the Research 1 ground-truth/contact monitor,
uses measured distance and final goal error, retains collisions/timeouts as terminal
trials, and bounds prediction counts by simulated episode timestamps. New summaries
use `research3-live-summary/v2`. Unmeasured semantic instruction completion and
wrong-goal identity are explicitly null. The older adapter sidecars and v1 campaign
analyzer remain unsuitable for estimating these research metrics.

Two isolated, non-protected development pilots verified the runner change:

- `reports/live_episodes/r3-measurement-dev00-v1/summary.json`: 247 ground-truth
  samples, 2.8149 m travelled, 0.1877 m final goal error, seven in-window predictions,
  measured navigation success under the declared 0.35 m position tolerance.
- `reports/live_episodes/r3-measurement-timeout-v1/summary.json`: deliberate 0.1 s
  wall-time limit, three ground-truth samples, timeout retained as a failed trial,
  no prediction observed. This is a timeout-path test, not a performance sample.

The planner now has an independent 0.25 s monitor freshness watchdog, rejects
future-dated timestamps, and invalidates malformed monitor input. An isolated ROS
timer test verified that stale data triggers abstention without incoming messages.
This checks publication of the stop decision; it does not independently measure
physical stopping distance. The watchdog uses ROS time and does not address a
stalled simulation clock. All 68 Python tests passed; modified ROS Python sources
compiled. These repairs do not retroactively validate the old campaign.

## Remaining work

1. Complete semantic outcome measurement and campaign analysis for v2 summaries;
   verify collision handling with contact evidence and retain raw trajectory evidence.
   Travelled distance, positional goal checks, timeout retention and in-window
   prediction counts are implemented and pilot-tested as described above.
2. Validate distinct inspection behavior and live risk/freshness handling before
   claiming the full guarded policy is evaluated in Gazebo.
3. Freeze a live comparative protocol and run the required systems and instruction
   conditions. The current live campaign contains only truthful B6 instructions.
4. Supply held-out scene and semantic-route catalogues for live evaluation. The
   Research 1 provider currently contains six development and three validation
   catalogues and no test catalogues. Graph access authorization does not supply
   these missing assets. Any new live test design must disclose prior graph access.
5. Archive the exact consumed Research 2 and Research 3 source snapshots and model
   assets for a reproducible release; existing worktrees are dirty.

Items 1–3 are implementation and experimental work, not a request for more human
landmark labels. The completed human review and frozen calibration remain usable.
