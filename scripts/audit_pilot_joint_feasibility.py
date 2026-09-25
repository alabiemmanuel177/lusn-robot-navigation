"""Necessary reference-pose gate, independent of human semantic verdicts."""
import json
import math
import yaml
from class_aware_acquisition_pilot import ROOT, OUTPUT, rows, check_pins
from run_stage1_feasibility import sha, write
from resume_stage1_two_workers import audit_capture


def consistent(observation, reference):
    distance = math.hypot(observation['x'] - reference['pose']['x'], observation['y'] - reference['pose']['y'])
    # Same explicit default as the unchanged provider's catalogue loader.
    angle = abs(math.remainder(observation['yaw'] - reference['pose'].get('yaw', 0.), 2 * math.pi))
    if not math.isfinite(distance) or not math.isfinite(angle):
        raise ValueError('finite coordinates required')
    return dict(planar_error_m=distance, yaw_copy_error_rad=angle,
                necessary_pose_rule_passed=distance <= .35 and angle <= 1e-6)


def main():
    check_pins()
    audit = json.loads((OUTPUT / 'final/audit.json').read_bytes())
    if not audit['integrity_passed'] or audit['scheduled'] != 96:
        raise ValueError('complete audited panel required')
    records = []
    for row in rows():
        run = ROOT / 'reports/physical_live_episodes' / row['candidate_id']
        result = json.loads((OUTPUT / (row['candidate_id'] + '.result.json')).read_bytes())
        if result['status'] != 'emitted':
            continue
        capture = audit_capture(run)
        obs = capture['selected_observation']
        request = json.loads((run / 'request.json').read_bytes())
        if sha(run / 'runtime_scene.yaml') != request['runtime_scene_sha256']:
            raise ValueError('reference bytes changed')
        scene = yaml.safe_load((run / 'runtime_scene.yaml').read_bytes())
        references = [r for r in scene['entities'] if r['entity_id'] == obs['entity_id']]
        if len(references) != 1 or obs['entity_id'] != row['entity_id']:
            raise ValueError('unique assigned catalogue reference required')
        records.append(dict(candidate_id=row['candidate_id'], category=row['category'],
            **consistent(obs, references[0]), observation_index_sha256=sha(run / 'perception_capture/observation_index.json'),
            runtime_scene_sha256=sha(run / 'runtime_scene.yaml'), human_verdict=None))
    counts = {}
    for category in sorted({r['category'] for r in records}):
        group = [r for r in records if r['category'] == category]
        counts[category] = dict(emissions=len(group),
            maximum_possible_joint_correct_under_accepted_pose_rule=sum(r['necessary_pose_rule_passed'] for r in group),
            pose_inconsistent=sum(not r['necessary_pose_rule_passed'] for r in group),
            minimum_error_m=min(r['planar_error_m'] for r in group), maximum_error_m=max(r['planar_error_m'] for r in group))
    blockers = [c for c, v in counts.items() if v['maximum_possible_joint_correct_under_accepted_pose_rule'] < 2]
    report = dict(schema_version='research3-pilot-necessary-joint-feasibility/v1',
        audit_sha256=sha(OUTPUT / 'final/audit.json'), checked_emissions=len(records), class_diagnostics=counts,
        classes_unable_to_meet_pilot_correct_floor=blockers,
        bulk_human_label_request_admitted=not blockers,
        human_labels_generated=False, calibration_eligible=False,
        interpretation='Necessary-condition bound from verified coordinates, not generated category/association/joint human labels. No automatic negative quotas.',
        rows=records)
    write(OUTPUT / 'necessary_joint_feasibility.json', report)
    print(json.dumps({k:v for k,v in report.items() if k != 'rows'}))


if __name__ == '__main__':
    main()
