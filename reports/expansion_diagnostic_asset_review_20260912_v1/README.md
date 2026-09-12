# Diagnostic asset review packet

Rendered candidates: 78 of 80. Agent preflight passed:
78 (38 occluders, 40 spheres).

Open `index.html` and inspect every card. Each shows the control render of the unmodified
world, the candidate render with overlays, and the changed-pixel map at the identical camera
pose used by the bound pilot view. `rendered_audit.json` holds the pixel measurements.

The occluder definition is 20% of the projected convex silhouette of the provider marker
box, not 20% of the whole semantic object. Accepting the definition is a separate field.

To decide: copy `DECISIONS.template.json` to `DECISIONS.json`, set every `decision` to
`accept`, `revise` or `reject`, set `occluder_definition_accepted`, fill your name, role and
an ISO-8601 `reviewed_at`, and set `packet_sha256` to the value in `manifest.json.sha256`.
Return `DECISIONS.json`. This decision authorizes diagnostic collection of accepted
candidates only; it generates no labels and grants no primary or protected execution.
