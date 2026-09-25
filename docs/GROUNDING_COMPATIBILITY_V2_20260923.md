# Grounding candidate v2: official checkpoint compatibility

The original 25b0b43 checkpoint cannot construct its historical
`grounding-dino-text-prenet` config under installed Transformers 4.57.1. It failed
before model load, journal creation or any image inference. Preserve v1 plan,
assets and startup failure; do not label this as a nondetection.

Use separate official revision e08274d3760f8fcfc53dcbb9ca3ed0a29fa9c40e, with
config-load verification before preparing the candidate. This supersedes only the
checkpoint revision in GROUNDING_CANDIDATE_PROTOCOL_20260923.md. No local model
config rewriting, random missing weights or arbitrary state-key mapping is allowed.
All other fixed panel/prompt/threshold/source protections remain unchanged.

The wrapper redirects only the output directory and asset inventory of the
unchanged R3 candidate runner. It adds its own source and this document to the
plan before create-once writing. No frozen provider/ROS code is modified. It does
not retry a captured observation; v1 never reached frame dispatch.
