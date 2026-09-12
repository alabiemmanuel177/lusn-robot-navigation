# Diagnostic sphere candidates (v2)

Rebuild the 80 diagnostic candidates with the verified rendering camera model.

Revision reason: the v1 occluders were placed with the localization transform of
`camera_depth_frame`, which sits about 0.06 m behind, 0.05 m left of and 0.11 m
below the Gazebo sensor that renders pixels; rendered v1 screens therefore miss
the projected marker-box strip. The v1 spheres could also intrude into the
target silhouette from the bound viewpoint. This builder keeps every v1 rule
(marker box, 20% of the projected convex silhouette, neutral visual-only screen,
same-colour visual-only sphere, unchanged source subtree and non-world assets)
and changes only the camera model and the sphere placement search. Rendered
verification and human acceptance remain required; no label is produced.

Not an observation review kit. Rendered preflight and human acceptance pending.
