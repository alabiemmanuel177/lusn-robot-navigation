# Hybrid candidate: a structural coverage failure

The repeated user instruction explicitly allowed raw-score pass-through as an
alternative to near-one assignment. That branch is now exactly implemented and
hash-frozen in `reports/hybrid_score_candidate_20260925_v1/candidate.json`.
This is a candidate snapshot, not scientific or runtime admission. The original
Wave S failure and 287 genuine human judgments are preserved unchanged.

## Completed work

Doorway uses the already fitted fixed logistic candidate. Chair/laboratory/office
use the original matching score identically, explicitly labeled uncalibrated.
No logits, thresholds, source detector, OCR or scene assets were modified.
39 hybrid and existing fitting tests passed. The full 287-emission S replay is
retained with class score meanings and original values; it is not C/V evidence.

## Why another unchanged C wave cannot fix the coverage gate

This is not a forecast inferred only from S outcomes:

1. The actual frozen OCR runner sets `text_score=0.5`.
2. The installed, source-pinned `RapidOCR.filter_result` retains only text scores
   greater than or equal to that threshold.
3. The entrance localizer copies the retained text score to `raw_score`.
4. The chosen upstream mapping is identity, so entrance input scores are >=0.5.
5. The unchanged coverage gate requires at least five scores in [0,0.5) for
   each class in C and V. The maximum for each entrance class is exactly zero.

The inspected-source argument was checked at the boundary using the actual OCR
filter with synthetic inputs, without loading inference models or generating
observation labels. Audit and source hashes:
`reports/hybrid_score_candidate_20260925_v1/ocr_support_audit.json`.
Confidence numerical clipping inside P2 does not alter upstream coverage counts.
Neither more workers, different simulator seeds nor broader execution authority
changes this bound. Constant-near-one scoring would also leave the low bin empty.

## Decision needed, not another generic permission

The supplied instruction permits a fitting bypass, but does not specify a
replacement C/V coverage/admission policy or authorize misrepresenting failure.
The remaining choice materially affects what the research can claim:

- Preserve the original four-class calibrated study: design and approve a new
  prospective observation/scoring study with attainable support and error
  diversity. It must disclose existing failures and cannot reuse validation to
  choose a method. It is not an unchanged C continuation or post-hoc S top-up.
- Narrow the study to descriptive/exploratory feasibility: retain the hybrid
  candidate and report the calibration failure without runtime calibration
  admission. Any fresh C/V descriptive study and navigation comparisons need
  their own exact estimands; they cannot retain the original validated-B5 claim.

Recommendation: explicitly choose the intended scientific scope before any
further live wave. Do not spend another400 attempts claiming they can satisfy
an unreachable gate. No existing gate, human verdict or detector threshold has
been altered. No C/V captures or protected data were accessed in this work.

Actual future C/V human labels and the reviewer-held V key/release remain separate
dependencies whichever scientifically defensible scope is selected. Existing
blanket autonomy cannot supply those data or certify achieved final results.
