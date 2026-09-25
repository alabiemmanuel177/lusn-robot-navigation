# Grounding DINO checkpoint compatibility investigation

Status: DONE for checkpoint loading; no detector/scientific admission follows.

Symptom: legacy pinned checkpoint failed before image dispatch under Transformers
4.57.1. A second old checkpoint constructed its config but had missing/unexpected
attention weights. Neither failure is a perceptual nondetection.

Root cause: 25b0b43 declares unsupported `grounding-dino-text-prenet`; e08274d has
legacy fused `in_proj_weight/in_proj_bias` keys where this runtime expects split
attention projections. Merely suppressing load warnings would permit partially
randomly initialized inference and invalid research results.

Fix: resolve official current revision through Hub model-info, then pin
a2bb814dd30d776dcf7e30523b00659f4f141c71. Safe weights only, no remote code or manual
config/weight conversion. Require empty missing/unexpected/mismatched/error lists
before preparing any inference schedule. Preserve all old asset inventories and
`reports/grounding_legacy_startups_20260923.json`.

Evidence: `reports/grounding_model_load_preflight_20260923_v3.json` reports complete
load. Fresh local reproduction confirms old AutoConfig rejects and new config
loads a BERT text component. Candidate inference proceeds in a separate v3 folder.
Relevant sources: `scripts/run_grounding_candidate_v3.py` and official issue
https://github.com/huggingface/transformers/issues/32353.

The investigation skill caused strict loading verification before inference,
preventing a compatibility failure from being mislabeled as a detector failure.
