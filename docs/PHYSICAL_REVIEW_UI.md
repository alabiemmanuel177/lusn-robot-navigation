# Physical-world human review UI

This is a separate localhost application for the new consolidated inventory.
It never opens or changes old Research 3 review worksheets or human labels.
No server is automatically launched by importing the module or running its tests.

## Preview first; review only after policy approval

The current workflow reviews category, stable entity association and pose as three
separate judgments. An inventory item marked `ready_for_human_review` has passed
image QA only. Joint evidence and an explicitly approved policy are also required.
A draft policy enables preview only: **no judgments, including Unreviewable, may
be saved**. Do not spend time reviewing all items while acceptance rules are pending.
No pose tolerance or treatment of catalogue-supplied yaw is chosen automatically.

The inventory must come from `prepare_consolidated_review.py` and contain genuinely
individually visually audited items. Supply the exact machine-QA JSONL used for
that inventory. Startup and every state/image/save operation recompute the
non-protected exact joins and QA bindings. A stale source frame, task, request,
inventory or QA input blocks review. Only `ready_for_human_review` items appear;
missing coverage and rejected items remain in the original inventory.

```sh
python3 scripts/serve_physical_review.py \
  --inventory /path/to/consolidated_inventory.json \
  --qa /path/to/actual_machine_visual_qa.jsonl \
  --evidence /path/to/joint_evidence.json \
  --policy /path/to/joint_policy.json \
  --progress /path/to/new_physical_human_progress.jsonl
```

Progress creation is exclusive: existing files are not overwritten. To reopen the
same review, pass `--resume`; inventory, QA, evidence and policy hashes must match the progress
header. The server binds only to `127.0.0.1`, defaults to port 8793, and has no
hosting or deployment step. Stop it with Ctrl-C.

Prepare evidence first with `prepare_joint_review_evidence.py --inventory PATH
--output NEW_PATH`. After genuine policy approval, create a separate progress file;
do not silently rebind a draft-policy preview header to an approved policy.

## What the person sees

The full camera frame dominates the page. A browser SVG places the detector's
crosshair in the original image coordinate system; hiding the crosshair leaves
the source image visible. RGB/BGR source bytes are decoded losslessly to an
in-memory PNG with original dimensions and row stride. No raster retouching,
colour answer key or expected-route answer appears. A full-width coordinate
diagram uses numbered catalogue references and a reported x/y cross, with a
readable full-ID legend. Catalogue IDs, regions and poses are reference evidence,
not automatic human labels. Yaw is catalogue-supplied, not independently estimated.

Claimed category, detector source, run, map and observation ID remain visible.
Each of the three dimension selectors offers Correct, Incorrect and Unreviewable
with no default. Legacy category-only buttons are hidden and disabled. A reviewer
name and all three choices are required. Overall correctness is true only if all
three are correct, false if any is incorrect, and null otherwise. Unreviewable
alone is not converted into a false label. Optional notes
explain ambiguity. Saving does not auto-advance, so the person can confirm what
was recorded before moving on.

## Persistence and limits

GET requests do not write labels. PATCH accepts only reviewer name, explicit
`dimension_verdicts` and notes, and needs a per-session review token and local host/origin.
Each save appends an fsynced v2 event with task/frame, evidence/item-evidence,
policy bindings and UTC timestamp. Missing policy approval blocks every save;
approved policy with missing reference evidence permits only all-Unreviewable.
Corrections append another event; earlier decisions remain intact. The latest
event is displayed, while raw sources and the consolidated inventory stay
unchanged. Local access is not identity authentication: the application records
the name supplied by the human; it does not certify that person's identity.

Opening this page is not calibration or detector validation. A separate exporter
must validate the finished audit, preserve unreviewable cases and missing strata,
and apply the frozen calibration protocol. Tests use synthetic records only;
test verdicts must never be represented as genuine human review.

## Verification

The host ran 26 review tests successfully. Actual desktop browser QA passed for
corrected items 1 and 60, Next unreviewed, disabled/hidden legacy controls and the
pending-policy preview state. Mobile rendering has **not** been tested. The preview
server is closed; its progress contains only a header, zero verdicts. Separately,
all 46 retained capture frames were individually visually inspected and all 60
selected joint evidence records are complete. These are not human labels.

Policy authority, genuine judgments, coverage requirements, calibration and
campaign/release gates remain separate. See
[PHYSICAL_JOINT_REVIEW.md](PHYSICAL_JOINT_REVIEW.md) and
[PHYSICAL_JOINT_CALIBRATION.md](PHYSICAL_JOINT_CALIBRATION.md).
