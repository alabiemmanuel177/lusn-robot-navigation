# Proposed bounded Stage 1 live feasibility check

Status: ready for scope review, not approved for execution. This is not the
replacement primary-calibration amendment or final scientific experiment.

## Exact proposed scope

- Manifest: `reports/stage1_view_feasibility_20260921_v3.json`.
- SHA-256: `124d634d6656a86fa4a830b19e3a27a494cf28cef77ec183f78a4d33fe79c37f`.
- 80 unique development-only assignments: ten existing maps, four original
  assigned entity/category targets, two fixed views each, simulator seed 1.
- Each pair uses the farthest screened grid location compatible with both a
  target-facing orientation and a fixed +0.65 rad (odd map) or -0.65 rad (even map)
  yaw offset. Grid spacing is .25 m; ties use increasing x then y. Selection uses
  geometry, not future confidence, detections or human outcomes.
- Original scenes, provider computation, palette profiles, 2.0-rad horizontal FOV,
  confidence settings and calibration coverage requirements remain unchanged.
- One earliest retained synchronized frame per assignment with exact-frame
  processing acknowledgment. Capture timeout 90 seconds, outer owned-process
  timeout 600 seconds including startup/cleanup. No automatic retries or replacements.
- Execute serially, low priority, with the existing R3 exclusive lock and resource
  checks. Four-worker permission covers offline CPU work, not concurrent simulators.
- Before launch, bind active runtime/provider/profile hashes, verify compatibility
  with the existing exact-frame collector, and confirm current approved resource
  isolation conditions. Do not start while another workload leaves inadequate GPU
  headroom. Human approval alone does not override a failed technical admission.
- Do not read validation labels or access protected worlds. Do not fit a model.

## Completed offline checks

All 80 poses pass the existing conservative 0.30 m footprint check. Both camera
orientations pass the analytic 2-D wall-box ray screen. Wall rays omit the final
0.15 m around the landmark reference to avoid treating a surface-mounted target
as hidden by its own mounting surface. Non-wall objects, optical occlusion,
appearance and detector responses are NOT certified by these checks.

The first occupancy-ray report rejected chair-centre rays due to target occupancy;
it is preserved as a superseded screening experiment. The second report exposed
camera-offset wall crossings for nine oblique rays. Version 3 selects only by
geometry to satisfy both fixed orientations. No live outcomes informed these
revisions. Four synthetic wall-intersection tests pass.

In the grid screen, greatest target-facing chair ranges span 6.87–7.62 m and
doorway ranges 7.02–7.79 m; choosing a point compatible with both orientations can
shorten the final range. The previous pixel-area heuristic suggested greater
distances for reduced support, so distance alone is not a demonstrated solution.

## Outputs and fixed stopping rule

Account for every assignment as captured, nondetection, ambiguous, infrastructure
failure or not started. Record full frames/context, exact assigned emissions, raw
confidence, pixel support, depth, processing completion and resource evidence.
Complete the fixed schedule unless infrastructure/resource safeguards halt it;
never stop early or add trials because a desired confidence/error quota is reached.
Retain failed and unstarted entries. Resuming after a fault must preserve the
original manifest, IDs and completed records; no silent replacement.

These are **design-only feasibility observations**, excluded from calibration
fitting, primary negative quotas and certification. Automated checks cannot assert
that an association is correct or incorrect; human review remains necessary for
any correctness claim. No large new labeling request is implied by this test.

The resulting report must say which confidence regions were actually exercised,
whether usable evidence is obtainable, and whether the proposed conditions plausibly
support a new primary study. If the evidence still fails to support such a design,
report that result. Do not automatically schedule another increasingly difficult
wave. Return for an explicit choice about scientific scope or a revised approach.

## Decision requested

Authorize or decline this exact bounded development-only feasibility scope.
Approval does not approve its unseen results, a new calibration model, a revised
primary collection budget, lowered coverage floors or any protected campaign.
After this feasibility check, the actual primary amendment remains a separate
decision with its distribution, budget and validation separation specified.
