# Phase 1 Rubric Usability and Calibration Deficit Audit
**Protocol / Amendment Reference:** R3-CA-20260911-01  
**Reviewer:** Emmanuel Alabi Olasubomi  
**Role:** Researcher (Lead Peer Reviewer)  
**Date:** 2026-09-12  
**Target Package:** `research3_reviewer_kit_v1`  
**Pilot Return Hash (SHA-256):** `24f80c5a553eb15e414ebefa363b55246eefc6a0379609265e7282f7eaec52e0`  

---

## 1. Executive Summary

This audit constitutes the formal Phase 1 human review and usability assessment of the 60-observation landmark perception pilot dataset (`research3_reviewer_kit_v1`), in strict compliance with the Research 3 calibration expansion framework.

All 60 observations have been systematically evaluated along three orthogonal evaluation axes:
1. **Category Classification** (Semantic identity verification)
2. **Entity / Instance Association** (Correspondence to specific catalogue landmark IDs)
3. **Reference-Point Consistency / Pose** ($d \le 0.35\text{ m}$ Euclidean planar distance bound; $10^{-6}\text{ rad}$ yaw metadata consistency check)

The pilot review return package `my-review-return.zip` was successfully compiled and cryptographically verified against the protocol authority specification. 

The empirical findings confirm:
- **Rubric Discriminative Validity:** The $0.35\text{ m}$ inclusive reference-point threshold cleanly discriminates valid sensor detections (which exhibit small physical offsets of $0.0847\text{ m} - 0.1483\text{ m}$ due to camera-depth projection against obstacle surfaces) from engineered diagnostic stress distractors ($0.6012\text{ m} - 0.8465\text{ m}$).
- **Usability & Completeness:** Zero observations were classified as unreviewable; sensor RGB-D streams, camera intrinsics/extrinsics, and catalogue coordinate transforms provided unambiguous evidence across all 60 trials.
- **Coverage Deficit Proof:** The pilot dataset exhibits severe, structural coverage shortfalls under Calibration Coverage Policy v2 (0 items in $[0, 0.5)$, 1 item per entrance class in $[0.5, 0.8)$, and exactly 1 negative item per class). This proves that the pilot alone cannot support reliable calibration fitting or validation, mandating the execution of Amendment R3-CA-20260911-01.

---

## 2. Phase 1 Pilot Evaluation & Per-Observation Breakdown

The pilot dataset comprises 60 landmark observations across 4 semantic classes: `chair` (15 targets), `doorway` (15 targets), `laboratory_entrance` (15 targets), and `office_entrance` (15 targets).

### 2.1 Nominal Targets (Items 0 to 55)
- **Observations:** Items 0 through 55 represent nominal viewpoints across development environments.
- **Category:** All 56 nominal observations were confirmed as `correct` (100% semantic classification accuracy).
- **Entity Association:** All 56 nominal observations matched their designated catalogue landmark entity (`correct`).
- **Pose / Reference-Point Consistency:**
  - Planar Euclidean distances to reference coordinates: $\min d = 0.0847\text{ m}$, $\max d = 0.1483\text{ m}$, $\text{mean } d \approx 0.116\text{ m}$.
  - Every nominal detection falls strictly within the $d \le 0.35\text{ m}$ inclusive threshold.
  - Yaw orientations matched catalogue metadata exactly (difference $\Delta\theta = 0.0\text{ rad} < 10^{-6}\text{ rad}$).
  - All 56 nominal items were labeled `pose: correct`.
- **Joint Verdict:** All 56 nominal items achieved `joint: correct`.

### 2.2 Diagnostic Stress Distractors (Items 56 to 59)
Items 56 through 59 were specifically engineered diagnostic stress distractors designed to test rubric sensitivity to spatial displacement:
- **Item 56 (`chair_dev_map10_seed2_d0`):**
  - Category: `correct` (true chair present in RGB frame)
  - Entity Association: `correct` (associated with target entity)
  - Pose: $d = 0.6012\text{ m} > 0.35\text{ m}$. Labeled `pose: incorrect`.
  - Joint Verdict: `incorrect`.
- **Item 57 (`doorway_dev_map10_seed2_d0`):**
  - Category: `correct` (true doorway present in RGB frame)
  - Entity Association: `correct` (associated with target entity)
  - Pose: $d = 0.8465\text{ m} > 0.35\text{ m}$. Labeled `pose: incorrect`.
  - Joint Verdict: `incorrect`.
- **Item 58 (`laboratory_entrance_dev_map10_seed2_d0`):**
  - Category: `correct` (true lab entrance present in RGB frame)
  - Entity Association: `correct` (associated with target entity)
  - Pose: $d = 0.7638\text{ m} > 0.35\text{ m}$. Labeled `pose: incorrect`.
  - Joint Verdict: `incorrect`.
- **Item 59 (`office_entrance_dev_map10_seed2_d0`):**
  - Category: `correct` (true office entrance present in RGB frame)
  - Entity Association: `correct` (associated with target entity)
  - Pose: $d = 0.7595\text{ m} > 0.35\text{ m}$. Labeled `pose: incorrect`.
  - Joint Verdict: `incorrect`.

### 2.3 Summary of Pilot Outcomes
| Semantic Class | Evaluated Observations | Joint Correct | Joint Incorrect | Unreviewable | Negative Rate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `chair` | 15 | 14 | 1 (Item 56) | 0 | 6.67% |
| `doorway` | 15 | 14 | 1 (Item 57) | 0 | 6.67% |
| `laboratory_entrance` | 15 | 14 | 1 (Item 58) | 0 | 6.67% |
| `office_entrance` | 15 | 14 | 1 (Item 59) | 0 | 6.67% |
| **Total** | **60** | **56** | **4** | **0** | **6.67%** |

---

## 3. Rubric Usability and Boundary Analysis

### 3.1 Discriminative Margin of the $0.35\text{ m}$ Boundary
The empirical distribution of planar position errors demonstrates a wide, unambiguous gap between genuine perception noise and spatial errors:
$$\max(d_{\text{nominal}}) = 0.1483\text{ m} \ll 0.3500\text{ m} \ll 0.6012\text{ m} = \min(d_{\text{distractor}})$$
The $0.2017\text{ m}$ safety margin below the threshold prevents false rejections of valid detections caused by surface vs. geometric centroid discrepancies in depth sensors. Simultaneously, the $0.2512\text{ m}$ margin above the threshold guarantees 100% rejection of spatial distractors.

### 3.2 Scope Clarification: Reference-Point Consistency vs. Full 3D Pose
- **Position ($0.35\text{ m}$):** Evaluates planar consistency against the catalogue reference point. It does *not* assert full 3D oriented bounding box intersection-over-union (IoU) or mesh alignment.
- **Yaw ($10^{-6}\text{ rad}$):** Serves solely as a data integrity check verifying that the catalogue entry orientation was copied without numerical corruption. It does *not* evaluate independent orientation estimation from monocular or depth imagery.
- **Joint Logic:** Preserves strict conjunctive correctness: $\text{Joint} = \text{Category} \land \text{Association} \land \text{Pose}$. If any dimension fails, the observation is marked incorrect.

---

## 4. Calibration Coverage Deficit Audit

Calibration Coverage Policy v2 establishes three non-negotiable coverage floors for empirical calibration:
1. **Map/Class Representation:** $\ge 1$ accepted observation per required map and class.
2. **Outcome Stratification:** $\ge 5$ correct AND $\ge 5$ incorrect observations per class.
3. **Confidence Bin Stratification:** $\ge 5$ observations per class in each confidence bin: $[0, 0.5)$, $[0.5, 0.8)$, $[0.8, 1.0]$.

### 4.1 Stratification Analysis of Pilot Observations
| Semantic Class | $[0, 0.5)$ | $[0.5, 0.8)$ | $[0.8, 1.0]$ | Correct | Incorrect | Status under Coverage v2 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `chair` | 0 | 5 | 10 | 14 | 1 | **FAILED** (Bin 1: 0/5; Incorrect: 1/5) |
| `doorway` | 0 | 1 | 14 | 14 | 1 | **FAILED** (Bin 1: 0/5; Bin 2: 1/5; Incorrect: 1/5) |
| `laboratory_entrance` | 0 | 1 | 14 | 14 | 1 | **FAILED** (Bin 1: 0/5; Bin 2: 1/5; Incorrect: 1/5) |
| `office_entrance` | 0 | 1 | 14 | 14 | 1 | **FAILED** (Bin 1: 0/5; Bin 2: 1/5; Incorrect: 1/5) |

### 4.2 Deficit Proof and Necessity of Expansion
The pilot exhibits an acute deficit:
1. **Low Confidence Starvation:** Exactly 0 observations exist in $[0, 0.5)$ across all 4 classes. Calibrators (such as Platt scaling, isotonic regression, or temperature scaling) cannot be fitted or evaluated in the low-confidence domain without severe extrapolation risk.
2. **Intermediate Confidence Deficit:** Doorway, lab entrance, and office entrance have only 1 observation in $[0.5, 0.8)$, failing the minimum requirement of 5.
3. **Negative Outcome Scarcity:** Only 1 negative observation per class exists (the engineered distractors), failing the requirement of $\ge 5$ negatives. Fitting calibration curves on a 14:1 imbalance yields degenerate, overconfident probabilities.

**Conclusion:** The pilot dataset cannot serve as calibration fitting or validation data. Amendment R3-CA-20260911-01 is empirically justified and methodologically necessary.

---

## 5. Phase 1 Pilot Restriction Recommendation

Under Amendment R3-CA-20260911-01 Section 1:
- The 60 pilot observations must be designated as **pilot-only development assets**.
- They are formally **excluded from the final calibration fitting partition** and **excluded from the held-out validation panel**.
- This segregation prevents data snooping, ensures prospective calibration integrity, and reserves the pilot exclusively for rubric and distractor validation.

---

## 6. Review Return Package Verification

The Phase 1 review return package was generated and validated via the kit's protocol CLI:
- **Command:** `python3 review.py return --output my-review-return.zip`
- **Validation:** `python3 review.py validate-return --input my-review-return.zip` (Validation status: PASSED, Return code: 0)
- **Archive Size:** 11,970 bytes
- **SHA-256 Hash:** `24f80c5a553eb15e414ebefa363b55246eefc6a0379609265e7282f7eaec52e0`
- **Contents:**
  - `review_output/policy.json` (Approved rules)
  - `review_output/approval.json` (Researcher approval record)
  - `review_output/requirements.json` (Pre-review rubric snapshot)
  - `review_output/progress.jsonl` (Complete 60-observation per-item review records)

---

**Audit Sign-off:**  
*Emmanuel Alabi Olasubomi*  
Lead Peer Reviewer, Robotics Perception & Calibration  
Date: 2026-09-12
