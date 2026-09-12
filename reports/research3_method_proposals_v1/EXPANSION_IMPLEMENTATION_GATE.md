# Expansion implementation audit: source approval still required

The 560-attempt plan is not executable with the frozen collector unchanged.
This is a newly verified implementation/protocol mismatch, not a missing human
label and not grounds to weaken the accepted coverage criteria.

## Evidence

`scripts/physical_perception_capture.py`, `PhysicalPerceptionCapture._pair`,
intersects buffered RGB timestamps with pending semantic observations and, when
configured, filters by target category. Its untriggered path uses the latest RGB
timestamp. Neither path implements the amendment's earliest synchronized frame
followed by exact prespecified entity selection with retained nondetections.
The existing tests intentionally assert that no observation consumes no frame.

`scripts/run_physical_episode.py` constructs that collector before localization
settles, then starts the provider later. An untriggered replacement therefore
needs an explicit readiness arm, not just flipping the old mode flag.

The accepted amendment retains the current source snapshot. Its exact hash is
`4eb51067c9d067954f4c0264e904993137d1be8e50f49401fc08870c8069056c`.
The snapshot validator still passes after this work. All original pinned R3 files
and provider/build bytes remain unchanged. A new sampling module was initially
placed under the snapshot's recursive core tree, detected by the source guard,
and moved to the candidate scripts directory before any execution. No frozen
manifest was rewritten to hide the addition.

## Implemented candidates, not active replacements

- `scripts/expansion_sampling.py`: deterministic earliest available synchronized
  pair, exact assigned entity/class selection without confidence ranking, explicit
  nondetection/ambiguous statuses, rejection of unfinished observation windows.
- `scripts/physical_expansion_capture_candidate.py`: unarmed by default; clears
  buffered images when armed; records a frame without waiting for a detection;
  retains late exact-frame observations. It is not wired into the frozen runner.
- `scripts/portable_physical_review.py`: can build an explicit primary expansion
  packet for one partition and variable item count. Refuses protected, mixed,
  pilot/diagnostic IDs and empty packets before evidence consolidation. The original
  published ZIP remains unchanged. New packet construction still requires actual
  captures, complete evidence and individual QA; none is invented here.

## Required approved source revision

Keep the provider score formula, palette, tolerance, association radius, camera
FOV, source geometry, route IDs and numeric coverage unchanged. Revise only the
capture orchestration/sampling source contract to implement the already approved
sampling semantics. Preserve the old source archive and labels as pilot-only.

After human approval of that scope, the agent must integrate the candidate,
record readiness/provider/TF evidence at arming, pin the new source set, and run
isolated synthetic and development live acceptance checks. It must retain bounded
observation-window completion evidence, overflow/conflict counts and timeout cases.
An empty truncated stream must not be classified as a genuine nondetection.
The current tests do not establish live ROS message ordering, readiness or complete
observation delivery. Do not launch the comparative campaign from these candidates.

Validation views can use separately bound per-view freezes; the old validation
checker permits one pose for each map/category in a freeze, not an unchecked list
of five poses. Development must complete first, with validation outcomes excluded
from fitting and model selection.

## Diagnostic asset status

All 40 same-colour sphere and 40 occluder candidate worlds exist. The independent
static audit v2 checks 80 sets of source/derivative hashes, unchanged original SDF
subtrees and non-world assets, no added collisions/plugins, and conservative screen
wall/ground clearance. All pass. Camera-facing screen rotations match the bound
pilot transforms. These are geometry checks, not rendered camera observations.

The occluder uses 20% of the projected convex silhouette of the provider marker box.
This is an explicit candidate definition, not 20% of an entire semantic doorway,
chair or entrance. The human asset review must accept that definition or request a
different target mask before the diagnostic condition is treated as finalized.
It must also inspect rendered context; no unseen-asset approval is inferred from
general acceptance of the treatment categories. Engineered diagnostics remain
excluded from primary negative quotas and calibration fitting.

## What is still not complete

Rendered asset preflight, approved active collector integration and source freeze,
the full expansion executor/lifecycle with real acceptance checks, new captures,
the actual consolidated observation kit, empirical calibration, sample-size
justification, comparative/held-out campaign and final analysis/release remain.
Some are engineering work after the source/asset decisions; they are not all human
tasks. This audit must not be used to claim that only human work remains or that
returning the current decision packet will automatically close the research.
