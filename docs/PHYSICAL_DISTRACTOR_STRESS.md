# Readable-world shape stress derivatives

`scripts/build_physical_distractor_worlds.py` supports only development base-r010
and validation base-r011. Each category gets a separate derivative containing one
additional visual-only primitive near the lexicographically first stable instance
of that category. Categories are chair, doorway, laboratory entrance and office
entrance. Keeping conditions separate avoids multiple mutually competing confusers
and leaves every original real object, readable sign and all four route choices.

Chair and doorway conditions append a sphere; laboratory/office entrance conditions
append a short upright cylinder. The v1 shapes sit at floor level and copy the exact
original target marker material. They do not replace the chair, doorway or sign.
The source XML tree remains canonically unchanged when the appended model is
removed; maps, perception scene, task IDs, collisions and plugins are unchanged.
Only the world and its manifest/execution-catalog world hashes change. Source and
derivative hashes and the selected shape pose appear in `shape_stress_audit.json`.

Placement respects the provider's existing 0.9 m XY association radius without
changing association logic. The provider matches category/attributes and chooses
the nearest unused entity, in detector-confidence order. A colour-matched shape
may therefore compete with the real object for a stable identity. Rendering,
occlusion, projection and confidence can prevent that; a nearby shape is **not**
evidence that a false positive occurred. No ground-truth feedback or labels are
fed to the provider, and no detections are invented by this builder.

```sh
python3 scripts/build_physical_distractor_worlds.py \
  --base base-r010 --output-root data/physical_shape_stress_dev10_v1
```

Output is create-once, with `CATEGORY/base-r010/` subdirectories. Validation
base-r011 can be generated using the same prespecified procedure; do not tune
the procedure to held-out outcomes. No protected source is opened.

## Before human review

Capture exact detector-linked RGB-D and the full corridor/room context. Check every
offered item's actual marked pixel and full silhouette, not just its nominal pose
or colour. If the marker still points to a real landmark, retain that observation
honestly; do not relabel it as an error. Reject clipped, visually ambiguous, or
unlinked observations instead of asking the user to guess. Mix review-ready true
landmark observations from the original readable worlds with genuinely observed
shape-confusion cases, while keeping condition/source provenance visible to the
analysis. Do not supply an answer key to the human reviewer.

These are **targeted stress conditions**, not natural-error prevalence or ordinary
scene coverage. Because the additions have no collisions, they are perception-only
stress assets, not physical obstacle-validation worlds. Human review, detector
performance, false-positive occurrence and live readability remain unvalidated
until actual captures are inspected. Tests only verify construction and invariants.

## Development chair occlusion v2

The actual v1 chair capture was inspected: its reported chair pixel remained on
the real visible backrest above the sphere. This was not a demonstrated sphere
false positive. Keep that evidence and the original v1 worlds unchanged.

The explicit `--controlled-chair-occlusion` option adds a separate development-only
condition with sphere centre `(2.0, 0.6, 0.45)` metres and radius `0.30` m. Relative
to v1, only the appended sphere's pose/radius change; original simulation elements,
collision/map geometry, scene, identifiers and all real landmarks remain intact.
This condition is restricted to base-r010/chair, never validation or held-out tuning.

```sh
python3 scripts/build_physical_distractor_worlds.py --base base-r010 \
  --controlled-chair-occlusion --output-root data/physical_shape_stress_dev10_v2
```

The sphere is intended to obscure more coloured seat/backrest area while remaining
visually identifiable in full context. Its full silhouette, actual occlusion and
detector pixel must still be checked from a live capture. Neither the geometry nor
the intended placement proves a false positive. This is a declared development
stress intervention, not a detector configuration change or natural-error estimate.

## Development doorway/entrance material-occlusion v2

Root's actual v1 inspections found the doorway pixel on the purple lintel, the LAB
pixel on its original plaque and the OFFICE pixel on its original plaque. None
demonstrated a shape false positive. V1 evidence and world files remain unchanged.

The separate `--controlled-material-occlusion` option appends a neutral gray visual
shell over the selected original lintel/plaque, copied at its exact pose with each
box dimension expanded by 0.01 m. The underlying original model and collisions are
untouched. Readable LAB/OFFICE lettering remains a separate untouched model. The
shell deliberately obscures the target marker's colour; it is not a box offered
to the human as the false-positive distractor.

The unmistakable sphere/cylinder remains the intended distractor. Doorway spheres
keep their v1 pose. Entrance cylinders move toward the opening to signed y=1.0 m,
bringing their visible front closer to the unchanged 0.9 m XY association region.
Circle-versus-wall footprint checks, including doorway openings rather than a
blanket corridor-width bound, verify that this placement does not intersect wall
footprints. Shell and distractor have no collision elements or plugins.

```sh
python3 scripts/build_physical_distractor_worlds.py --base base-r010 \
  --controlled-material-occlusion --output-root data/physical_shape_stress_dev10_v2
```

This creates only doorway/LAB/OFFICE conditions and leaves the separately retained
chair v2 untouched. The intervention is development-only and explicitly recorded
in each audit. It changes the visual scene intentionally, not detector thresholds
or association. A live frame must still establish unobscured shape silhouette,
readable context and actual detector pixel before any item is offered for review.
No false positive, calibration improvement or natural-error prevalence is implied.

## Final development chair material-occlusion v3

The root's v2 inspection found the chair pixel on a tiny surviving backrest corner,
outside the sphere silhouette. Retain that evidence without calling it a false
positive or offering an ambiguous corner for human review. Do not move the sphere
again based on detector outcomes.

The explicit `--controlled-chair-material-occlusion` condition keeps the sphere at
the v2 pose/radius and appends neutral gray, visual-only shells over **both**
`chair_back` and `chair_seat`. Each shell copies the original box pose and expands
its dimensions by 0.01 m. Original coloured boxes, collision geometry, black legs,
all other models, maps, scenes and task IDs remain unchanged. Audits record both
source materials, original/shell dimensions, masks and poses. The masked chair
still exists; this is deliberate colour occlusion, not a claim that the scene
contains no real chair.

```sh
python3 scripts/build_physical_distractor_worlds.py --base base-r010 \
  --controlled-chair-material-occlusion --output-root data/physical_shape_stress_dev10_v3
```

This final chair condition is development-only, create-once and separate from v2.
It changes no detector code or threshold. Actual shape visibility and detector
targeting remain live-review gates; no false positive or natural-error prevalence
is asserted by construction.
