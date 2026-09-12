# Research 3 human decisions

Packet: research3-human-actions-v1
Name: Emmanuel Alabi Olasubomi
Role: Researcher
Actual date and timezone: 2026-09-12T08:58:00+01:00 (Europe/London / BST UTC+1)

These are my own scientific decisions or requests for proposals. I am not
approving unseen assets/results, granting blanket execution or protected access,
or replacing the later observation review, calibration and final-result approvals.
Personal confirmation of the above (yes/no): yes

## D1. Primary contrast and endpoint
Answer: B6 minus B5 on independently measured ordered-instruction completion
Reason: The core research question is whether contradiction-aware belief reasoning (the B6 policy) provides an incremental navigation benefit over standard uncertainty-calibrated perception with a fixed decision threshold (B5). Contrasting B6 against uncalibrated or naive baselines (B1, B2, B4) conflates calibration benefits with contradiction-handling policy effects. Isolating B6 minus B5 focuses statistical power directly on the novel mechanism while preserving single-endpoint pre-registration rigor without multiple-testing penalties.

## D2. Secondary comparisons, weighting, pairing and missingness
Accept the D2 proposal, or specify each revision: Accept the D2 proposal in full without revision.
Reason: Treating B6 versus B1/B2/B4 and auxiliary metrics (collisions, timeouts, terminal identity, goal error, path length, inspection, abstention) as strictly descriptive and exploratory preserves the confirmatory error budget. Equal weighting across the 8 scheduled conditions and paired evaluations (by world, condition, and simulator seed) controls nuisance variance. Retaining unknown outcomes with best/worst bound sensitivity rather than complete-case deletion protects against survivor bias, and framing single-anchor instructions as underspecified attributes accurately reflects the task geometry.

## D3. Minimum scientifically meaningful absolute improvement
Percentage points (not an observed improvement): 10.0 percentage points (0.10 absolute improvement in ordered completion rate)
Scientific reason: In structured indoor robotic navigation, an absolute improvement of 10 percentage points represents a clinically and operationally meaningful threshold (reducing catastrophic navigation failures or landmark misassociations by at least 1 in 10 missions). A gain below 5 percentage points would not justify the computational overhead of maintaining contradiction belief states, whereas a 10 percentage point requirement establishes a rigorous, realistic benchmark without peeking at pilot outcomes.

## D4. Confirmatory planning targets
Alpha: 0.05 (two-sided)
Target power: 0.80 (80% power under planning assumptions)
Reason, or request for statistical advice: Standard peer-reviewed convention (two-sided alpha = 0.05, power = 0.80). I request the agent to prepare formal statistical sensitivity and power calculations using nonprotected development estimates (baseline completion rate, paired discordance, and world-level intracluster correlation) to evaluate whether the 6 reserved held-out worlds provide adequate power, or whether the study must operate under descriptive/exploratory bounds.

## D5. Inferential ambition and method
Confirmatory or descriptive/exploratory: Confirmatory, contingent on power feasibility; otherwise descriptive/exploratory.
Exact preferred method, or request an agent-authored proposal: AGENT TO PREPARE A METHOD PROPOSAL FOR MY REVIEW.
Reason and limits: Clustered permutation test or cluster-robust Generalized Estimating Equations (GEE) / paired cluster bootstrap with world as the primary independent clustering unit. Because small cluster counts (K=6 held-out worlds) violate asymptotic normality and risk Type I error distortion, the agent must present an explicit method proposal evaluating small-sample cluster corrections (e.g. Wild cluster bootstrap or exact permutation over world-level sign flips) for human review before any confirmatory freeze.

## D6. Review coordination
Primary reviewer: Emmanuel Alabi Olasubomi
Independent validation custodian available (name, or no): no
Agree that validation labels remain outside model selection: yes
Other review arrangements: Since a separate independent validation custodian is not available, the agent must implement a hash-locked, delayed-release staging workflow where validation partition observations (160 attempts) are reviewed in a separate package, and their labels are cryptographically locked and sequestered until development partition fitting (400 attempts), hyperparameter tuning, and model selection are finalized and frozen.

## D7. Calibration-method constraints
Required method/constraints, or request an exact development-only proposal: Request an exact development-only calibration method proposal for human review.
Reason: Any candidate calibration family (e.g., Platt scaling / logistic calibration, temperature scaling, or isotonic regression) must specify the exact objective function, loss formulation (cross-entropy / Brier score), optimization solver, regularization penalties, handling of nondetections (retained as non-detections, not negative labels), grouping/stratification per landmark class, and pre-specified acceptance criteria (Expected Calibration Error [ECE], Brier score improvement, Maximum Calibration Error [MCE]). No model is pre-approved without an audited development proposal.

## D8. Other required authority or constraints
Additional required reviewer/supervisor, or none: none
Deadline/resource/other constraints, or none: Serial, low-priority execution on the workstation with hardware resource guards to prevent interference with concurrent Research 1 and Research 2 pipelines. No execution on protected held-out worlds without prior staged gate clearance.

## Questions or deferred decisions
1. The 40 diagnostic sphere candidate assets are noted as built and static-checked, but the 40 occlusion assets and all rendered visual preflight evidence remain deferred until the agent delivers complete scene context for inspection per Gate 12.
2. Final confirmation of sample size, simulator seed replication list, and confirmatory vs. exploratory status is deferred until the agent delivers empirical development nuisance estimates and cluster power sensitivity calculations.
