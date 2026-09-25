# Fixed offline object/depth integration candidate

This is engineering replay, not a primary calibration sample or runtime deployment.
Use the completed OWLv2 panel unchanged: 24 source slots, 23 intact development
frames, all 93 display boxes, including duplicates and out-of-image coordinates.
Do not change prompts, threshold, detector weights, or original evidence.

Before replay, hash-bind source results, frame metadata, RGB/depth bytes, requests,
catalogues, this protocol and integration dependencies. Decode float32 depth with
declared endianness and row stride; require matching image dimensions, exact RGB-D
synchronization, and undistorted full-image intrinsics.

The transform is explicitly an engineering assumption: commanded stationary robot
pose plus the existing rendering-camera model. It is NOT measured robot pose or
the recorded nominal camera TF. Its accuracy is not established by this replay.
No catalogue landmark coordinate is used to construct the transform or surface.

Keep the existing central-40%-box depth estimator unchanged. Missing or insufficient
support remains unresolved, not a negative label. If its multiple-surface flag is
set, retain the surface diagnostics but abstain from instance association. Other
valid navigation-class surface estimates are compared against every same-class
reference within 0.9 m; preserve all alternatives, never select a nearest winner.
Background and sign queries remain non-navigation hypotheses. No expected target
ID, colour, or claimed category filters predictions. A unique geometric candidate
is neither verified identity nor reference-point accuracy. Surface spread is not
calibrated covariance. Scores remain raw matching scores, not joint probabilities.

All outputs are excluded from calibration and live runtime. This replay cannot
resolve the previously observed absence of doorway proposals, human outcome
coverage, or calibration-method suitability. Validation labels remain sealed.
