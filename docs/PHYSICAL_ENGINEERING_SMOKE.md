# Remaining physical engineering smoke checks

This is bounded engineering contract verification, **not a comparative campaign,
performance estimate, seed/power justification or protocol freeze**. It introduces
no runtime changes and does not modify the frozen source files.

`reports/physical_engineering_smoke_plan_v1.json` reserves eleven new dev10 runs:

- B6: truthful original, truthful paraphrase, ambiguous reference, missing landmark,
  relation corruption, topology corruption and false inserted clause.
- B1, B2, B4 and B5: truthful original only.

The eighth B6 condition, attribute corruption, points to the retained
`r3-readable-inspect-dev10-20260911-v2` evidence: a completed short inspection,
fresh post-completion anchor after dwell, and safe inspection-budget abstention.
It is not counted as task success or evidence for other conditions. Older truthful
and missing-landmark attempts are historical references only; they do not remove
any of the eleven new planned checks. Differences in source/evidence provenance
must remain visible rather than pooling historical runs into a campaign result.

Missing-landmark uses `data/physical_absence_worlds_v1/base-r010`, including its
actual chair-removal and occupancy-map intervention. Other cases use
`data/physical_worlds_readable_v1/base-r010`. The original absence derivative does
not acquire readable signage implicitly. All cases retain the dev10 engineering
palette, tolerance 10, camera FOV 2, simulator seed 1, instruction seed 0, timeout
90 seconds and ROS domain 89. No calibration or risk/STOP threshold is changed.

Commands are reconstructed for the owned physical runner, not executed from
arbitrary plan strings. Each case invokes the current offline `prepare` function
and compares source/asset pins immediately before execution. Profile and runtime
hash changes fail closed. All cases must remain in the exact eleven-case matrix.

Execution is serial, `nice 15`, with OMP/OpenBLAS/MKL/NumExpr limited to two threads.
Each run must pass the resource guard. Coexistence with Research 2 requires the
explicit flag; otherwise Research 2 must be idle. Existing run directories are
reported as skipped, never relaunched or counted as successes. Ordinary measured
failures and timeouts remain retained and may be followed by the next case.
Infrastructure failures, resource violations or missing/unverifiable measurement
evidence halt the batch. Logs and a flushed attempt journal remain even on failure.
Cleanup belongs only to the newly launched Research 3 process group.

Prepare a fresh plan:

```sh
PYTHONPATH=src python3 scripts/physical_engineering_smoke.py prepare --output reports/physical_engineering_smoke_plan_v1.json
```

After the capture batch finishes and resource headroom is checked, explicitly run
under the sourced ROS overlays (the output directory must not exist):

```sh
PYTHONPATH=src python3 scripts/physical_engineering_smoke.py run --plan reports/physical_engineering_smoke_plan_v1.json --output reports/physical_engineering_smoke_batch_v1 --allow-coexistence-trial
```

Planning and unit tests launch no Gazebo process. Review each retained outcome for
contract behavior; do not tune thresholds to make these checks pass or treat a
single-layout engineering sample as scientific validation. Human review, proper
detector calibration, final experiment design and protected comparative evaluation
remain distinct requirements.
