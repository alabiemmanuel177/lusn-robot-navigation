"""Audit the complete fresh class-aware design panel; never assign human labels."""
from collections import Counter
import json
import math
import numpy as np
from PIL import Image
from analyze_feasibility_score_support import analyze, PROVIDER
from class_aware_acquisition_pilot import ROOT, OUTPUT, rows, check_pins, bound_engine
from distance_lighting_pilot import SNAPSHOT, CLASSES
from expansion_rendered_checks import decode_frame
from resume_stage1_two_workers import audit_capture
from run_stage1_feasibility import sha, write


def require(value, message):
    if not value:
        raise ValueError(message)


def check_request(request, row):
    require(request['run_id'] == row['candidate_id'], 'run identity')
    require(request['partition'] == 'development' and not request['protected_test_routes_used'], 'scope')
    require(request['capture_only'] is True and request['capture_frame_budget'] == 1, 'stationary frame')
    require(request['simulation_seed'] == 17 and request['camera_horizontal_fov'] == 2., 'seed/camera')
    require(request['capture_pose'] == row['capture_pose'], 'assigned pose')
    require(request['capture_target_entity_id'] == row['entity_id'], 'target identity')
    require(request['capture_target_categories'] == [row['category']], 'class identity')
    require(request['calibration_sha256'] is None, 'no calibration')
    require(request['camera_profile_sha256'] == sha(ROOT / row['camera_profile']), 'profile')
    require(request['expansion_instrumentation_sha256'] == sha(SNAPSHOT), 'snapshot')
    require(request['source_sha256'] == json.loads(SNAPSHOT.read_bytes())['source_sha256'], 'core source')
    provenance = request['distance_lighting_pilot']
    require(provenance['plan_sha256'] == sha(OUTPUT / 'plan.json'), 'new plan binding')
    require(provenance['source_binding_sha256'] == sha(OUTPUT / 'source_binding.json'), 'new source binding')
    require(provenance['world_sha256'] == sha(ROOT / row['derivative_world_path']), 'lighting hash')
    require('world_path:=' + str(ROOT / row['derivative_world_path']) in request['simulation_launch_argv'], 'world argument')


def main():
    schedule = rows()
    with bound_engine() as engine:
        summary = engine.summarize()
    require(summary['completed'] == 96, 'fixed schedule incomplete')
    output = OUTPUT / 'final'
    output.mkdir(exist_ok=False)
    previews = output / 'previews'
    previews.mkdir()
    evidence, scores = [], []
    bins = {c: [0, 0, 0] for c in CLASSES}
    counts = {c: Counter() for c in CLASSES}
    for row in schedule:
        name = row['candidate_id']
        folder = ROOT / 'reports/physical_live_episodes' / name
        result_path = OUTPUT / (name + '.result.json')
        result = json.loads(result_path.read_bytes())
        require(result['run_id'] == name, 'result identity')
        counts[row['category']][result['status']] += 1
        request = json.loads((folder / 'request.json').read_bytes())
        check_request(request, row)
        record = dict(candidate_id=name, category=row['category'], status=result['status'], human_verdict=None,
                      lighting_scale=row['lighting_scale'], acquisition_family=row['acquisition_family'],
                      distance_fraction=row.get('distance_fraction'), source_view_index=row.get('source_view_index'),
                      result_sha256=sha(result_path), request_sha256=sha(folder / 'request.json'))
        if result['status'] != 'infrastructure_failure':
            capture = audit_capture(folder)
            require(capture['status'] == result['status'] and capture['selected_observation'] == result['selected_observation'], 'capture evidence')
            frame = folder / 'perception_capture/frame-000.json'
            rgb, _ = decode_frame(frame)
            image_path = previews / (name + '.png')
            Image.fromarray(rgb).save(image_path)
            with Image.open(image_path) as image:
                require(np.array_equal(np.asarray(image), rgb), 'lossless full frame')
            record.update(frame_sha256=sha(frame), preview=str(image_path.relative_to(ROOT)), preview_sha256=sha(image_path),
                          full_frame=True, cropped=False, overlays_added=False)
            obs = capture['selected_observation']
            if obs:
                require(obs['entity_id'] == row['entity_id'] and obs['category'] == row['category'], 'exact selection')
                p = obs['confidence']
                require(math.isfinite(p) and 0 <= p <= 1, 'finite raw probability')
                bins[row['category']][0 if p < .5 else 1 if p < .8 else 2] += 1
                score = analyze(dict(run_id=name, partition='development', panel='design_feasibility', category=row['category'],
                                     observation_id=obs['observation_id'], probability=p))
                require(score['score_reconstruction_matches'], 'score reproduction')
                scores.append(score)
                record.update(confidence=p, metric_reference_error_m=score['association_error_m'],
                              metric_threshold_exceeded=score['association_error_m'] > .35,
                              metric_diagnostic_is_not_joint_human_verdict=True)
        evidence.append(record)
    check_pins()
    require(bins == summary['raw_confidence_bins'], 'independent count reproduction')
    passed = all(n >= 2 for b in bins.values() for n in b)
    report = dict(schema_version='research3-class-aware-pilot-audit/v1', integrity_passed=True,
                  plan_sha256=sha(OUTPUT / 'plan.json'), scheduled=96, status_counts=summary['status_counts'],
                  class_status_counts=counts, raw_confidence_bins=bins, automatic_feasibility_passed=passed,
                  previews=sum('preview' in r for r in evidence), score_reconstructions=len(scores),
                  all_emitted_scores_reproduced=True, human_labels_generated=False, calibration_eligible=False,
                  primary_collection_authorized=False, validation_or_protected_data_read=False,
                  next_gate='genuine_pilot_joint_review' if passed else 'design_decision_not_calibration_review', rows=evidence)
    write(output / 'audit.json', report)
    write(output / 'score_reconstruction.json', dict(rows=scores, provider_core_sha256=sha(PROVIDER / 'research3_landmark_bridge/core.py'),
                                                   human_labels_generated=False, calibration_eligible=False))
    print(json.dumps({k: v for k, v in report.items() if k != 'rows'}))


if __name__ == '__main__':
    main()
