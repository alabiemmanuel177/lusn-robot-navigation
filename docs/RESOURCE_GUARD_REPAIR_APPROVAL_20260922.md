# One infrastructure decision needed to resume Stage 1

The four-worker feasibility collection attempted 24 of the fixed 80 views before
the prespecified stop-on-infrastructure-failure rule halted it. One process lookup
failed when an unrelated process exited during `/proc` enumeration. The other
completed captures retain exact-frame and raw-byte integrity checks.

## Requested scope

1. Apply only the demonstrated process-exit handling fix in
   `src/language_nav/live_resources.py`: change the handler at the PID cmdline read
   from `except FileNotFoundError` to
   `except (FileNotFoundError, ProcessLookupError)`.
2. Bind this additional source scope in a new approval record and new capture
   snapshot, with a narrowly updated snapshot validator/generator that recognizes
   this specific authorized revision. Preserve every historical source pin.
3. Run regression checks and readiness checks. Resume only the 56 not-started
   assignments in the original schedule under four-worker resource guards.
4. Preserve the failed attempt as infrastructure failure. Do not repeat it,
   replace it, add attempts, change the detector, alter confidence/camera/scene
   settings, lower calibration gates, release validation labels or enter protected
   worlds. Any further infrastructure failure again stops execution.

This fixes a process-monitoring race, not a scientific outcome. The candidate has
passed deterministic in-memory tests, including fail-closed permission errors
and continued detection of active Research 2 drivers. It has not been applied or
live-verified. Original source SHA-256:
`fc0ad9a3e249c2aeffbe2e64424d67230e9604bd588e48b12b9e88a2c3df4a0c`.
Proposed source SHA-256:
`a484706b8133c95a8c4f2ae90677a5246513d6d9e77eb7d8e6117cf1347df9aa`.

## Reply

“I approve the minimal resource-guard repair, the narrowly bound source repin,
and resuming the 56 unstarted assignments; retain the failed attempt without
replacement.”

Or decline/request a revision. Approval does not approve calibration, validation
release, a new primary-data amendment, comparative campaign or final results.
