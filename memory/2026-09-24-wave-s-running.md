# Authorized Wave S started

Latest user: proceed, use workers/resources, no stalling. Approved protocol still
requires serial capture; no amendment inferred from generic resources instruction.
24CPU, ~25GiB available, pressure0,99GiB disk at launch.

New external scheduling wrapper scripts/run_authorized_wave_s.py (not editing any
manifest-pinned source) tested with4new tests plus13driver/binding tests:17pass.
Serial fixed400schedule then existing prepare/detector/OCR/export chain. No retry,
new labels, model fitting or C/V. Stops and writes blocked.json on safety failure,
child nonzero, incomplete accounting or unclean shutdown. Ordinary terminal
infrastructure-failure attempts remain consumed and do not get replacements.

Exec session24688; supervisor PID3976936. Started host ROS/Gazebo scoped escalation
with ROS/R1/R3 environment sourced and PYTHONPATH preserved; nice19, isolateddomain218.
Live control reports/joint_score_wave_s_supervisor_20260924_v1 (launch.json,
closed-NNN.json, capture-NNN.log, eventual complete.json or blocked.json).
Primary reports/joint_score_wave_s_primary_20260924_v1. Eventual offline output
reports/joint_score_wave_s_primary_inference_20260924_v1.

Do not start another campaign root or rerun consumed attempts. On resume inspect
actual process+control status first, poll exec session if available. Sourceguard
checks wrapperhash betweenattempts; neveredit runningwrapper. Scheduler refuses
automatic resume/restart if outputroot alreadyexists. Any genuine interruption
requires accounting-preserving continuation design, not reset.
