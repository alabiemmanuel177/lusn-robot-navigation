# Fixed side-of-opening depth diagnostic

Hypothesis: central-box support can sample through a portal into the room rather
than its frame. This is a testable geometric explanation, not a confirmed cause
for every box. New engineering-only candidate; no detector rerun or primary data.

Use every exact doorway/laboratory-entrance/office-entrance prediction from the
completed Grounding v3 panel. Preserve original box indices and central-depth
results. No selection by expected target, distance, confidence or prior success.

For each box take left/right strips 15% of width, trimming 15% of box height at
top and bottom. Require >=16 valid depth pixels and >=50% valid fraction per side,
with the existing depth range (0.05,12) m. Each side supplies its median; abstain
if their difference divided by their median exceeds 15%. Otherwise use mean side
depth on the box-centre ray. This is a surface hypothesis, not proven reference
point geometry. Angled portals may legitimately fail the side-agreement screen.

Keep the same assumed rendering-camera transform and same-class 0.9 m ambiguous
association rules. Report all statuses and 0.35 m geometric candidate counts only;
do not convert them to human correctness, accuracy or calibration coverage.
No thresholds are revised in response to this replay. A failed result remains a
failed candidate and does not silently replace the original estimator.
