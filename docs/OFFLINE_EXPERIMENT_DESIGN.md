# Offline physical experiment design review

Status: draft, not frozen; no simulator was started for this review and no
protected world, label or outcome was opened. This supplements the physical
protocol draft rather than retroactively changing historical evidence.

## Simulator seed: supported mechanism and missing integration

The locally installed Gazebo Harmonic CLI supports `gz sim --seed N`.
This was checked using `gz sim --help`, the installed Ruby parser
`/opt/ros/jazzy/opt/gz_sim_vendor/lib/ruby/gz/cmdsim8.rb` (integer parsing and
passing the value to the server), and installed `ServerConfig.hh` (unsigned
integer API; zero denotes unspecified). Our explicit contract therefore accepts
1 through 4294967295 and rejects zero, booleans, fractions and negatives.

Research 1's `src/simulation_worlds/launch/sim.launch.py` has a fixed-seed
docstring but its actual Gazebo argv contains no `--seed` and it declares no seed
launch argument. Appending `simulation_seed:=N` to that provider launch would not
establish seed control. Its files remain unchanged.

`scripts/physical_seed_preflight.py` hashes the inspected source and emits a safe
argv list without executing it. Research 3's new owned launch
`physical_sim.launch.py` accepts `world_path`, `simulation_seed`, start pose,
`research1_root` and `tb3_root`. It invokes Gazebo directly with `--seed N` and
reuses provider robot xacro and bridge resources read-only. It also starts robot
spawn and robot-state publishing, preserving the small provider launch topology.
The runner must set isolated ROS and Gazebo domains, enforce Research 2 resource
guards, retain actual argv and source/asset hashes, and validate a development
run before claiming runtime seed acceptance. No environment variable is assumed
to substitute for the CLI seed. Launch plumbing is not bitwise reproducibility:
ROS scheduling, GPU rendering, model nondeterminism and independently seeded
plugins can still vary. Report these limits and test repeated-seed variation.

The instruction seed `s0`, execution-order seed 0, and simulator seed are different
controls. Seed 1 is only a proposed engineering smoke seed. No confirmatory seed
list or replication count is approved by this draft. Pair each chosen simulator
seed across all five systems for a world-condition block; restart complete runtime
state each episode. Do not choose seeds based on favorable protected outcomes.

## Paired estimand and replication proposal

Use independently measured ordered-instruction completion as a candidate primary
endpoint, not Nav2 status alone. For each system contrast, compute the paired
completion difference within world, condition and simulator seed; average equally
over prespecified conditions and replications within each world, then equally over
worlds. This world-average paired risk difference prevents repeated episodes from
being mistaken for independent buildings. Seed repetitions improve within-world
precision but do not increase the number of independent world clusters.

Candidate contrasts are B6 minus each of B1, B2, B4 and B5. The primary contrast,
multiple-comparison policy and inference method must be chosen before freeze.
Keep development and validation diagnostics separate from held-out estimates.
Six reserved held-out worlds are few clusters: avoid unqualified normal/Wald or
large-sample cluster-robust claims. World-level paired estimates and intervals
should be shown individually. Any cluster bootstrap is descriptive with such few
worlds; a sign-flip/permutation test additionally needs defensible exchangeability
assumptions and should not be called exact merely because execution was randomized.

Retain collision, timeout, terminal identity, goal error, path length, inspection
and abstention as distinct secondary endpoints. Never score unknown measurement
as success or zero collision. Report attempted/dispatched/evaluable/unknown and
infrastructure counts, paired-block completeness and best/worst outcome bounds
for unknowns using the same world weighting. Complete-case estimates are a
disclosed sensitivity analysis, not silent removal of unfavorable episodes.
Freeze the missingness estimand and treatment of pre-dispatch versus post-dispatch
infrastructure failures before execution. Supplemental reruns never replace originals.

One simulator replication would entail 560 non-protected and a separately gated
240 held-out episodes. Multiplying seeds multiplies episodes, not independent
worlds. A defensible power analysis needs a target meaningful difference, target
power, alpha, baseline success, paired discordance, within-world dependence and
replication count. These remain null in the draft, not invented approvals.
Estimate nuisance quantities from non-protected pilots only, show sensitivity
across plausible dependence/effect scenarios, and decide whether the available
six held-out clusters support the intended claim before freezing. New independent
world families or changed sample sizes require an explicit design decision.

## Ambiguous-reference construct decision

Preserve the original ambiguous-reference text variant and label its actual
interpretation: **underspecified attribute in a single-anchor scene**, not
disambiguation between competing chair identities. Do not add distractor chairs,
change geometry or relabel old results silently. This limitation can remain in
the study if claims are correspondingly narrow. A claim about competing-object
reference resolution would require a deliberate new-world design decision,
separate asset validation and calibration coverage before freeze. No such
redesign or decision is made here.

## Offline checks

```sh
PYTHONPATH=src python3 scripts/physical_seed_preflight.py
PYTHONPATH=src pytest -q tests/test_physical_seed_preflight.py
```

The first command reports source support, not runtime reproducibility. The draft
configuration remains explicitly non-executable. No final protocol freeze or
held-out execution is authorized by these artifacts.
