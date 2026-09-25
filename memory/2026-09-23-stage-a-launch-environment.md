# Stage A launch environment — debugging report

Status: DONE for import failure; rendered capture verification still required.

- Symptom: first dispatched Stage A assignment failed before simulator launch
  with `ModuleNotFoundError: rcn` through `episode_logger.monitor`.
- Root cause: sourcing the ROS overlays exposes episode_logger but not the
  Research 1 repository-root Python package `rcn`.
- Fix: add `/home/eao/risk-calibrated-nav` to the executor's process-local
  PYTHONPATH alongside R3 src/scripts. No R1/R2 or pinned source edits.
- Regression reproduction: `import run_live_episode` fails with the initial
  environment; the same import succeeds with the R1 repository root included.
- Retain the first assignment as infrastructure failure. Never replay it or
  count it as a nondetection. Continue only unstarted fixed assignments, with
  the next live batch serving as rendering verification.
- Historical source binding, approval, schedule, and result remain unchanged.

Second environment check found the repository-root install was a stale overlay:
it resolves language_nav_bringup but has no physical_sim.launch.py. The live
overlay is `ros_ws/install/setup.bash`. Both launch assets and the full import
chain now pass an explicit pre-dispatch check in launch_redesign_stage_a.sh.
The two affected dispatched assignments remain infrastructure failures, never
replayed. This is environment correction, not a scientific/protocol change.
