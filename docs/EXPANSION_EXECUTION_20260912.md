# Expansion execution record — 12 September 2026

Emmanuel asked for every outstanding item to be completed in one pass. This
record states what was actually done, what the evidence shows, and which
decisions still belong to him. Nothing here manufactures a label, freezes a
model, or authorizes protected execution.

## 1. Rendering camera model (new finding)

Rendering the first diagnostic candidate showed the v1 occluder screen well
below and left of the projected marker-box strip it was meant to cover. The
cause is not the projection arithmetic: v1 placed screens using the
localization transform published for `camera_depth_frame`, which comes from
the state publisher's URDF. The Gazebo RGB-D sensor that renders pixels is
composed from the robot SDF instead: camera link (0.069, -0.047, 0.107) plus
sensor (0.064, -0.047, 0.107) plus the 0.010 m spawn height, so the optical
centre sits at (0.133, -0.094, 0.224) m in the base frame with zero pitch. The
transform used by v1 is about 0.06 m behind, 0.05 m left and 0.11 m below it.

`scripts/expansion_camera_model.py` encodes this model and verifies it from
retained depth samples: floor pixels give the camera height, wall faces give
its horizontal position. `reports/rendering_camera_verification_20260912_v1.json`
checks all 40 same-session control renders; every one agrees with the model
within 7 mm. The provider is not modified. Its back-projected observation
positions inherit the same offset; that is a property of the frozen detector
and is measured, not corrected, by the calibration study.

## 2. Diagnostic candidates: v1 evidence and v2 rebuild

Batch 1 (`reports/expansion_diagnostic_render_batch1_20260912_v1`) rendered the
40 unmodified control views plus eight v1 candidates through the owned runner
using a new `--diagnostic-derivative` mode. That mode launches the candidate
`world.sdf` over unchanged source assets after re-running the independent
static audit, so nothing in the frozen candidate directories is rewritten.
Control renders are pixel-identical to the bound 11 September pilot frames.

The v1 evidence packet (`packet_v1_evidence` in that directory) shows all four
rendered v1 occluders covering 0% of the projected marker box, and the v1 chair
sphere covering about 10% of the chair pixels from the bound viewpoint.
Entrance and doorway spheres were clear.

`scripts/prepare_expansion_diagnostics_v2.py` rebuilt all 80 candidates with
the verified camera. Rules kept from v1: same marker models, 20% of the
projected convex silhouette of the provider marker box, neutral visual-only
screen at 70% of the marker depth, same-colour visual-only sphere of radius
0.20 m, original SDF subtree and non-world assets unchanged. Changed: the
camera model, and a fixed ordered placement search for spheres that rejects
positions whose projected disc intersects the projected silhouette of the
target's own models, leaves the image, sits behind a wall, or touches the
target geometry. Ten chair spheres moved 0.6 m across the camera ray; the 30
entrance and doorway spheres kept their v1 positions. The independent static
audit v2 (`reports/calibration_expansion_diagnostic_static_audit_20260912_v3.json`)
passes all 80.

Batch 2 (`reports/expansion_diagnostic_render_batch2_20260912_v1`) rendered the
80 v2 candidates against the reused controls: 78 succeeded and all 78 pass the
agent preflight (rendered box coverage 0.174 to 0.203, median 0.183; every
sphere leaves 100% of the control target pixels unchanged and forms a separate
same-colour component). Two occluder renders (`r002 laboratory_entrance`,
`r009 chair`) failed for infrastructure reasons (stack exit, transform not
settling) and are queued for re-rendering after the collection chain releases
the simulator; their failure records are retained. Both re-rendered successfully on 14 September. The complete packet
`reports/expansion_diagnostic_asset_review_20260914_v2` (ZIP alongside,
manifest SHA-256 `6d21d134f964b81d6bdf337276ac75e2bcafbc43ceff1a348480b093ece7fb28`)
is the asset-review deliverable: all 80 candidates rendered and passing the
agent preflight (occluder box coverage 0.174 to 0.203), `index.html` with
control, candidate-with-overlays and changed-pixel images, `rendered_audit.json`
with the pixel measurements, `manifest.json` and `DECISIONS.template.json`.
234 of its 240 images are byte-identical to the earlier 78-candidate packet;
only the six images for the two re-rendered occluders are new. Decisions must
bind to the v2 manifest hash.

Agent preflight thresholds (not acceptance criteria): occluder rendered box
coverage within 0.06 of 0.20, screen visible, at most half the changed pixels
outside the box, target still mostly unchanged; sphere visible as a separate
same-colour component, at least 97% of the control target pixels unchanged.
Measurements are same-session control-versus-candidate pixel differences at
the identical pose. Palette masks on shaded entrance lintels are fragile, so
occlusion and retention are measured as rendered change over control pixels.

**Human decision:** open the packet, judge each candidate accept/revise/reject,
state whether the marker-box occluder definition is accepted, and return
`DECISIONS.json` bound to `manifest.json.sha256`. Diagnostic collection of a
candidate is refused by the runner without an accepting decision.

## 3. Primary collection executor

`scripts/run_expansion_collection.py` runs one partition of the accepted
560-row plan (hash-bound to Emmanuel's amendment decision) serially through
the owned runner with a pinned instrumentation snapshot. Snapshot v4 pinned the
revised runner; the first attempts under it failed on exact-stamp transform
races (the collector looked up the camera transform immediately, and the
provider wrapper's own transform buffer could start after the frame stamp, so
its lookup failed "into the past"). Snapshot v6 bounded both waits; snapshot
v7 (`reports/expansion_instrumentation_snapshot_20260914_v7`) adds a positive
readiness file written by the wrapper once its buffer holds the camera-to-map
chain at the current simulated time, and the runner arms only after it
exists. Snapshot changes on a resumed schedule are recorded in the lifecycle
directory, and every attempt's request pins the snapshot it ran under. Each
attempt uses its candidate ID as its immutable run ID,
the exact prespecified entity, camera profile hash, FOV 2.0, seed and pose
from the plan. Research 2 idleness and host headroom are checked before every
attempt; the exclusive execution lock is held for the whole partition. One
new-ID retry is permitted only for an infrastructure failure with no provider
outcome (never armed, provider never started, provider raised before any
detection outcome, or only the collector's own transform record missing); the
original is retained and listed. Launches the runner rejected before creating
a directory retained nothing and are listed separately, not counted as attempts. The schedule halts only after three consecutive
infrastructure failures, never on outcome. `report.json` accounts for every
scheduled attempt by status (emitted, nondetection, ambiguous emissions,
infrastructure failure).

Validation capture was previously impossible: the runner allowed the
expansion pin only for development, and the frozen-view checker accepts one
pose per map and class. The runner now admits validation only with the
complete development report (hash-verified against every attempt's request)
and a per-view v2 camera freeze derived from the pinned engineering freeze,
one file per validation view, as the accepted gate text permits.

## 4. Review kits

`scripts/build_expansion_review_kit.py` turns a complete collection report into
the portable reviewer kit: automated per-observation image checks
(`scripts/expansion_machine_visual_qa.py`, which decodes each exact frame and
verifies the reported pixel lies on a palette blob of the task's class), a
prespecified sampling policy selecting exactly the assigned entity's emission
per emitted attempt, the consolidated inventory, an attempt-accounting file
listing every nondetection and failure, and the kit ZIP. Non-selected
emissions in the same frames stay retained but are not review targets.

Development and validation kits are separate. Return only the sealed
validation return; keep the key private until the freeze gate.

## 5. Calibration pipeline (ready, unrun)

`scripts/fit_expansion_calibration.py develop` validates a returned development
review against its kit, exports the human binary labels through the existing
exporter, binds each to its map and view group, checks the accepted coverage
floors, fits the four class temperatures on development only, runs
leave-one-map-out diagnostics, and writes a development candidate plus a
freeze proposal with all source, protocol, plan, snapshot and return hashes.
`validate` evaluates the frozen temperatures on the opened validation return
without refitting and applies the accepted point-estimate screen. Both wait on
human labels; no synthetic or pilot rows are admitted.

## 6. Power and feasibility

`scripts/world_paired_power_simulation.py` implements the declared-grid
simulation the P1 decision requires: world logit random effect from the ICC,
paired Bernoulli outcomes with prescribed margins and discordance, equal
condition and seed weights, exact sign-flip test. Grids for six held-out
worlds with 1, 2, 4 and 8 seeds are in `reports/world_paired_power_grid_20260912_*.json`
(2,000 replications per point, Monte Carlo seed 20260912).

| Worlds | Seeds per world | Max power at +0.10 | Grid points at or above 0.80 |
| --- | --- | --- | --- |
| 6 | 1 | 0.05 | 0 of 72 |
| 6 | 2 | 0.31 | 0 of 72 |
| 6 | 4 | 0.83 | 6 of 72 (discordance 0.1, ICC 0 only) |
| 6 | 8 | 0.996 | 12 of 72 (discordance 0.1, ICC up to 0.1) |

With one seed the six-world test cannot reach the target under any grid
value: per-world differences move in steps of 1/8 and rejection needs all six
signs to agree. The null size is conservative (at most 0.03) because of ties.
Four or more seeds per world reach 0.80 only when paired discordance is about
0.10 and worlds barely differ.

**Empirical nuisance estimates (14 September).** The 160 paired B5/B6
development episodes (`scripts/run_feasibility_navigation.py`,
`reports/feasibility_navigation_20260912_v1/report.json`; one simulator seed,
no calibration artifact, matching the retained engineering smoke
configuration) measured 159 episodes and one infrastructure failure. Seven
measured episodes have no valid ordered-completion outcome, leaving 72
complete pairs over all ten worlds.

| Quantity | Value |
| --- | ---: |
| B5 ordered completion (baseline) | 0.847 |
| B6 ordered completion | 0.736 |
| Mean paired difference B6 − B5 | −0.111 |
| Paired discordance | 0.139 |
| World ICC of paired differences | −0.13 (treated as 0) |
| Collisions, timeouts | 0, 0 |

The difference is concentrated in one condition: under attribute corruption
B5 completed 9 of 10 worlds and B6 none, because B6 abstains; under topology
corruption neither completed; the other six conditions differ by at most one
world. This is engineering evidence from truthful-instruction development
worlds with uncalibrated confidence, not a held-out or confirmatory result,
and it does not establish the sign of the eventual contrast.

Bound simulation at the empirical point (baseline 0.85, discordance 0.14,
ICC 0; `reports/world_paired_power_bound_20260914_seeds*.json`, estimates in
`reports/feasibility_nuisance_20260914_v1.json`):

| Seeds per world | Power at +0.10 | Null size |
| --- | ---: | ---: |
| 1 | 0.05 | 0.002 |
| 2 | 0.22 | 0.004 |
| 4 | 0.60 | 0.009 |
| 8 | 0.90 | 0.011 |

At six held-out worlds the +0.10 target reaches 0.80 power only with about
eight simulator seeds per world (48 world-seed blocks, 8 conditions and 5
systems each: 1,920 episodes), and the test remains conservative. Emmanuel
decides final sample size and confirmatory versus descriptive status from
these numbers; a descriptive designation before held-out access is the
fallback the P1 decision names.

## 6a. Collection outcome (14 September)

Development: 400 of 400 accounted, 399 emitted, 0 nondetections, 1
infrastructure failure after its retry. Two completed attempts lost their
retained bytes when the host restarted (07:38 UTC) before the page cache was
flushed; they are listed as unrecoverable in the report and kit accounting,
excluded from review, and not re-run under the fixed budget. The development
review kit holds 397 targets covering every map and class.

## 7. What remains with Emmanuel

1. Diagnostic asset decision on the v2 packet.
2. Development review in the portable kit; validation review returned sealed.
3. Freeze approval, then key release; then the validation screen outcome.
4. Sample-size and inference designation from the feasibility estimates.
5. Explicit authorization of the nonprotected campaign, then the protected
   scope separately.

Source is committed on `main`; large capture media stay untracked and are
hash-pinned from the JSON evidence files.
