# Candidate depth and instance association contract — offline only

This is an explicit implementation proposal, not a calibrated measurement model.
The new helper accepts a predicted image box, depth image, camera intrinsics and
a proper rigid optical-to-map transform. No catalogue position or expected
landmark ID can influence its point calculation.

Fixed engineering settings: central 40% of predicted box width/height; retain
finite depth strictly between 0.05 and 12 m; require at least 16 valid pixels and
50% valid support. Back-project each retained pixel, transform to map coordinates,
and take coordinate-wise medians. Report depth IQR and robust coordinate scatter
with a 0.02 m sensor-floor term. Do not divide scatter by pixel count or describe
it as calibrated pose covariance. A depth IQR above 10% of median depth explicitly
flags possible multiple surfaces. These settings are candidates, not fitted
hyperparameters or experimentally validated bounds.

The point is visible surface support inside a predicted box. It can lie on
background, be systematically displaced from a catalogue reference, or belong
to a misclassified object. No guarantee of 0.35 m accuracy follows. Insufficient
support is a retained unresolved measurement, not an incorrect human label.

Association consumes the independently estimated visual class and point only
after localization. Retain every same-class reference within the fixed 0.9 m
radius; two or more remain ambiguous, regardless of nearest distance. A unique
candidate is not verified identity. Do not fill joint confidence from geometric
distance or treat the model score as a calibrated joint probability.

These modules are tested on synthetic numerical fixtures only. They have not
been connected to ROS, the frozen provider, calibration fitting or the campaign.
Applying them to actual candidate observations requires a hash-bound source/
sensor-transform contract and complete retained measurement accounting. Runtime
admission, model validation and human correctness gates remain separate.
