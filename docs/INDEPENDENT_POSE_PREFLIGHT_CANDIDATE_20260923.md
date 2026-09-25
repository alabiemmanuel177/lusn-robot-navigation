# Independent pose preflight candidate

The old capture records cannot retrospectively provide independent robot pose or
capture-time description provenance. A new development-only preflight must retain:

- Actual expanded robot SDF, state-publisher URDF, camera settings and mount
  transforms, with hashes captured at launch (not inferred from today's files).
- RGB, depth, intrinsics and localization TF at the selected synchronized timestamp.
- Simulator world pose for the uniquely identified spawned robot at that same
  timestamp, plus the actual sensor mount chain. No commanded spawn pose, AMCL/odom
  TF or nearest timestamp is a substitute. Missing exact truth is missing evidence.
- Source world and capture manifest hashes, raw simulator pose message, entity
  name/ID mapping and clock/sequence metadata. Truth collection is evaluation-only,
  never subscribed to or passed into the detector, association or score learner.

`candidate_pose_validation.py` checks rigid transforms, exact timestamp equality
and declared provenance. The engineering screen is translation error <=0.03 m
and orientation error <=1 degree. These are proposed preflight checks, not new
calibration certification thresholds. Boolean provenance fields are assertions,
not cryptographic proof: the eventual collector/auditor must verify raw evidence
and all source hashes before constructing that input.

Separately check the predicted point against the existing inclusive 0.35 m
catalogue-reference rule. That distance alone does not establish category or
instance correctness; those remain genuinely human-reviewed dimensions.

Tests cover wrong truth source, missing source binding, timestamp mismatch,
orientation error, translation error and the inclusive reference boundary.
This is prepared validation tooling, not a claim that a new live preflight ran.
