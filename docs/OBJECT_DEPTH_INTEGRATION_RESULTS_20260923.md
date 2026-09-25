# Object/depth integration results

Completed the authorized next engineering step using retained development data.
The immutable replay protocol is `OBJECT_DEPTH_INTEGRATION_20260923.md`.

| Accounting | Count |
| --- | ---: |
| Scheduled source slots | 24 |
| Intact frames replayed | 23 |
| Historical infrastructure failures retained | 1 |
| Display boxes retained without filtering | 93 |
| Unique same-class geometric candidate | 34 |
| Multiple-depth-surface abstention | 26 |
| No same-class reference within 0.9 m | 23 |
| Background/sign hypothesis | 10 |

Outputs: `reports/object_depth_integration_20260923_v1/`. The audit checks 124
input hashes, preservation of every original box, depth-estimator replay, and
separately coded transform and geometric-match arithmetic. It verifies the
computation, not physical pose accuracy or object correctness.

Verification: full regression suite **1,151 passed, 1 skipped**, no failures or
errors. One existing synthetic-depth invalid-multiply warning remains. Frozen
instrumentation snapshot v8 still validates; `git diff --check` passes.

No model rerun, GPU workload, live simulation, primary sample addition, human
label generation, validation release, or protected-world access was performed.
The original provider and Research 1/2 were not modified.

## Remaining engineering and scientific limits

1. The camera transform assumes the commanded stationary pose and existing
   rendering-camera offsets. Independent actual-pose/transform validation is
   still required before using this path for metric claims.
2. A central-box depth median can describe a wall or visible surface rather than
   a landmark reference point. The 26 mixed-surface cases abstain; the remaining
   estimates are not thereby proven correct.
3. There are still no doorway proposals above the original fixed threshold.
   This integration neither changes the detector nor remedies class coverage.
4. Raw OWLv2 matching scores are not joint correctness probabilities. The
   previously accepted calibration protocol has not been shown suitable for
   this redesigned observation channel. No rescaling or threshold relaxation
   was performed to manufacture coverage.
5. Human outcome review, actual model admission, sealed validation release and
   staged campaign gates remain in force. This is not research completion.

Next: validate the sensor transform and prepare a separately versioned detector
and confidence-contract feasibility step. Do not send this engineering panel
for bulk calibration labeling or activate it in the runtime.
