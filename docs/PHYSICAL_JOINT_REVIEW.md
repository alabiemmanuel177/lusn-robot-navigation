# Joint observation review

Provider calibration correctness covers three claims together: category, stable
entity association, and acceptable pose. Category-only historical judgments must
not be promoted to this joint target. No historical progress is rewritten.

The new UI keeps the original decoded RGB frame and detector crosshair. A separate
map-coordinate diagram identifies catalogue landmarks and reported x/y; the
coordinate data, region IDs, capture pose and covariance remain visible. These are
nonprotected reference records, not automatic labels. Reported yaw is copied from
the catalogue and is **not an independent orientation estimate**. The diagram is
not an occupancy map or camera projection; x increases right and y increases up.

Prepare evidence, create once:

```sh
python3 scripts/prepare_joint_review_evidence.py --inventory PATH/inventory.json --output PATH/joint_evidence.json
python3 scripts/serve_physical_review.py --inventory PATH/inventory.json --qa PATH/qa.jsonl --evidence PATH/joint_evidence.json --policy PATH/joint_policy.json --progress PATH/new_joint_progress.jsonl
```

Evidence preparation retains incomplete items and their gaps. It checks the exact
request-pinned runtime scene and summary-pinned observation index, using the exact
selected frame and observation ID. UI inventory validation separately rechecks
the retained frame/task/QA hashes. Only development maps 001–010 and validation
011–014 are admitted before reading scene evidence. No route answers are displayed.

The policy schema is `research3-joint-review-policy/v1`. A draft can contain only
that schema and `status: draft`; it enables evidence preview but **no saved
judgments**, including unreviewable. Do not ask a person to review 60 items while
this policy is pending. An approved policy requires `status: approved`,
`protected_data_used: false`, `reviewer_type: human`, `approved_by`, a timezone-aware
past `approved_at`, and explicit nonempty `category_rule`, `entity_association_rule`,
`pose_rule`, `yaw_rule`. No tolerance or rule is supplied by this tool. Structural
validation and a typed name cannot authenticate a person or confer protocol authority.

Once the policy is genuinely approved, reviewers explicitly choose correct,
incorrect or unreviewable for category, entity_association and pose, with no
default. All correct gives overall true; any incorrect gives false; otherwise
overall correctness remains null. Incomplete reference evidence permits only
all-unreviewable after approval. Missing policy is not a reason to fabricate
unreviewable judgments.

New progress uses `research3-physical-human-review-audit/v2`. Header binds inventory,
QA, evidence and policy SHA256. Each append-only event additionally binds
`item_evidence_sha256` and `dimension_verdicts`, plus the aggregate legacy fields.
Evidence is recomputed from retained source artifacts on each validation. A stale
scene, index, inventory, policy or QA blocks review. Human name is still mandatory.
GET requests never write labels. Legacy v1 APIs remain for historical readers;
the live CLI now requires joint evidence and policy and does not promote v1 labels.

Tests are synthetic only. No actual approval, human labels, calibration fit or
runtime-source change is produced by this implementation.

## Browser regression checks

The reference diagram occupies a full-width row, with short numbered markers and
a separate readable full-ID legend. Legacy category-only controls are both hidden
with an explicit `[hidden]` CSS rule and disabled in joint mode. Image-loaded status
must remain “preview only” while the policy is pending. Testing only the DOM hidden
attribute missed an author-CSS display override; browser computed visibility and
disabled states must be checked together. Synthetic regressions cover these paths.
The subsequent actual desktop check passed for items 1 and 60 and Next unreviewed;
mobile rendering has not been tested. The preview server is closed and its progress
contains only a header, with zero judgments. Policy approval remains pending.

The joint export and calibration workflow is documented separately in
[PHYSICAL_JOINT_CALIBRATION.md](PHYSICAL_JOINT_CALIBRATION.md). Legacy category-only
labels are not silently promoted to the joint calibration target.
