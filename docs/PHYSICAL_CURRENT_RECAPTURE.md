# Fresh current-source capture workflow

The runtime source freeze now includes one shared 79-file Research 3 source/interface
map for both camera settings and episode requests. It includes the previously
missing semantic-route node, belief/instruction/monitor nodes, provider wrapper,
core Python dependencies and message definitions. The separate provider snapshot
pins 16 explicit R1 source/config files, three active bridge modules and two active
semantic-perception transformation modules. It does not claim full binary/model,
ROS/Gazebo, Research 2 or environment closure.

The immutable preparation directory is
`reports/fresh_current_capture_20260911_v1`. Original `plan.json` has 42 views:
30 development and 12 gated validation. `recapture_plan.json` additionally records
four final development stress views, for 46 total; `stress_commands.json` retains
those four commands separately. All poses, camera palettes, FOV, world assets and
stress derivative versions are preserved from the selected historical requests.
Every run ID is new. No old request, freeze, review journal or QA file is replaced.

`current_source_snapshot.json` has SHA256
`4eb51067c9d067954f4c0264e904993137d1be8e50f49401fc08870c8069056c`.
The source/config archive supplied separately by the packaging tool has SHA256
`db94b72f6430f8823234e70de8e49764449ec73c4d46d6dd9f9a2da1d26cadbc`.
It retains the exact 100 source/config payload members matching this snapshot.

## Dispatch exactly one case

Only the root operator runs live captures. The helper does not run on import or
during plan preparation. After sourcing the established ROS overlays:

```sh
PYTHONPATH=src python3 scripts/prepare_current_capture_plan.py dispatch \
  --directory reports/fresh_current_capture_20260911_v1 \
  --run-id r3-current-v1-r005-chair \
  --plan-sha256 8d5e121806fa7e741bdab1d4ace246a0f27321c33435ee23ebfbeac3a19b14d5 \
  --allow-coexistence --output reports/fresh_current_dispatch_r005_chair_v1
```

Change only the explicit planned run ID and new dispatch-output directory for each
case. The helper acquires the existing Research 3 lock, refuses a surviving owned
runner, and passes the lock descriptor to its single child. It uses nice 15 and
four thread caps of two, current source/provider checks, measured headroom and
create-once start/log/finish or failure records. No existing run is retried or
replaced. The explicit coexistence flag is for bounded stationary capture, not
campaign-wide permission or proof of zero effect on Research 2. Without it, R2
must be idle. If using the older direct CLI, the operator must supply the equivalent
outer lock/orphan guard and `--capture-source-freeze` explicitly.

The runtime rejects mismatched source/provider pins and unexpected active provider
import resolution before launching. It rechecks source hashes at capture-loop
checkpoints and records them in `capture_summary.json`. This establishes no change
observed at those checks, not a continuous attestation between checks.

## New validation freeze after six fresh development checks

First individually inspect new chair views from maps 1–4 and the new laboratory
and office views from map 10. Do not reuse old visual attestations. Only after
those checks are genuinely complete may the operator invoke:

```sh
PYTHONPATH=src python3 scripts/freeze_engineering_camera_settings.py \
  --plan reports/fresh_current_capture_20260911_v1/plan.json \
  --output reports/fresh_current_camera_settings_20260911_v1 \
  --evidence-run reports/physical_live_episodes/r3-current-v1-r001-chair \
  --evidence-run reports/physical_live_episodes/r3-current-v1-r002-chair \
  --evidence-run reports/physical_live_episodes/r3-current-v1-r003-chair \
  --evidence-run reports/physical_live_episodes/r3-current-v1-r004-chair \
  --evidence-run reports/physical_live_episodes/r3-current-v1-r010-laboratory_entrance \
  --evidence-run reports/physical_live_episodes/r3-current-v1-r010-office_entrance \
  --development-visual-check-complete
```

For each planned validation dispatch, add
`--validation-settings reports/fresh_current_camera_settings_20260911_v1` to the
one-case helper. It requires fresh planned development evidence with matching
R3/provider snapshots and the new freeze's exact validation view/source bindings.
The old freeze continues to reject current runtime source hashes. The new freeze
is camera engineering preparation, not confidence calibration or study approval.

## Post-capture source audit

After capture, run `prepare_current_capture_plan.py audit` with `--directory`,
`--archive`, `--archive-sha256` and a new `--output`. It compares each of the 46
planned requests against the original snapshot and retained source archive,
requires matching provider pins and source-checkpoint evidence, and retains
missing/incomplete runs as blockers. It never substitutes current workspace
hashes for historical request provenance. An intermediate audit remains incomplete
until every planned source-bound capture is present; exit 2 is expected then.

This audit does not grant media reviewability. Every fresh run still needs exact
provider/media association, individual visual QA and a newly bound review packet.
No correctness labels or QA attestations are generated by this workflow. Genuine
human labels, approved coverage/exclusion policy, calibrated confidence and the
comparative/held-out protocol remain separate gates.
