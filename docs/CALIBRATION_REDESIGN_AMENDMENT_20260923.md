# Calibration redesign amendment R3-CA-20260923-02

Status: prepared for feasibility and exact protocol review; **not approved for
primary collection, calibration freeze or protected access**. Emmanuel's latest
“yes go ahead” authorizes preparing this redesign. It is not recorded as approval
of unseen rendered assets, future labels, fitted models or results.

## Decision and rationale

Keep the existing marker-based RGB-D provider for the first candidate and change
the observation conditions, not its reported scores. Add modest whole-scene
illumination variation and camera framing near the image boundary. Preserve all
Research 1/2 files, colliders, routes, landmark identities, marker materials,
camera intrinsics, FOV, detector palettes, thresholds and association rules.
This is the smallest candidate that addresses the observed colour-agreement
floor while allowing partial-object projection errors without injected poses.

This is a hypothesis, not a claim of sufficient coverage. Reduced illumination
may produce only nondetections, and truncated objects may be unreviewable.
The existing method infers category from coloured markers; this amendment does
not turn it into general visual-language object recognition.

## Exact proposed conditions

| Factor | Fixed choices |
| --- | --- |
| Classes | Chair, doorway, laboratory entrance, office entrance |
| Position | Original expansion view 0 and view 3 (+1 m offset); coordinates copied from the historical planning manifest |
| Orientation | Face the catalogue reference from the base pose, then add 0, −0.95 or +0.95 radians |
| Lighting | Nominal, 90%, 80% of nominal world ambient and directional-sun diffuse RGB; alpha unchanged |
| Camera/detector | Existing profile, FOV 2.0 radians, unchanged raw score and temperature 1 |
| Frame selection | Earliest synchronized RGB-D frame, exact assigned entity/class; never select by confidence or correctness |
| Attempt budget | One frame, 90 seconds; infrastructure failures and nondetections remain distinct |

SDFormat 1.9 specifies a default world ambient colour of (0.4,0.4,0.4,1).
The source worlds have a single directional sun with diffuse (0.9,0.9,0.9,1).
The nominal control is byte-identical to its source. The two dimmer candidates
explicitly scale those two illumination fields; model materials and geometry are
unchanged. These are **hypothetical simulator lighting conditions**, not measured
lux levels, a realistic sensor-noise model or estimates of real-building prevalence.
References: [scene specification](https://raw.githubusercontent.com/gazebosim/sdformat/sdf13/sdf/1.9/scene.sdf),
[light specification](https://raw.githubusercontent.com/gazebosim/sdformat/sdf13/sdf/1.9/light.sdf).

No sensor noise, postprocessed images, painted marker changes, new occluders,
spheres or synthetic position displacements are introduced. Camera framing can
truncate an object through the ordinary renderer; actual visibility is unverified
until rendered preflight. Static footprint checks are not visibility evidence.

## Stage A: bounded design-only feasibility

Use development maps 1 and 6: the first map in each half of the ten-map list,
not maps selected for favourable observed outcomes. Four classes × two positions
× three orientations × three lighting levels × one simulator seed (7) × two maps
= **144 fixed assignments**. Shuffle once using ordering seed 20260923.

Keep all terminal attempts, including failed and empty captures. No replacement,
confidence-conditioned retry or automatic schedule extension is permitted. A
pre-dispatch resource admission refusal is not an attempt; any dispatched failure
is retained. All pilot images and any pilot labels remain excluded from fitting,
primary coverage quotas and certification.

Before live dispatch, the R3 lighting-asset admission path and updated source
binding must be tested. Do not rename lighting worlds as previously approved
sphere/occluder assets to bypass the existing runner's asset checks. Verify that
rendered full-scene RGB-D evidence uses the intended world and actual camera,
then preserve complete raw bytes and checksums for every completed assignment.

### Stop before wasting human review

First check the complete fixed pilot automatically: every class must have at
least two usable emissions in each unchanged raw-confidence bin. If any class
fails, report the result and stop—do not request another large labeling round.

Only if that screen passes, assemble all emitted pilot observations for genuine
joint review with full frames, depth, catalogue/pose context and nondetection
accounting. Human review must show at least two correct and two incorrect joint
outcomes per class. These are pilot feasibility screens, **not replacements for
the primary minimum of five**. Unreviewable remains a legitimate verdict and is
not converted to incorrect. A failed pilot requires another explicit design
decision; it does not trigger an expanding search until errors are found.

Passing the pilot is not statistical assurance that the primary schedule will
pass. In particular, two development worlds cannot establish error prevalence
across fourteen worlds or generalization to the validation partition.

## Stage B: prospective primary candidate, conditional on Stage A and review

The complete candidate matrix is already enumerated, but is not executable:

- Development: maps 1–10, the same 18 position/orientation/lighting combinations
  per class, seeds 11 and 12: **1,440 attempts**.
- New validation: maps 11–14, identical factors/seeds: **576 attempts**.
- Total: **2,016 attempts**, with no outcome-dependent additions or early stopping
  because coverage happens to pass. This is a proposed budget, not a completion ETA.

Both seeds share a view group for weighting; repeats are not independent worlds.
The new wave is a new observation distribution. Do not pool any old pilot, old
primary, engineered diagnostic or design-feasibility rows into it. Do not inspect
the old sealed validation labels to choose or evaluate this redesign. New matched
validation is required, with reviewer-held-key delayed release after actual
development model freeze. No reserved navigation worlds 15–20 are accessed.

The equal-map/equal-view-group/equal-emission P2 weighting is retained within each
class, with lighting included in the declared view-group identity. Calibration is
conditional on an emitted observation; report all attempted denominators and
non-emission rates separately. No model is fitted to nondetections as if they
were p=0 negative observations.

### Meaning of errors in the revised primary distribution

A primary negative must be a human-reviewed error in an actual rendered RGB-D
observation under the declared conditions. Neither the generator nor pose
comparison alone supplies the joint human verdict. Errors are simulator-generated
perception errors, not demonstrated naturally occurring real-world errors.

Treating these new lighting/framing conditions as primary rather than diagnostic
is an explicit scientific amendment requiring review. **The old engineered
diagnostic exclusions remain in force**; this proposal does not reclassify those
observations or their labels. If the reviewer does not accept this new target
distribution as primary, the candidate cannot close calibration coverage.

## Unchanged certification requirements

Independently in development and new validation, require per class: at least five
emissions in each [0,.5), [.5,.8), [.8,1] bin, five genuine correct and five genuine
incorrect joint outcomes, and at least one accepted observation per map/class.
Position remains an inclusive .35 m reference-point consistency threshold;
catalogue yaw remains a metadata check, not orientation-estimation accuracy.

Fit the accepted P2 classwise scalar-temperature grid on development only. Keep
the exact objective, weighting, leave-one-map-out diagnostics and failure policy.
Actual-model human freeze, validation release, unchanged validation admission
screen and human model acceptance remain separate. A failure is reported, not
waived or repaired using validation labels.

## Navigation compatibility and claims

Passing calibration on this lighting mixture does not automatically certify the
old nominal-only navigation campaign. The eventual navigation protocol must
specify matched lighting exposure or separately justify the supported nominal
subgroup. Report calibration and nondetection metrics by lighting/framing stratum
without changing the existing aggregate coverage floors.

The primary B6−B5 ordered-completion contrast stays the same. Equal weighting of
the eight instruction conditions can be preserved with a prospectively balanced
lighting assignment within each condition. Any added lighting replication changes
the campaign budget/dependence assumptions and requires revised feasibility/power
assessment before final design freeze. The previous synthetic power numbers are
not achieved power for this redesigned experiment.

## Prepared evidence and next gate

- Config: `configs/calibration_redesign_v2.yaml`.
- Exact shuffled plans and asset/source hashes:
  `reports/calibration_redesign_20260923_v1/plan.json`.
- Static audit: 42 world variants, 336 pose checks, zero footprint failures.
- Independent verifier checks every assigned pose, target, profile and lighting
  asset, plus full-factorial completeness and original source bindings.

No simulator or new primary collection has run under this amendment. The next
execution scope to admit is **Stage A only**, with a tested R3 lighting admission
path and rendered evidence retained for inspection. Stage B remains conditional;
approving this document generically must not be treated as approving its future
observations, final coverage, fitted parameters or downstream campaign.
