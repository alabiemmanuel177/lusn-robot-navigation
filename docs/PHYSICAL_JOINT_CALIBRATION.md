# Joint observation export and calibration admission

The physical provider's confidence target is a jointly correct observation:
correct object category, stable entity association, and pose under an explicitly
approved rubric. A category-only human judgment does not establish that target.
The [joint review interface](PHYSICAL_JOINT_REVIEW.md) records the three dimensions
separately; the exporter and calibration bridge revalidate that distinction.

## Human decisions required before review

The joint rubric uses `research3-joint-review-policy/v1`. It needs
`status: approved`, `reviewer_type: human`, a nonempty human `approved_by`, a
timezone-aware `approved_at`, `protected_data_used: false`, and four nonempty
rules: `category_rule`, `entity_association_rule`, `pose_rule`, and `yaw_rule`.
Approval must precede every retained verdict. A typed approver name is an external
attestation, not authenticated identity.

The human must specify the pose acceptance rule or tolerance and how to judge
yaw. The retained yaw is catalogue supplied, not an independently estimated
orientation. No script chooses a tolerance, treats catalogue yaw as an independent
measurement, or approves these rules automatically. An absent or draft policy is
preview-only; it does not authorize saving judgments. Missing reference evidence
under an approved policy allows only an unreviewable item.

The coverage policy is separate. Existing
`research3-physical-calibration-coverage/v1` and `/v2` requirements retain their
explicit map/class/outcome and confidence-bin minima. Those values must be
prespecified; neither the exporter nor fitter relaxes them to make a packet pass.

## Export contract

[`export_physical_human_review.py`](../scripts/export_physical_human_review.py)
reads existing human decisions without changing them. Its joint mode takes
`--inventory`, `--qa`, `--progress`, `--evidence`, `--policy`, `--requirements`, and
a new `--output` directory. Evidence and policy must be supplied together.

Joint audit headers use `research3-physical-human-review-audit/v2` and pin the
inventory, individual visual QA, reference evidence and rubric. Every event
includes `dimension_verdicts` with exactly `category`, `entity_association`, and
`pose`. Each value is `correct`, `incorrect`, or `unreviewable`. The event also
binds `evidence_sha256`, `policy_sha256`, and `item_evidence_sha256`.

The exporter recomputes the aggregate:

| Explicit dimension results | Joint calibration label |
| --- | --- |
| All three correct | `1` |
| At least one incorrect | `0` |
| No incorrect dimension, but at least one unreviewable | Excluded as unreviewable; not a negative |

It rejects missing dimensions, conflicting aggregates, stale evidence/rubric
hashes, explicitly non-human provenance, duplicate/conflicting events, invalid or
non-monotonic timestamps, and approval dated after a verdict. Latest valid human
decisions supersede earlier events without deleting audit history.

Legacy v1 logs remain readable historical records. Their binary judgments are
excluded with reason `legacy_category_only_not_joint_review`, regardless of sign.
They cannot silently become joint calibration labels. A new joint review requires
a new create-once progress log; old artifacts are not relabeled or overwritten.

The output readiness schema is `research3-physical-human-export/v2`. Its
`joint_review_contract` uses `research3-joint-calibration-label-contract/v1` and
records the target
`category_and_stable_entity_association_and_pose_under_approved_rubric`, the
dimensions, evidence/rubric hashes, and accepted per-observation label bindings.
Provider rows and normalized samples keep their existing v1 formats for runtime
compatibility; the separate contract states what their binary `correct` means.

## Candidate fitting and deployment approval

[`fit_physical_joint_calibration.py`](../scripts/fit_physical_joint_calibration.py)
fits only after re-running the joint export and matching all retained export
files. It requires explicit `--partition` (`development` or `validation`) and
`--minimum-samples`; no new research sample threshold is chosen for the caller.
Both binary outcomes must be present. Protected samples are forbidden.

The create-once candidate keeps `landmark-calibration/v1` and adds the exact
`joint_review_contract`. Its metrics are in-sample only and
`deployment_approval_granted_by_this_tool` is false. The fitter grants no protocol
or deployment approval.

[`validate_physical_calibration.py`](../scripts/validate_physical_calibration.py)
now also requires the evidence/rubric paths for successful admission. It rejects
an old category-only artifact even if its normalized sample checksum happens to
match. Successful admission requires
`research3-physical-calibration-approval/v2`, the existing explicit human
`nonprotected_physical_calibration` scope, every current input/export hash, exact
reviewed scene/provider bindings, prespecified coverage policy, final-review
timing, and acknowledgement that fit metrics are in-sample only. Its campaign
output remains `research3-physical-calibration-validation/v1` for compatibility.

The historical generic calibration freezer remains available for historical
workflows; it does not supply this joint contract and is not the physical joint
admission path. No frozen provider/core/capture source needs to change to implement
these review and export semantics.

## Verification boundary

Synthetic tests reproduce the former legacy-positive promotion and verify its
rejection, plus missing dimensions, wrong entity association, uncertain pose,
tampered hashes/aggregates, draft and post-hoc rubrics, legacy artifacts, coverage
blocks and candidate provenance. These are software tests, not genuine research
labels, approved pose tolerances or evidence of calibrated detector performance.
