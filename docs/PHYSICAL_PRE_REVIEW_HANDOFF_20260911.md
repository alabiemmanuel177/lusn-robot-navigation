# Physical-world pre-review handoff — 11 September 2026

All 46 fresh current-source captures are complete. The review packet is assembled,
but **human review is not yet open**: the joint-observation acceptance policy and
calibration sampling/coverage rules still require a genuine decision before labels.
No human verdicts have been entered. The source freeze is
`reports/fresh_current_capture_20260911_v1/current_source_snapshot.json`.
The pre-capture source archive is `reports/fresh_capture_sources_20260911_v1.tar.gz`
(SHA-256 `db94b72f6430f8823234e70de8e49764449ec73c4d46d6dd9f9a2da1d26cadbc`).
It retains 79 R3 sources/interfaces, 16 named provider source/config files,
three active bridge files and two active image-transform files. This is local
source-byte provenance, not full external environment reconstruction. The older
packet and archive remain historical artifacts and must not be used to claim
calibration of the current runtime.

The separate [held-out runtime reference](PHYSICAL_HELDOUT_RUNTIME.md) and
[authorized execution how-to](howto-authorized-physical-heldout.md) document
implemented, synthetic-tested tooling; no real held-out experiment is claimed.

## Human review packet

`reports/physical_review_packet_20260911_v2` contains the consolidated inventory,
exact-frame machine visual QA, explicit sampling policy and hash-bound manifest.
There are 60 targets across 46 runs and 14 development/validation maps: 56 ordinary
targets (chair, doorway, laboratory entrance and office entrance per map), plus
four deliberate development-only shape-stress targets. All 3,960 provider rows
remain available; selection does not silently delete other observations.

The assistant inspected every ordinary capture image and each selected pixel,
then all four final stress images individually. These are presentation and
category-decidability checks, not independent stable-instance/pose verification
or human correctness labels. No review verdict or reviewer identity was entered.

Independent binding audit:
`reports/physical_review_packet_20260911_audit_v2.json`.
The selector and Next unreviewed control make every item directly accessible;
resume starts at the first pending item. Frontend-design guidance informed these
small navigation improvements while retaining neutral, image-first presentation.
The actual desktop preview was rechecked after correcting legacy-button visibility,
policy-aware image status and coordinate-diagram legibility. Item 1 and item 60
display the corresponding frame/claim/reference; Next unreviewed returns to item 1
with zero reviews. No real mobile-device validation is claimed. Full Python suite:
781 passed, one sandbox socket skip; separate host-side review suite: 26 passed.

Joint reference evidence for all 60 items is in
`reports/physical_joint_review_20260911_v1/joint_evidence.json`.
The associated `joint_policy.json` is explicitly a draft with no invented pose
tolerance or human approval. Category, stable association and pose must each be
reviewed; reported yaw is copied from the catalogue, not independently measured.
See [joint review contract](PHYSICAL_JOINT_REVIEW.md).

The following command starts a **preview only**, with saving disabled. If its
create-once journal already exists, use `--resume`. Do not run two servers:

```sh
python3 scripts/serve_physical_review.py \
  --inventory reports/physical_review_packet_20260911_v2/inventory.json \
  --qa reports/physical_review_packet_20260911_v2/combined_visual_qa.jsonl \
  --evidence reports/physical_joint_review_20260911_v1/joint_evidence.json \
  --policy reports/physical_joint_review_20260911_v1/joint_policy.json \
  --progress reports/physical_joint_review_20260911_v1/preview_progress.jsonl \
  --port 8793
```

Open http://127.0.0.1:8793/ on this machine. Do not start another server while that
port is already serving the packet. Do not spend time judging items while the
policy is pending. Once genuinely approved, use a separately saved approved policy
and a new joint-review journal; do not mutate the preview's pinned policy. No answer
is preselected. Old journals are neither relabelled nor merged into this packet.

## Interpretation and downstream gates

The four-stage plan is **not complete**. Engineering preparation and a scientific
result are different deliverables:

| Stage | Delivered now | Evidence/authority still required |
| --- | --- | --- |
| 1. Runtime/world integration | Geometry-faithful readable worlds, route alternatives, runtime wiring, INSPECT and engineering smoke checks | Full multi-world campaign validation; point-goal/localization limitations remain visible |
| 2. Detector validation | 46 current-source captures, 60 individually presentation-checked targets, joint reference evidence, review/export/fitter/admission tools | Prespecified joint rubric and coverage policy, genuine labels, adequate coverage, calibration validation/freeze |
| 3. Comparative and held-out campaign | Draft protocol, guarded serial executor, authorized held-out builder/runtime, sealed measurement audit | Scientific design and sample/seed decisions, frozen calibration/protocol, R2-idle resource gate, explicit held-out authorization, actual runs |
| 4. Analysis and reproducible release | Outcome export, analysis/readiness tools, engineering source/evidence archive | Complete measured campaign outcomes, approved inference and limitations, final scientific release |

Before requesting labels, a human with protocol authority must decide category and
stable-association acceptance, positional acceptance and the treatment of
catalogue-supplied yaw, plus the sampling/coverage/exclusion policy. These are not
60 repetitive labeling tasks and cannot be replaced by an assistant-signed
approval. After these choices, use the exact joint-review/export/candidate-fit
workflow in [joint calibration](PHYSICAL_JOINT_CALIBRATION.md). If coverage is
insufficient, collect the additional nonprotected evidence allowed by that
prespecified policy; do not relax it after seeing outcomes.

The detector is the simulated RGB-D colour-marker bridge, not a learned shape/text
recognizer. Readable LAB/OFFICE lettering supplies human context. Stress derivatives
deliberately alter visible marker presentation and add spheres/cylinders while
preserving collision geometry and task identity. Earlier stress revisions remain
separate engineering attempts; the final four selected revisions are not random
natural errors, approved calibration negatives, or evidence of recall coverage.

The camera/viewpoint/source freeze is not confidence calibration. Genuine review
must be exported through `export_physical_human_review.py`, with prespecified
coverage and exclusion requirements; see [export instructions](PHYSICAL_HUMAN_EXPORT.md).
The current sample may require additional evidence after those requirements are
agreed. Do not promise that 60 verdicts alone guarantee calibration readiness.

Scientific decisions in `physical_experiment_design_draft_v2.yaml` remain unapproved:
primary comparison, meaningful effect, inference/multiplicity, replication/seeds
and power inputs. See [proposed decisions](PHYSICAL_DESIGN_DECISIONS_PROPOSED.md).
After genuine labels and approved coverage, fit/check/freeze calibration, freeze
the experiment protocol, run the comparative and held-out campaign, then analyze
and issue the final reproducible research release. An engineering archive is not
that completed release. No held-out live results or labels were used for this
capture/calibration preparation. Earlier unrestricted tests did touch reserved
catalogue metadata for a refusal check and authored held-out corpus definitions;
the physical refusal test now uses a synthetic fixture. See the
[test-access accounting note](../memory/2026-09-11-heldout-audit-boundaries.md).

## Completed engineering smoke checks

The independent audit is
`reports/physical_engineering_smoke_audit_20260911_v1.json`. All 11 planned cases
have measured outcomes: ten original runs plus one separately identified retry.
The interrupted original setup remains the twelfth retained attempt, not a
discarded or silently replaced result. Nine measured runs complete the ordered
instruction; five meet the independent point-goal/navigation criterion. No
measured collision, timeout or infrastructure failure occurred in the eleven
completed runs. This single-layout matrix is descriptive engineering evidence,
not a comparative performance estimate or a power/replication justification.

External batch-parent termination was observed; its origin is unknown. A briefly
overlapping new attempt was stopped after an earlier surviving child was found.
The updated executor uses a child-inherited lock, checks for live R3 runners,
and defaults to one new dispatch per invocation. Historical zero overlap is not
claimed. See [interruption report](../memory/2026-09-11-smoke-parent-interruption.md).

## Resource isolation

Development smoke checks and stationary captures use serial, low-priority R3-owned
processes, domain 89 and explicit bounded coexistence guards. R1/R2 files and jobs
are not edited, restarted or terminated. CPU/memory headroom is measured; GPU
telemetry and unchanged R2 performance are not established. Full campaign execution
retains its R2-idle gate rather than inheriting this bounded-trial permission.

For the 46 fresh captures, 777 recorded resource samples show minimum available
RAM 23,913,988 KiB (22.81 GiB), maximum CPU pressure avg10 3.7%, and maximum load1
11.466 on 24 logical CPUs. All captures report no motion commands and zero contact
collisions. Stationary zero-contact evidence is not navigation collision validation.
