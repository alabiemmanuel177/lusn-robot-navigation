# Research 3 calibration recovery proposal

Status: proposal only; no new collection, source change, protected access,
validation-key release or calibration freeze authorized by this document.

## Verified starting point

The completed fixed development schedule accounted for 400 attempts. The 397
reviewable targets have returned binary human labels, all correct. Their accepted
raw-confidence coverage is:

| Class | [0,.5) | [.5,.8) | [.8,1] | Correct | Incorrect |
| --- | ---: | ---: | ---: | ---: | ---: |
| Chair | 0 | 60 | 39 | 99 | 0 |
| Doorway | 0 | 0 | 98 | 98 | 0 |
| Laboratory entrance | 0 | 0 | 100 | 100 | 0 |
| Office entrance | 0 | 0 | 100 | 100 | 0 |

Evidence: `reports/expansion_development_calibration_candidate_20260914_v1/development_calibration_candidate.json`,
SHA-256 `3524e0416a702369cdec2d83c97b9aa7caf34e598db189bca5a670590e868dd0`.
Its recorded development-return hash matches the received ZIP. Status is
`coverage_blocked`, classes are null, and validation_used is false.

The historical `development_freeze_proposal.json` contains a generic invitation
to approve a freeze despite null temperatures and failed coverage. It must NOT
be treated as a ready-to-approve model or justification to release validation.
This proposal preserves that original record rather than rewriting its history.

The completed diagnostic asset decision file records acceptance of all 80 assets,
but explicitly does not grant collection by itself. Development/validation review
must not be requested again merely because older status text says it is pending.

## Recommended route: preserve the original question

### Step 1: development-only feasibility and design preparation

Before asking the reviewer to label another large batch, inspect retained
development capture metadata and the frozen provider's score/association path.
Separate pixel support, colour mismatch, metric association and sampling effects.
Use existing permitted evidence first. Any synthetic analysis is engineering
evidence only and cannot supply calibration observations or correctness labels.

The provider combines colour agreement and component pixel support, then applies
a spatial association factor and temperature transform. It filters by catalogue
category/attributes and association radius. These mechanisms make viewpoint
variation alone an uncertain way to obtain the missing distribution. The formula
does permit low probabilities; the current data do not establish that low scores
are impossible. No threshold, palette, temperature or human label will be changed
simply to populate a quota.

An exact-ID audit of all 397 retained development provider tasks is now saved in
`reports/development_score_support_20260921_v1.json`. All 397 components have at
least 72 pixels (class minima: chair 1,528; doorway 949; both entrances 77).
With the frozen provider's default min_pixels=18, 72 pixels already saturates its
support term. Thus this collection did not exercise reduced pixel support.
Minimum recorded confidence is .531 for chairs and above .860 for the other
classes. This identifies a concrete limitation of the sampled views, not proof
that reducing support will generate incorrect outcomes or meet the full gate.
The audit reads development data only and binds each task file by SHA-256.

Prepare candidate viewing/scene conditions with a stated environmental rationale,
clear provenance and exact source/asset identities. If feasibility needs new live
captures, submit their own bounded, development-only schedule for approval first.
Mark those outcomes design-only and exclude them from future certification. Do
not select production frames by confidence, success or correctness.

### Step 2: an exact prospective amendment before additional primary data

The amendment must specify:

- Target distribution and whether it still represents the original navigation
  task. Purposefully engineered challenges are not naturally occurring errors.
- Exact development and untouched validation sampling frames, sources/assets,
  conditions, seeds, view groups, attempt budget and order.
- Whether the previous development wave is retained or excluded, with fixed
  weighting and no undocumented pooling across changed distributions.
- Treatment of the previously collected validation set. Its labels remain
  uninspected; it cannot automatically certify a changed observation distribution.
  Specify the need for additional matched validation before new outcomes exist.
- No outcome-dependent early stopping, replacement of failures or additions until
  the requirements happen to pass. Explicit infrastructure and missingness rules.
- Unchanged coverage floors, unless a separately justified change of scientific
  scope is explicitly chosen and the original failed gate is still reported.
- Human evidence review, source/resource safeguards, and failure-to-close policy.

No executable schedule or sample-size guarantee is claimed by this outline.
The existing engineered diagnostic observations remain excluded from primary
negative quotas and fitting under the accepted protocol. Changing that exclusion
would be a substantive new scientific decision, not an implementation shortcut.

### Step 3: resume the established downstream gates

Only after genuine new primary evidence passes its approved requirements: fit on
development, review/freeze the actual candidate, authorize validation release,
evaluate without refitting, decide model acceptance, finalize statistical design,
authorize the exact campaign scopes, analyze and approve the reproducible release.

The preliminary B6 minus B5 contrast is -0.111 among 72 complete development pairs.
This is uncalibrated feasibility evidence, not a successful confirmatory result.
Any use for design must retain the eight incomplete pairs and their missingness
accounting; complete-pair point estimates alone do not certify achieved power.

## Alternative requiring explicit change of scope

Close the current work as a limited descriptive/engineering study: report the
failed calibration coverage, perception review and navigation feasibility honestly.
Do not call this completion of the original calibrated-navigation experiment,
validated calibration, or demonstrated B6 benefit. Its manuscript and release
still need engineering checks and human acceptance, but it avoids promising an
unbounded sequence of collection rounds.

## Decision boundary

The user's request to complete Research 3 permits preparation toward the original
objective. It is not recorded as approval to relax coverage, repurpose diagnostic
negatives, inspect validation labels, change provider code, or execute an unspecified
new campaign. The next requested decision should be on a concrete bounded
feasibility/collection proposal, not another generic "approve everything" form.
