# Physical held-out audit boundary regressions

The new post-execution evaluator was independently reviewed with entirely synthetic
worlds, approvals and measurements. Three concrete regressions failed before the
fix: a mismatched measurement run ID, absent frozen execution-source identity,
and unknown ordered completion could each be accepted as a complete audit.

Root cause: byte hashes and metric recomputation establish internal consistency,
not identity with the approved scheduled experiment. The audit now also requires
request/measurement/summary run identity, approved execution-source pins, exact
scheduled world-asset pins, matching summary map/variant/system/partition and known
boolean endpoints. Unknown outcomes remain unresolved. Additional tests substitute
a self-consistent different world and forge summary identities; both are rejected.
After these fixes the focused audit/release suite passed 42 tests.

This post-execution tool does not implement protected live launch or statistical
inference. No real held-out result was read or generated to build these tests.
Typed human approval fields remain external attestations, not authentication.

## Test-access accounting correction

The pre-existing unrestricted full suite included a refusal test that passed the
real reserved `base-r020` catalogue to the engineering loader, which reads catalogue
metadata before rejecting its partition. The suite also builds the authored corpus
including held-out instruction definitions. Therefore a blanket claim that the
full test suite never touched any protected metadata would be too strong. These
were automated schema/refusal/corpus checks, not live held-out evaluation, label
collection or tuning on held-out outcomes. Root changed the physical refusal test
to use synthetic protected metadata in a temporary directory. Live capture/review
and engineering runs in this continuation remain development/validation only.
