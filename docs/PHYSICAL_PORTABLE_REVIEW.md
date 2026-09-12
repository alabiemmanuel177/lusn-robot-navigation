# Portable reviewer handoff

Prepared from Research 2's concrete proposal / human acceptance / evidence-review /
return-validation structure. Research 2's own approved amendment makes a primary
researcher review sufficient and external second review optional. Its approval,
thresholds, and completed labels are NOT Research 3 approval or labels. Relevant
read-only sources inspected: `docs/supervisor-threshold-review.md`,
`configs/protocol_amendment_1.1.yaml`, the threshold proposal/template/researcher
review, `docs/logging-labeling-taxonomy.md`, and the review app / packet renderer
in the Research 2 repository. No Research 2 files or running jobs were changed.

## Deliverable

`reports/research3_reviewer_kit_v1.zip` is a portable kit, not the large engineering
archive. Extract it and follow its README. It contains the 60 selected targets
from 46 nonprotected captures, exact RGB-D evidence and provider logs, individual
QA bindings, the local review server, proposals with rationale, and a pending
accept/revise/reject form. No ROS, Gazebo, GPU or project checkouts are required.
Python 3.10+, Pillow and PyYAML are required; installation instructions are included.
Python dependency ranges are not a fully locked operating environment.

ZIP size: 47,482,492 bytes. SHA-256:
`8146bdfac814a382e696af53b15130554cd74a6cb164fd0b23bcfa76b89d83bd`.
All 384 ZIP members were independently verified after creation.

The kit was subsequently uploaded to the private GitHub prerelease
[research3-review-kit-v1](https://github.com/alabiemmanuel177/lusn-robot-navigation/releases/tag/research3-review-kit-v1).
GitHub's uploaded ZIP digest matches the checksum above. External reviewers must
sign in with repository access. Repository visibility was not changed and no
local source changes were committed/pushed. Do not send the 273 MB engineering
archive as a substitute for this runnable kit.

Following the anonymous protocol review, a separate
[two-phase amendment](PHYSICAL_CALIBRATION_EXPANSION.md) is proposed. The published
kit remains unchanged; it does not authorize that amendment or calibration freeze.

## Two distinct human actions

1. A human with protocol authority reviews the proposed category, association,
   planar position, catalogue-yaw and coverage rules. They may accept all using
   the explicit `approve` command, or fill the pending decision form with revisions
   or rejection and return it before labeling. Their role/name/date and proposal
   hash are recorded. Existing approval files are never overwritten.
2. A human reviewer inspects each observation and explicitly records all three
   dimension judgments. Preview cannot save. Missing information is unreviewable,
   not an automatically incorrect observation. No real approvals or labels were
   generated while preparing or testing this kit.

Proposed position tolerance is 0.35 m, tied to the current R3 goal-error criterion
as an engineering scale, not a validated landmark-optimal threshold. Yaw tolerance
1e-6 rad checks copied catalogue metadata only. Both need human acceptance.
Coverage proposes at least one accepted item per map/class, five per pooled
class/outcome, and five per class/bin with fixed [0, 0.5, 0.8, 1] edges. These are
pilot coverage floors, not precision/power guarantees. The existing 60-item packet
may not meet them; the thresholds must not be lowered after inconvenient labels.
Acceptance does not settle stress-example fit suitability, statistical design,
calibration deployment, or protected evaluation authority.

## Return and validation

The reviewer runs `python3 review.py return --output my-review-return.zip`, then
sends that small ZIP back. It contains approval, policy, coverage and the original
append-only judgment journal, with input hashes. The recipient runs
`python3 review.py validate-return --input my-review-return.zip` in a copy of the
same kit. Partial returns are retained and reported as incomplete. Validation
does not change local labels, silently merge reviewers, or claim calibration.

The kit uses canonical relative run directories, not the capture machine's absolute
paths. Its derived inventory/evidence hashes intentionally differ from the original
workspace packet; the kit manifest records the original inventory hash, and the
request/frame/task/QA bindings remain unchanged. Return validation uses this exact
portable inventory and checks the actual exporter semantics. Do not transplant a
portable journal into the old absolute-path inventory or rewrite its headers.
Downstream fitting must use the verified portable adapter/input contract or an
explicitly audited conversion; this kit does not authorize either automatically.

Archive hashes detect corruption and mismatches, not reviewer impersonation.
Confirm the returning reviewer through your normal trusted communication channel.

## Verification

Twelve synthetic tests cover pending proposals, explicit human acceptance, immutable
inputs, path containment, relocation, return membership/size limits, kit binding,
and a real exporter roundtrip with a synthetic observation. Recomputed archive
checksums cannot hide a contradictory judgment aggregate from that validator.
The actual unlabelled kit was extracted to a folder with spaces, loaded all 60
targets, decoded the first/last images, then moved and resumed with zero verdicts.
Windows/macOS and a clean dependency installation have not been tested; the actual
relocation check was on Linux without project paths in PYTHONPATH. The existing
review UI was reused, not replaced with unverified new rendering code.
The extracted CLI also passed an actual localhost HTTP check for all 60 state
items and first/last PNG endpoints, then its owned server was shut down. Full
Python suite: 793 passed, one sandbox socket skip. No actual review verdicts or
approvals were entered in these real-kit checks.

The earlier engineering archive remains sealed and does not contain this later
portable-kit implementation or proposal. They are a separate dated deliverable.
