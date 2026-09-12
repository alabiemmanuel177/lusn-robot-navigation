# Read-only audit: physical INSPECT v2

Run: `reports/physical_live_episodes/r3-readable-inspect-dev10-20260911-v2`.
This audit creates documentation only. No code, source freeze, run evidence,
human labels or simulator state was changed. Summary, resource report, complete
adapter trace and controller bridge-shutdown log were present before auditing.

## Outcome

The short physical inspection completed successfully, followed by the required
fresh-anchor and two-second dwell gate. The policy still requested INSPECT and
the adapter correctly stopped at its one-inspection budget. Final reason:
`inspection budget exhausted; abstained`.

This closes the specific engineering check for an actually completed inspection
with post-viewpoint observation handling. It is not successful navigation,
successful instruction completion, detector calibration, or comparative evidence.

## Retained timeline (simulation nanoseconds)

| Event | Timestamp | Evidence |
|---|---:|---|
| Initial task-goal commit | 11508000000 | Adapter trace: goal `(7.5, -2.0)` |
| Inspection preemption requested | 11694000000 | Adapter trace |
| Commit cancellation confirmed | 11718000000 | Adapter trace and Nav2 cancellation log |
| Short INSPECT dispatched | 11718000000 | Goal `(1.107449562958621, -0.0037818164196892212)` |
| INSPECT completed | 13467000000 | Adapter trace and Nav2 `Goal succeeded` log |
| Fresh anchor observed | 15501000000 | Selected-route candidate: chair sequence 43 |
| Post-dwell policy decision / final abstention | 15561000000 | Measurements and adapter outcome |

Inspection travel duration was 1.749 simulated seconds. The first retained
post-completion decision satisfying both checks occurred 2.094 seconds after
completion; its anchor was 0.060 seconds old, within the unchanged three-second
freshness limit. The bound observation was:

`research3-landmark-bridge:r3geo_base_r010:v1:15501000000:dev_00-r010-blue-chair`

Source: `research3-landmark-bridge:r3geo_base_r010:v1`; entity:
`dev_00-r010-blue-chair`; observed position `(2.0515788506991113,
0.6311809707928273)`. The selected route was
`r3geo_base_r010_right_2`. Replaying `has_post_inspection_anchor` against retained
candidates succeeds. Three retained callbacks share the same final timestamp and
anchor identity; they are not three independent new observations. No second
INSPECT or subsequent navigation goal appears in the trace.

There were eight startup `stop_and_abstain` decisions before the first commit,
for missing/incomplete proposals or Nav2 assessments. None followed the commit.
The final stop was inspection-budget exhaustion, not a monitor-driven STOP.

## Independent measurements and limits

- 123 ground-truth samples; measured travel **0.4184554712250245 m**.
- Recomputed trajectory quality passes: maximum time gap **0.036 s**, maximum
  position step **0.009995889502644245 m**.
- Collision count **0**; timeout **false**; infrastructure failure **false**;
  no `failure.json` exists.
- Ordered instruction completion **false**, with no required gates crossed.
- Final measured position `(1.0096888021589017, 0.06892622210050416)`.
- Final position is **0.12183441721284613 m** from the dispatched inspection
  point. This is a diagnostic using the final sample, not a separately measured
  pose-at-completion or orientation-accuracy result.
- Summary task-goal error, goal reached, selected route and confirmed terminal
  execution are null. These are not zero-error claims. The robot did not finish
  the task route. A purely geometric final-to-task-goal distance is approximately
  **6.8121 m**, not a navigation-success score.
- The legacy adapter outcome's `distance=8.22818844509921` is planned route
  distance, not measured travel; its `started_at_ns=0` is not the retained
  inspection start. Use the independent measurements and execution trace above.
- No Research 2 prediction windows were recorded during this short episode;
  it therefore does not validate long-horizon predictor behavior or active
  monitor-driven cancellation. Existing safety thresholds were not modified.

Resource checks stayed below configured limits: CPU pressure at most 4.35,
load1 at most 8.7891 on 24 logical CPUs, available memory at least
23,442,372 KiB. GPU headroom and unchanged Research 2 performance remain explicitly
unproven in the retained resource report. All request-bound source hashes matched
the current files when checked; this audit made no source changes.

## Immutable evidence hashes (SHA-256)

All paths below are relative to the run directory.

| File | SHA-256 |
|---|---|
| `request.json` | `5695f2244f9b9363c3178820faa9df3d677d6fcf6ef4d10333388b8e0c8f431f` |
| `summary.json` | `6c51f60de0b16b8361f280f6afb5b4f31f37040572269f5ae0f3b1fef53bf5ef` |
| `measurements.json` | `e37031d4ba93dce7cf447758ac027fc9ed6bc51638b71f5547246bca328338e2` |
| `resource_guard.json` | `f880cea306aa7539ee2716a3eaa0760132a2e10da9b652caa249be4294853f65` |
| `research3/r3-readable-inspect-dev10-20260911-v2.trace.json` | `8c861f8685eaf92ae69a4337a78edd2a28a23952b7165b64567f6e1508ef7d5f` |
| `research3/r3-readable-inspect-dev10-20260911-v2.json` | `4c9e0050e7238cbd5c680d80b9fddb5ef8e712eb465b535eafd05701d502e921` |

No new functional bug is established by this run. The legacy adapter metric
limitations and short-run predictor coverage limitations remain disclosed.
