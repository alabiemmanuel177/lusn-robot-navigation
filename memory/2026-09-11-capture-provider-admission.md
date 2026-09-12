# Provider provenance through calibration and campaign admission

Fresh source-bound captures retain explicit R3 hashes and a separate detector
provider source/build snapshot. Inspection found that the calibration evidence
bridge only carried R3 source hashes, and campaign admission compared those alone.
Thus recorded external provider identity could be dropped or changed without
rejecting the reviewed binding.

Four regressions demonstrated the gap before the fix: missing, changed and
incomplete provider identities were accepted at campaign admission, and the bridge
dropped the captured provider field. The bridge now requires and preserves a
complete, hash-bearing provider snapshot. Campaign admission recomputes the active
snapshot and requires full equality. The 32 focused bridge/executor tests pass.

Fixtures are synthetic and mock provider inspection; no human labels or execution
approvals were created. Historical evidence without these pins remains historical,
not automatically compatible. Explicit source/build pins do not establish complete
external model, ROS binary or environment reconstruction.
