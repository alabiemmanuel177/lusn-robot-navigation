# Grounding v3 compatibility, before any inference

Use official current revision a2bb814dd30d776dcf7e30523b00659f4f141c71, obtained
from the official Hub model-info endpoint and pinned before download. This
supersedes the legacy checkpoint revision only; fixed images, prompts, score and
text thresholds in GROUNDING_CANDIDATE_PROTOCOL_20260923.md are unchanged.

Two earlier checkpoints were rejected before any frame dispatch: unsupported
historical text config, then fused attention-projection weight keys incompatible
with installed split-projection modules. Never continue with randomly initialized
missing weights. Require empty missing/unexpected/mismatched/error key lists
from `output_loading_info=True`. Keep both asset inventories and failure records.
No model bytes are manually converted or local library files modified.

After numerical audit, retain all proposals through the unchanged engineering
depth/association rules. Exact navigation phrases alone are eligible for depth;
incomplete/mixed text stays unresolved. Keep the commanded rendering-model
transform explicitly unvalidated, mixed-depth abstentions, all geometric matches
and absent matches. This is not a calibrated runtime or an identity-verdict test.

The official library issue documents this compatibility problem:
https://github.com/huggingface/transformers/issues/32353
