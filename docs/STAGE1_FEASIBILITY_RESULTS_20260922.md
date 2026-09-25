# Completed development-only viewpoint feasibility panel

The fixed 80-assignment schedule is fully accounted for. It produced 49 assigned
landmark emissions, 26 evidenced nondetections and five infrastructure failures.
All 75 completed captures passed retained RGB/depth byte hashes, exact synchronized
frame/provider-completion matching and emission-delivery integrity checks.
No failed assignment was repeated or replaced. The final 36-assignment two-worker
resume completed without a new infrastructure failure.

## Raw-confidence support

Each class had 20 scheduled attempts. Counts below include only the assigned
emission, not other objects emitted from the same frame.

| Class | [0, 0.5) | [0.5, 0.8) | [0.8, 1] | Nondetections | Infrastructure failures |
| --- | ---: | ---: | ---: | ---: | ---: |
| Chair | 11 | 0 | 0 | 7 | 2 |
| Doorway | 0 | 6 | 12 | 0 | 2 |
| Laboratory entrance | 0 | 5 | 3 | 11 | 1 |
| Office entrance | 0 | 5 | 7 | 8 | 0 |

These counts show that the fixed viewpoints exercised low-confidence chair
emissions and medium-confidence emissions in the other classes. They did not
provide any low-confidence doorway or entrance emissions. Some views produced
nondetections rather than low-confidence predictions. Nondetections remain in
the denominator and cannot be treated as probability-zero negative labels.

## Scientific interpretation and limits

An additional frozen-provider audit reconstructed all 49 selected scores with
maximum residual 1.12e-16. Selected component sizes ranged from 18–109 pixels for
chairs, 26–242 for doorways, 18–166 for laboratory entrances, and 28–185 for office
entrances. Thus reduced pixel support was exercised; the missing bins cannot be
explained solely by all components remaining above the support-saturation limit.
Minimum emitted probabilities were .11779, .65472, .59234 and .64462 respectively.
All computed reference-point discrepancies were below .35 m (maximum .23554 m),
but this is only an automated numerical check, not a human joint verdict.
Source: `reports/stage1_design_score_support_20260922_v1.json`.

This design-only panel does not establish correctness, incorrect associations,
calibration quality or downstream navigation benefit. Its observations are
excluded from primary calibration fitting and certification. No human labels
were generated, and no validation labels were consulted.

The panel does not demonstrate a sampling design that meets the unchanged
class/confidence-bin coverage requirements. Even human review of every emitted
item cannot create observations in the empty raw-confidence bins. Therefore a
large calibration-labeling request for these 49 items is not justified as a way
to close the existing coverage gate. Optional engineering inspection is distinct
from primary calibration review.

The previous primary development wave remains coverage-blocked: its 397 reviewed
observations were all correct. The current design panel cannot be silently pooled
into it, used to satisfy negative quotas, or used to release validation labels.
Any additional primary collection needs a prospective amended sampling design
and rationale. Changing the detector, class definitions, confidence formula,
negative-exclusion rule or study scope is a separate scientific decision.

## Execution limitations

One historical failure was a reproduced process-exit race in the resource guard;
the explicitly approved repair was applied and bound in snapshot v8. Four later
attempts were stopped by the CPU-load safeguard while another project's campaign
was active. The old scanner missed Gazebo's rewritten argv[0]; the corrected
scanner was bound into the two-worker resume. Short resource tests did not prove
long-run noninterference, and no claim of zero impact on the external campaign is
made. No external campaign was changed or stopped by this work.

## Reproduction and evidence

- Scientific assignment manifest: `reports/stage1_view_feasibility_20260921_v3.json`.
- Original 24 attempts: `reports/stage1_four_workers_20260922_v1/`.
- Next 20 attempts: `reports/stage1_four_workers_20260922_v2/`.
- Final 36 attempts: `reports/stage1_two_workers_20260922_v4/`.
- Combined accounting: `reports/stage1_two_workers_20260922_v4/summary.json`.
- Read-only reconstruction: import `summarize_stage1_four_workers.summarize()`;
  its CLI writes the summary create-once and should not overwrite the existing one.
- Capture files: the 80 exact `r3-recovery-feas-*` run directories referenced by
  the manifest, not arbitrary files under `reports/`.

This is completion of the bounded design-feasibility panel, not completion of
Research 3, calibration certification, or the comparative/held-out campaign.
