# Readable physical-world capture derivatives

`scripts/build_readable_physical_worlds.py` creates non-protected, create-once
copies with visual-only LAB / OFFICE signage. Source worlds, task instructions,
stable entity/region IDs, markers, maps and collision geometry remain unchanged.
No Research 1/2 files are modified, and protected source IDs are rejected before
any file is opened. These assets prepare genuine human review; generated signage
does not provide human labels or prove that a captured sign is legible.

Each of the four existing entrances gets a corridor-facing and room-facing sign
showing only its existing category. No sign exposes target selection, side,
ordinal, expected route or evaluator answer. LAB means laboratory entrance;
OFFICE means office entrance. Both alternatives on each side are treated equally.

Signs use self-contained 5-by-7 block-letter box visuals, white on a dark board.
They add no collision, plugin or texture dependency. Board dimensions are
1.02 m wide by .30 m high, centered at z=1.43 m (bottom 1.28 m, top 1.58 m), above
the original marker and below the lintel. Text pixels are .026 m apart. Local
front is -Y, with each face independently rotated so letters are not mirrored.

For base-r010, doorway x positions are 4.3 and 7.5 m. Corridor panels are at
y=±1.10 m; room panels at y=±1.30 m. Right-side panels say OFFICE; left-side
panels say LAB. On other worlds the builder uses the actual existing category,
doorway location and corridor width, never a selected target. The explicit
positions and orientations are retained in `visual_derivative_audit.json`.

Every original SDF element is checked structurally unchanged before adding
visual models. Maps and semantic scenes are copied byte-for-byte. New world
hashes replace only `world_sha256` in the copied execution catalogue and manifest.
The original geometry audit and ordered annotations remain byte-identical;
the new visual audit explicitly pins that audit to its original world hash and
inherits only its unchanged-collision result, not live visual validation. The
visual audit hashes every source and derivative asset.

Build example (output must not already exist):

```sh
PYTHONPATH=src python3 scripts/build_readable_physical_worlds.py --output-root data/physical_worlds_readable_v1 --base base-r010
PYTHONPATH=src pytest -q tests/test_readable_physical_worlds.py
```

The builder also supports `--all-nonprotected` for a fresh output root. It launches
no simulator. Before presenting reviews, capture representative corridor and
room-facing views and verify actual text size, occlusion and crosshair identity.
Do not reuse previous detector-coverage claims: new visual content is a derivative
requiring documented capture provenance and its own evidence. Preserve previous
failed/ambiguous review images unchanged. No calibration freeze or held-out
evaluation is authorized by this derivative.

## Offline build completed

All 14 development/validation derivatives are now under
`data/physical_worlds_readable_v1/base-r001` through `base-r014`, including
`base-r010` for the first live capture. All 56 runtime route alternatives validate;
112 visual-only panels were added. Four regression tests pass. Original geometry
and assets remain unchanged; live legibility still requires a real capture check.
