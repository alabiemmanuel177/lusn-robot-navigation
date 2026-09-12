# How to prepare and run separately authorized physical held-out work

Use these commands only after the relevant genuine approval is supplied. The
three approvals are independent; see the
[schema and safety reference](PHYSICAL_HELDOUT_RUNTIME.md). The placeholders below
are not existing approved artifacts.

## Prerequisites

Work from the repository root with its Python dependencies available. A live run
also needs the installed Research 1, Research 2 and Research 3 ROS overlays,
Research 2 idleness, resource headroom and the settled source/configuration pins.
Complete non-protected review, calibration and scientific protocol decisions
before requesting live held-out authorization.

## Commands

1. Verify the available interfaces without opening protected inputs:

   ```sh
   PYTHONPATH=src python3 scripts/build_authorized_heldout_assets.py --help
   PYTHONPATH=src python3 scripts/run_authorized_heldout_episode.py --help
   PYTHONPATH=src python3 scripts/audit_physical_heldout.py --help
   ```

2. With build-only approval, create the protected derivatives and pending schedule:

   ```sh
   PYTHONPATH=src python3 scripts/build_authorized_heldout_assets.py \
     --authorization /path/to/build-authorization.json \
     --authorization-sha256 APPROVED_BUILD_AUTHORIZATION_SHA256
   ```

   Check `build_result.json` in the plan's new output directory. Preserve the
   original source and intermediate absence proof. Do not treat the generated
   schedule template as a frozen campaign: supply genuine calibration and freeze
   the execution order through separate runtime approval.

3. With that separate runtime approval, validate one exact scheduled episode:

   ```sh
   PYTHONPATH=src python3 scripts/run_authorized_heldout_episode.py \
     --authorization /path/to/runtime-authorization.json \
     --authorization-sha256 APPROVED_RUNTIME_AUTHORIZATION_SHA256 \
     --episode-id EXACT_APPROVED_EPISODE_ID \
     --prepare-only
   ```

   This prints a request and does not launch ROS. Only once live execution is
   genuinely approved and the resource gates pass, use the same command without
   `--prepare-only`. The runner writes a new run directory; it does not resume or
   replace an existing attempt.

4. Preserve each request, summary, final measurements and pre-evaluation sealed
   measurements. Create explicit hash-bound assignments and use the separate
   [post-execution audit command](PHYSICAL_HELDOUT_AUDIT.md). A passing audit means
   the scheduled measurements were verified, not that the robot succeeded on
   every task or that inferential analysis is complete.

## Verification and troubleshooting

The offline regression tests create synthetic fixtures only:

```sh
PYTHONPATH=src pytest -o addopts='' -q \
  tests/test_physical_heldout_runtime.py \
  tests/test_authorized_heldout_asset_builder.py
```

If an approval, source or asset checksum fails, retain the evidence and reconcile
it through a new explicit approval. Do not edit old freezes to make them pass.
If the source directory or run output already exists, inspect the retained
attempt; do not delete it to obtain a clean retry. Research 2 activity or an owned
Research 3 survivor blocks dispatch: wait for safe idleness rather than bypassing
the guard. A missing or null calibration hash requires genuine non-protected
calibration, not protected labels. An unresolved measurement audit requires the
missing or corrected evidence, never a manufactured outcome.
