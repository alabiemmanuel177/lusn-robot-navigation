# Wave S driver prelaunch handoff

User explicitly authorized execution prospectively in the current conversation.
Bounded task complete: driver wired, all400 static clearances passed, four live
dev/r001/seed29 engineering views captured, unchanged detector/OCR integration
completed, exact manifest authority bound. No primary attempts started; no jobs
remain. See docs/WAVE_S_DRIVER_PREFLIGHT_20260924.md for paths and launch command.

New sources: joint_score_wave_s_driver.py, prepare_joint_score_wave_s_driver.py,
joint_score_wave_s_inference.py, bind_wave_s_execution.py. Existing pinned core
and frozen v8/R1/R2 untouched. Assets v3 and preflight v2 are successful versions;
failed/partial assets v1,v2 and preflight v1 remain. Do not edit pinned new sources
without invalidating/repeating the necessary preflight and authority binding.

Investigate skill: first exact-frame TF failure root cause was a newly constructed
buffer after AMCL initialization. AMCL future-dates map->odom; at frame11.001s
the earliest new sample11.902s cannot be repaired by waiting2s. Actual tf2 isolated
reproduction confirmed earlier buffered sample resolves exacttime lookup. Fix
driver-only: create listener/buffer during localization, transfer to collector.
Fresh subprocess per preflight view also eliminates reused-context staleDDS graph
blocking observed despite no surviving domain218processes. Four freshviews pass.
Pre-fix driver archive in assetsv2 hashes exactly to failed-run source config.

Preflight inference3emissions(chair/lab/office), doorwayabstention; NOT accuracy or
coverage. No emission-success quota added. All400 still must be collected once.
Fullsuite1311passed1skipped (1312total), nofailure/error; olddepthwarningonly.
13newtests. Original32componentpins/51readinesspins match, v8same6b7bc9e5….

Execution manifest canonical SHA707e1828780277f991e62f506e4081cdbbfa67e4c7004459e4ef592aed617028
under reports/joint_score_wave_s_execution_20260924_v1. Approval receipt derived
from userprospectiveinstruction, not fabricated futurehumaninspection/signature.
Sonly400, noC/V/protected/modelapproval. No need ask again forS execution.

Watch lifecycle contact semantics: collector summary closes at fixed-frame TF;
monitor readiness/contact checks surround capture. Staticpreflight is not a live
routecollision benchmark. Scheduler must not evade no-retry via newoutputroots.
No all400 scheduler daemon was started in this bounded prelaunch task.
