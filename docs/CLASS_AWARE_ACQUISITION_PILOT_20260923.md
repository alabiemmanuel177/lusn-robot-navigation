# Class-aware acquisition pilot — exploratory development only

This is another explicitly recorded design-development iteration under Emmanuel's
instruction to continue the research. It is not primary collection or a change to
the failed panels' gates. No old observation is pooled into this new pilot.

The preceding experiments isolate two different mechanisms: near-oblique
doorway observations can have projection uncertainty; smaller distant entrance
markers under reduced lighting can have unsaturated support and colour agreement.
The static marker projection diagnostic predicts all sampled doorway marker boxes
remain in the saturated size range, unlike some entrance marker boxes. The
acquisition policy therefore branches on the requested landmark class—not on
an observed confidence or human verdict during collection.

## Fixed prospective pilot policy

- Development maps 1 and 6, all four classes; simulator seed 17.
- Doorway: original view positions 0 and 3; face the catalogue target plus
  −0.95 or +0.95 radians; nominal/90%/80% existing lighting.
- Chair/laboratory entrance/office entrance: the distance–lighting pilot's
  midpoint/far poses and 0 / map-signed 0.65-radian offsets, with the same lights.
- Two maps × four classes × two positions × two offsets × three lights = 96
  newly captured assignments. Fixed shuffle seed 20260925.
- All 96 attempts remain, with failures/nondetections distinct and no replacements.
  Earliest synchronized RGB-D frame, exact assigned entity/class, fixed 90-second
  wait. First dispatch alone; at most two low-priority workers thereafter.

Keep provider scores, palettes, camera settings, source geometry, landmarks,
Research 1/2 and primary coverage floors unchanged. The policy is informed by
exploratory development results, not preregistered independently of those results.
Repeating static views under another seed is not evidence of independent-world
generalization. New validation would be required for any admitted primary policy.

The complete pilot must have two emissions per class/raw bin before any proposed
joint human feasibility review. Genuine human incorrect/correct coverage is a
separate gate and cannot be inferred from bin support. This pilot cannot grant
primary collection, model freeze, validation release or protected access.

## Execution provenance

The new driver reuses the frozen distance–lighting execution functions in an
isolated process with explicit temporary dependency bindings. Both driver and
dependency source hashes are pinned; imports do not change the historical module.
The existing request's `distance_lighting_pilot` provenance field carries this
new plan/source digest; it does not reuse the old experiment's approval. Original
source files, plans, starts and results are never edited or overwritten.
