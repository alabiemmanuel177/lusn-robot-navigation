# Research 3 Final Closure: Descriptive and Exploratory Feasibility Deliverable

**Reviewer**: Emmanuel Alabi Olasubomi  
**Role**: Researcher  
**Timezone**: Africa/Lagos  
**Date**: 26 September 2026  
**Scope Decision**: Option 2 — Narrow study scope to descriptive and exploratory feasibility; formally close Research 3.

## Executive Summary of Findings

1. **Structural OCR Support Limitation**:
   Frozen upstream thresholding in RapidOCR (`text_score >= 0.5`) mathematically truncates entrance input support to [0.5, 1.0]. Because the localizer copies the retained text score directly to `raw_score` and identity pass-through is used, populating the required [0, 0.5) bin for laboratory and office entrances is structurally impossible (0 emissions vs 5 required). Unchanged collection waves cannot satisfy Coverage v2.
   Audit: `reports/hybrid_score_candidate_20260925_v1/ocr_support_audit.json`.

2. **Wave S Clean-View Precision Saturation & Error Localization**:
   Grounding DINO and RapidOCR achieved 100% precision on chairs and signage across 261 views evaluated by human review (99 chair, 84 lab entrance, 78 office entrance; 0 incorrect). Geometric localization error was strictly isolated to doorway portal void penetration (20 correct, 6 incorrect out of 26 doorway emissions), where depth rays penetrate the open portal void rather than striking jamb boundaries.
   Zero negative outcomes for three classes prohibited multi-class supervised logistic calibration under the pre-registered outcome floor (>= 5 incorrect per class).

3. **Exploratory Hybrid Candidate**:
   Retained in `reports/hybrid_score_candidate_20260925_v1/candidate.json`. Combines the fitted 5-feature doorway logistic model with raw-score pass-through for chairs and signage. Retained strictly as an exploratory feasibility candidate; not admitted for runtime robot navigation.

4. **Final Closure & Policy Actions**:
   - Research 3 is formally terminated under the descriptive and exploratory feasibility deliverable.
   - Wave C (calibration) and Wave V (validation) are not scheduled or launched.
   - Four-class runtime calibration is not claimed.
   - Blockers B03 and B09 are formally resolved.
   - All dangling locks and tasks have been cleared.
