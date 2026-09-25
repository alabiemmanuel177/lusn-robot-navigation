# Exploratory distance × lighting pilot, R3-DL-20260923

The user instructed continuation after the failed Stage A pilot. This authorizes
continued R3 development/design experimentation, not approval of unseen primary
distributions, human labels, calibration models, validation release or protected
execution. This is a separate exploratory iteration, not an extension of Stage A
and not a confirmatory preregistration. All earlier failures and evidence remain.

## Mechanism and test

Stage A reconstructed all 119 scores. Every emitted laboratory/office entrance
had size support saturated at 1 (at least 72 pixels). At 90% lighting, colour
agreement fell to 0.2004–0.2282 and 0.2472–0.2604 respectively, but scores stayed
above 0.5. Earlier nominal-light distant observations reduced support without
reducing colour agreement. The untested interaction is distance plus lighting.
Neither evidence panel supplies human correctness labels for this experiment.

Test this interaction without changing the provider, score formula, temperature,
palette, thresholds, association radius, camera, landmark identities or geometry.
Reuse the exact Stage A lighting assets (nominal/90%/80%). New poses interpolate
halfway or fully from original expansion view 0 toward the earlier geometry-only
maximum-range pose. Face the target, with the original far-view offsets 0 and
+0.65 radians on map 1 / −0.65 on map 6. Interpolation is in base x/y, not a claim
of half optical range. Static footprint checks pass for all 32 distinct poses.

## Fixed budget before new rendered outcomes

Two development maps (1,6) × four classes × two distance fractions (0.5,1) ×
two yaw offsets × three lighting levels = **96 assignments**, simulator seed 9.
Shuffle once with seed 20260924. Do not select maps/poses from favourable
outcomes, sample until quotas pass, replace failures or change factors mid-run.
Map choice is inherited from Stage A, not a new outcome-based selection.

Use the earliest synchronized RGB-D frame, one frame per attempt, exact assigned
entity/class, 90-second capture wait. Keep nondetections and infrastructure
failures distinct. First assignment runs alone, then at most two low-priority
workers with source/resource guards. Correct environmental failures and continue
unstarted assignments only; never replay a dispatched assignment. Persistent
source/resource failures pause dispatch without changing the scientific schedule.

All observations are design-only and excluded from fitting and primary quotas.
Record prior-data-driven design development explicitly. No primary schedule is
automatically promoted from this experiment.

## Evaluation

After exhausting the schedule, independently audit every request and usable
capture, reconstruct all emitted scores, and report strata and missingness.
Retain the Stage A feasibility screen: at least two emissions per class per raw
bin [0,.5), [.5,.8), [.8,1]. If it fails, do not request calibration human review.
If it passes, genuine human joint review is still necessary, with the existing
two-correct/two-incorrect per-class pilot screen and legitimate unreviewable
outcomes. Neither pose arithmetic nor AI image inspection supplies those labels.
Full-frame raw RGB-D and context remain available; distant markers may be
unreviewable. Successful score coverage is not calibration or navigation benefit.

Primary Coverage v2 floors stay unchanged and separately apply to development
and validation. Old validation labels remain sequestered. No Research 1/2 files,
protected worlds, primary experiment protocol or approved calibration method is
changed. A failed interaction pilot is not permission for endless outcome-driven
collection; report its mechanism and remaining scientific design alternatives.
