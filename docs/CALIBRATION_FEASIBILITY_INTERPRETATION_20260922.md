# Why another identical viewpoint round is not justified

The fixed design-only panel has 49 assigned emissions, 26 nondetections and five
retained infrastructure failures. All 49 raw confidences reproduce from the frozen
provider. This analysis neither labels observations nor changes collection rules.

For an emitted component with at least 18 pixels, support s is at least .25.
With provider temperature 1 and association distance d≤.9 m, its score is

    p = (.45 s + .55 c) (1 − d/3),

where c is colour agreement and support saturates at 72 pixels. Therefore, if
colour agreement remains at least .89 and reference-point error is at most .35 m,
even the smallest permitted component has p≥.53177. Reducing apparent size alone
cannot put such an observation into the [0,.5) bin before it disappears below
the component-size threshold. At minimum support and c=.89, p<.5 requires
d>.5083 m, or a decrease in colour agreement. These are conditional inequalities,
not guarantees about unseen views, and they do not establish semantic correctness.

Observed minimum colour agreement was .89175 for doorways, .89837 for laboratory
entrances and .90502 for office entrances. Their conditional minimum-support,
pose-consistent score floors are .53262, .53583 and .53906. Chairs differ: their
observed colour agreement reaches .0202 and the panel contains 11 low scores.
The analytic report retains every class and marks future colour floors unknown:
`reports/conditional_score_bounds_20260922_v1.json`.

## Consequences for the next design

- More copies of the same view geometry do not address the demonstrated support
  mechanism. The completed panel already includes reduced pixel support.
- A scientifically justified new observation distribution would need to expose
  naturally occurring colour/depth/association ambiguity, not simply select low
  scores after collection. Whether an amended environment represents the target
  navigation task must be specified prospectively.
- Engineered distractors, inserted occluders and synthetic pose shifts remain
  diagnostic only under the accepted amendment. They cannot be reclassified as
  primary negatives to satisfy a quota. Nondetections are not negative labels.
- A further fixed primary schedule cannot presently be claimed likely to meet
  coverage. A changed design or a narrower descriptive study remains a human
  scientific decision; no additional large human review is requested for this panel.

## Claim scope

The provider uses catalogue-supplied colour/category signatures, then associates
projected components to nearby catalogue entities of matching category/attributes.
The silhouettes aid human review but are not a learned semantic classifier.
Calibrating this pipeline would establish evidence about this marker-based
simulator observation mechanism, not general visual-language recognition accuracy.
That scope limitation persists even if future coverage and navigation gates pass.
