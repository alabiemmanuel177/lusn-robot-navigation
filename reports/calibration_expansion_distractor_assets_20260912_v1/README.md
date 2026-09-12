# Diagnostic sphere candidates — not an observation review kit

Forty create-once development derivatives have been built: ten maps × four
classes, using the approved seed-1/view-0 target and camera pose for each class.
Each adds one 0.20 m radius, visual-only sphere using the target marker's exact
material. Original objects, readable signage, collision geometry, catalogue IDs,
routes and map bytes remain unchanged. The manifest's world hash is updated.

Placement chooses the first geometrically feasible distance from the fixed list
0.45, 0.55, 0.65, 0.75 m toward the prespecified camera position. It uses only wall
and camera clearance, not observations, confidence or correctness. These are
engineered conditions, never primary calibration negatives.

All 40 passed static placement and camera footprint checks. An independent audit
verified every source/derivative digest, exact preservation of the original SDF
subtree, unchanged non-world assets (except the necessary manifest hash), and no
added collisions or plugins. This does not prove visibility or detector response.

Status: built candidates, not approved execution inputs. No new RGB-D capture or
human labels are included. Rendered visual preflight and exact asset approval are
still required. The separate 40 occlusion assets have NOT been built here; this
package must not be mistaken for completion of the 80-attempt diagnostic panel.
Do not run these through the historical distractor launcher by relabeling audits.

The original pilot review remains accepted. No repeat pilot review is requested.
