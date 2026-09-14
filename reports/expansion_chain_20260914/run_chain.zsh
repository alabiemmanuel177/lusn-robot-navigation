#!/usr/bin/env zsh
# Serial expansion pipeline. Every stage is create-once/resumable; failures stop the chain.
set -e
cd /home/eao/lusn-robot-navigation
source scripts/ros_env.zsh
log() { print -- "[$(date -u +%FT%TZ)] $*" }
SNAP=reports/expansion_instrumentation_snapshot_20260914_v7/snapshot.json
log "chain: STAGE development collection (resume under v7)"
python3 scripts/run_expansion_collection.py --snapshot $SNAP --partition development --lifecycle-directory reports/expansion_collection_development_20260912_v1 --execute --resume --accept-snapshot-change "v7: provider transform-readiness file gates arming; provider-failed frames are retryable; after v4/v6 transform races"
log "chain: STAGE development review kit"
[ -f reports/expansion_review_development_20260914_v1/research3_expansion_development_review_kit.zip ] || python3 scripts/build_expansion_review_kit.py --report reports/expansion_collection_development_20260912_v1/report.json --partition development --output reports/expansion_review_development_20260914_v1
log "chain: STAGE validation collection"
python3 scripts/run_expansion_collection.py --snapshot $SNAP --partition validation --lifecycle-directory reports/expansion_collection_validation_20260914_v1 --development-complete-report reports/expansion_collection_development_20260912_v1/report.json --execute --resume
log "chain: STAGE validation review kit"
[ -f reports/expansion_review_validation_20260914_v1/research3_expansion_validation_review_kit.zip ] || python3 scripts/build_expansion_review_kit.py --report reports/expansion_collection_validation_20260914_v1/report.json --partition validation --output reports/expansion_review_validation_20260914_v1
log "chain: STAGE feasibility navigation"
python3 scripts/run_feasibility_navigation.py --lifecycle-directory reports/feasibility_navigation_20260912_v1 --execute --resume
log "chain: STAGE re-render two failed occluder candidates"
python3 scripts/render_expansion_diagnostics.py run --output reports/expansion_diagnostic_render_batch2b_20260914_v1 --run-prefix expansion-diag-render-v1b --occluder-assets reports/calibration_expansion_occluder_assets_20260912_v2 --sphere-assets reports/calibration_expansion_distractor_assets_20260912_v2 --only expansion-diag-render-v1b-occluder-v2-r002-laboratory_entrance --only expansion-diag-render-v1b-occluder-v2-r009-chair
log "chain: COMPLETE"
