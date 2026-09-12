# Campaign readiness — 8 September 2026

## Completed in this continuation

Ordered instruction scoring is implemented in `src/language_nav/evaluation/ordered.py`
and connected to the runner through `--ordered-geometry`. It detects crossings of
directed, bounded passage gates in trajectory order and combines them with independent
terminal identity, collision and timeout outcomes. Merely reaching the destination,
crossing gates in reverse order, or passing outside an aperture does not pass. The
measurement record retains the annotation, and the analyzer independently recomputes
the score. Unverified/missing geometry yields an unknown outcome. Dataset-wide scoring
cannot be completed until the geometry annotations below are resolved.

The isolated live collision validation passed:
`reports/collision_validation/r3-contact-v1/report.json`. Gazebo produced an actual
robot/fixture collision after 0.5775 m of travel. Raw disqualifying contact pairs and
the ground-truth trajectory were retained; the Research 1 monitor counted one
collision. A temporary derivative world contained the test obstacle. No physical
robot, navigation campaign or frozen provider world was modified. This verifies the
simulator/contact-monitor path; terminal-record retention also has synthetic tests.

Held-out catalogue construction and validation are complete locally in
`configs/heldout_landmark_bridge_v1`: three scenes, three semantic-route catalogues,
six routes and 42 stable entities. Identity, map hash, occupancy and frozen route
association checks passed, along with an explicit test-partition JSON Schema
extension. `audit.json` records hashes and prior protected graph access. These are
visual catalogues; no protected live capture has run, and they do not certify physical
doorway topology. The existing runtime still defaults to non-protected use.

Two Research 1 source files were changed locally: the landmark core loader/validator
and catalogue builder now accept explicit `allow_protected=True`. Default test-scene
loading remains denied. Human-label export restrictions and Research 1 geometry are
unchanged. Research 1 is now a dirty source tree; do not describe the current combined
code as the old clean provider revision.

Verification: all 73 Research 3 Python tests and all seven Research 1 landmark tests
passed. Runner/collision script Python compilation and test-scene schema validation
passed. Existing test results and calibration were not rewritten.

## Why the full comparative campaign has not started

`reports/doorway_geometry_audit_v1.json` audits all five recent executed development
paths against the second doorway marker's actual aperture plane. None crosses it,
including all four trials previously counted as navigation successes. This is a
concrete mismatch between reaching the route goal and executing the instruction
"take the second doorway".

The provider builder samples marker locations at fractions of an existing shortest
path and offsets them sideways. Its fallback offsets can change sides when necessary
to avoid occupied cells. The visual props do not add physical passage choices.
Consequently, silently scoring passage near a marker as taking a doorway would change
the research task. Running the prepared 560 cases does not resolve that mismatch.

The comparative study therefore needs a research-design decision:

1. Preserve the doorway-navigation claims and author/verify geometry-faithful
   Research 3 derivative worlds and passage annotations, leaving Research 1 worlds
   untouched. Revalidate the affected perception/route setup before the campaign.
2. Change the research task explicitly to ordered marker navigation, revise the
   instruction benchmark/protocol and claims accordingly, then freeze the campaign.

The first choice preserves the original research question. It expands world/benchmark
construction beyond the visual-only handoff. The second changes the question being
evaluated. Neither can be silently selected as a routine scoring implementation.
No additional landmark human labels are being requested at this point.
