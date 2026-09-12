# Camera freeze safety correction

The investigation skill identified a protected-data guard gap: the camera freeze
validator checked an evidence request's partition flag but not its stable map ID.
A synthetic protected-map request mislabeled development reached raw-image reads.
The regression failed before the fix. The requested map and each development
evidence map now pass stable non-protected identity checks before corresponding
freeze/profile/media reads. Both protected-read regression cases now pass.

Validation execution additionally requires engineering-camera-freeze/v2. Its
12 explicit validation views bind map, category, capture pose and five world asset
hashes. Eighteen owned source files are pinned; the direct runner and serial
executor reject mismatched view/source identity. Old v1 freeze files remain
historical readable artifacts but cannot authorize validation execution. Future
serial capture batches snapshot all owned runner-preparation source paths and
check them before every new launch, failing closed on changes.

`reports/engineering_camera_settings_v2` was created once using the same six
explicitly visually checked development runs from v1, not new human correctness
labels. Four chair-colour runs and two dev10 entrance views are reused unchanged.
No palette, tolerance or FOV change was made; fourteen profile files and twelve
bound validation commands were produced. Confidence calibration remains false.

Freeze SHA256: `be24ac5a288312534eb9928a29c7a496d72a4402987819c3974860ec2be0813c`.
Commands SHA256: `756c2633a8e2986013a556d7b64c6e8eba486c169580910e0f8703f023c377fc`.
All twelve generated commands passed the owned runner's `--prepare-only` checks;
no simulator launched for these tests. V1 and all retained images are unchanged.

Remaining scope: actual validation captures still need join/visual QA and genuine
human correctness review. This engineering settings freeze is not confidence
calibration or scientific protocol approval. Process-group descendant containment
after leader exit was separately flagged for follow-up, not claimed proven here.
