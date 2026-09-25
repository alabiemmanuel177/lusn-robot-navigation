"""Create-once protocol review packet. No launcher, label reader or real fitter."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = 'docs/SCORE_LEARNING_COLLECTION_PROTOCOL_20260924.md'
SOURCE = 'reports/calibration_expansion_handoff_20260912_v1/plan.json'
READINESS = 'reports/four_class_perception_readiness_20260924_v1/manifest.json'
CLASSES = ('chair', 'doorway', 'laboratory_entrance', 'office_entrance')
WAVES = (('S', 'development', 100, 10), ('C', 'development', 200, 10),
         ('V', 'validation', 300, 4))
DECISIONS = ('joint_probability_as_p2_raw_input', 'fixed_three_wave_budget',
             'class_specific_depth_features', 'duplicate_and_missingness_rules',
             'fixed_learning_solver_and_failure_policy', 'unchanged_p2_gates',
             'staged_human_review_and_validation_custody')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def make_schedule(source):
    original = source['rows']
    rows = []
    for wave, partition, seed_base, maps in WAVES:
        selected = [r for r in original if r['partition'] == partition]
        expected_maps = {f'r3geo_base_r{i:03}' for i in
                         (range(1, 11) if partition == 'development' else range(11, 15))}
        if {r['map_id'] for r in selected} != expected_maps:
            raise ValueError('exact declared map partition required')
        keys = set()
        for r in selected:
            view = int(r['view_group'].rsplit('view', 1)[1])
            seed = r['seed']
            if type(seed) is not int or seed not in (1, 2) or view not in range(5):
                raise ValueError('exact seed/view grid required')
            if r['category'] not in CLASSES:
                raise ValueError('four primary classes only')
            key = (r['map_id'], r['category'], seed, view)
            if key in keys:
                raise ValueError('duplicate source cell')
            keys.add(key)
            pose = r['capture_pose']
            if set(pose) != {'x', 'y', 'yaw'} or not all(
                    type(v) in (int, float) and math.isfinite(v) for v in pose.values()):
                raise ValueError('finite planar pose required')
            rows.append(dict(attempt_id=f'jsc-v1-{wave}-{r["map_id"]}-{r["category"]}-s{seed_base+seed}-v{view}',
                wave=wave, partition=partition, map_id=r['map_id'],
                acquisition_class=r['category'], seed=seed_base+seed, view=view,
                view_group=r['view_group'], capture_pose=deepcopy(pose),
                pose_source_attempt_id=r['candidate_id'],
                world_directory=f'data/physical_worlds_readable_v1/base-{r["map_id"].rsplit("_",1)[1]}',
                execution_manifest_sha256=None, execution_authorized=False,
                human_label=None))
        if len(keys) != maps * 4 * 2 * 5:
            raise ValueError('incomplete source grid')
    rows.sort(key=lambda r: ('SCV'.index(r['wave']), r['map_id'],
                            CLASSES.index(r['acquisition_class']), r['seed'], r['view']))
    return dict(schema_version='research3-joint-score-schedule/v1',
                protocol_id='R3-JSC-20260924-01', rows=rows,
                counts=dict(Counter(r['wave'] for r in rows)),
                execution_authorized=False, human_labels_generated=False,
                protected_worlds_included=False, scientifically_approved=False)


def validate_schedule(schedule, source):
    # Exact reconstruction catches altered poses, roles, seeds, ordering, authority
    # flags and unexpected labels, not just superficially plausible row counts.
    if schedule != make_schedule(source):
        raise ValueError('schedule differs from exact prospective construction')
    return {'valid': True, 'attempts': len(schedule['rows']),
            'counts': schedule['counts'], 'execution_armed': False}


def write(path, data):
    with path.open('x') as handle:
        json.dump(data, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')


def build(output):
    source = json.loads((ROOT / SOURCE).read_text())
    schedule = make_schedule(source)
    audit = validate_schedule(schedule, source)
    readiness = json.loads((ROOT / READINESS).read_text())
    if readiness.get('engineering_readiness_passed') is not True:
        raise ValueError('four-class engineering readiness required')
    for name, digest in readiness['input_sha256'].items():
        if sha(ROOT / name) != digest:
            raise ValueError(f'changed readiness evidence: {name}')
    inputs = [PROTOCOL, SOURCE, READINESS, 'scripts/prepare_joint_score_protocol.py',
              'tests/test_joint_score_protocol.py',
              'docs/JOINT_SCORE_METHOD_CANDIDATE_20260923.md',
              'docs/CALIBRATION_METHOD_PROPOSAL_20260912.md',
              'docs/VALIDATION_DELAYED_RELEASE.md',
              'scripts/joint_score_method_candidate.py']
    pins = {name: sha(ROOT / name) for name in inputs}
    output.mkdir(parents=True, exist_ok=False)
    write(output / 'schedule.json', schedule)
    write(output / 'schedule_audit.json', audit)
    write(output / 'review_decision_TEMPLATE.json', dict(
        schema_version='research3-joint-score-protocol-review/v1',
        protocol_id=schedule['protocol_id'], protocol_sha256=pins[PROTOCOL],
        schedule_sha256=sha(output / 'schedule.json'),
        reviewer_name=None, reviewer_role=None, reviewed_at=None,
        overall_decision='pending',
        decisions={d: dict(decision='pending', rationale=None) for d in DECISIONS},
        approves_unseen_labels_or_models=False, grants_execution_by_itself=False,
        authorizes_validation_release_or_protected_access=False))
    write(output / 'manifest.json', dict(
        schema_version='research3-joint-score-protocol-packet/v1',
        protocol_id=schedule['protocol_id'], status='final_proposal_pending_human_review',
        input_sha256=pins,
        packet_sha256={p.name: sha(p) for p in sorted(output.iterdir()) if p.is_file()},
        execution_armed=False, live_launches=0, real_model_fits=0,
        validation_labels_read=False, protected_worlds_read=False,
        limitations=['not a portable observation-review kit',
                     'execution asset/source manifest required per wave',
                     'one-frame production adapter and feature extractor require implementation',
                     'scientific approval and staged execution gates remain']))
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.output), indent=2))


if __name__ == '__main__':
    main()
