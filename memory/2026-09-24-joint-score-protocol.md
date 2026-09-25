# Joint-score protocol handoff

User requested finalization of the score-learning/collection protocol after
four-class engineering readiness. Delivered exact proposal R3-JSC-20260924-01:
`docs/SCORE_LEARNING_COLLECTION_PROTOCOL_20260924.md`.

Create-once packet: `reports/joint_score_protocol_20260924_v1/`.
Builder: `scripts/prepare_joint_score_protocol.py`.
Tests: `tests/test_joint_score_protocol.py`; all 24 targeted protocol/prototype
tests passed. Full regression report is separately generated under
`reports/joint_score_protocol_regression_20260924_v1.xml`.
Final full result: 1,242 passed, 1 skipped, zero failures/errors, existing
synthetic-depth warning only. Twelve packet/source pins checked without mismatch;
frozen v8 validated unchanged at 6b7bc9e5dd4f5289af88ee4524db3544d277eeeb6a0685177b12c128ef6fb49a.

960 rows: S400, C400, V160. Reuses old approved five-view pose metadata, not data,
labels, old camera profiles or world hashes. Fresh seeds 101/102, 201/202,
301/302. All actual per-wave source/asset/execution pins remain an arming gate.
Serial low-priority guarded collection; exact first synchronized frame, fixed
two-second TF delay, 90-second deadline, no consumed-attempt retries.

Important methodological proposal changes: upstream class-specific joint logistic
score, explicit class-specific depth features, numerical clipping for endpoint
matching scores, duplicate-entity groups abstain (no highest-score selection),
only acquisition-class unique candidates primary (never expected-ID filtering),
raw joint score is proposed P2/Coverage input; retain original matching-score
audits. Exact content duplicates cannot inflate quotas or cross roles unnoticed.
These changes require human scientific review, not fabricated acceptance.

Existing synthetic fitter remains synthetic-only; no real model fit. New one-frame
production adapter and feature extractor must be implemented/tested before arming.
Readiness candidate source files, v8 snapshot, R1/R2 and earlier evidence untouched.
Validation/protected content unopened; only predeclared pose metadata read.
Human observation reviews are necessarily staged S then C then V, since S labels
must freeze upstream model before C collection; no single end-of-study label batch.
