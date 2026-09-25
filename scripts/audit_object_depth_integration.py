"""Check retained inputs, replay depth, independently enumerate geometric matches."""
from collections import Counter
import json
import math
import numpy as np
import yaml
from candidate_depth_support import estimate
from integrate_object_depth_candidate import ROOT, SOURCE, OUTPUT, sha, write, decode_depth


def main():
    plan = json.loads((OUTPUT/'plan.json').read_bytes())
    report = json.loads((OUTPUT/'report.json').read_bytes())
    assert report['plan_sha256'] == sha(OUTPUT/'plan.json')
    assert report['results_sha256'] == sha(OUTPUT/'results.json')
    for path, expected in plan['input_sha256'].items():
        assert sha(path) == expected, path
    actual = json.loads((OUTPUT/'results.json').read_bytes())
    original = [json.loads(line) for line in (SOURCE/'results.jsonl').read_text().splitlines()]
    assert len(actual) == len(original) == len(plan['slots']) == 24
    counts = Counter()
    for slot, before, after in zip(plan['slots'], original, actual, strict=True):
        assert slot['source_index'] == before['source_index'] == after['source_index']
        assert len(before['boxes']) == len(after['boxes'])
        if slot['status'] != 'ready':
            assert after['status'] == 'retained_source_failure'
            continue
        frame = ROOT/slot['frame']
        meta = json.loads(frame.read_bytes())
        depth = decode_depth((frame.parent/meta['depth']['file']).read_bytes(), meta['depth'])
        request = json.loads((frame.parent.parent/'request.json').read_bytes())
        # Separate scalar construction of the declared (unverified) transform.
        pose = request['capture_pose']; c, s = math.cos(pose['yaw']), math.sin(pose['yaw'])
        transform = np.array([[s,0,c,pose['x']+.133*c+.094*s],
                              [-c,0,s,pose['y']+.133*s-.094*c],
                              [0,-1,0,.224],[0,0,0,1]])
        assert np.allclose(transform, after['optical_to_map_assumed'], atol=1e-12, rtol=0)
        refs = yaml.safe_load((frame.parent.parent/'runtime_scene.yaml').read_bytes())['entities']
        for old, new in zip(before['boxes'], after['boxes'], strict=True):
            assert old == new['prediction']
            assert new['human_verdict'] is None and new['entity_id'] is None
            assert new['joint_correctness_probability'] is None
            assert not new['calibration_eligible'] and not new['runtime_admitted']
            counts[new['status']] += 1
            if old['query'] in ('background', 'sign'):
                assert new['status'] == 'non_navigation_visual_hypothesis' and new['depth'] is None
                continue
            surface = estimate(depth, old['xyxy'], np.asarray(meta['camera_info']['k']).reshape(3,3), np.asarray(after['optical_to_map_assumed']))
            assert surface == new['depth']
            if surface['map_pose'] is None:
                assert new['association'] is None and new['status'] == surface['status']
            elif surface['multiple_surfaces_possible']:
                assert new['association'] is None and new['status'] == 'unresolved_multiple_surfaces'
            else:
                x,y = surface['map_pose']
                matches = sorted([dict(entity_id=r['entity_id'], reference_distance_m=math.hypot(x-r['pose']['x'],y-r['pose']['y']))
                    for r in refs if r['category']==old['query'] and math.hypot(x-r['pose']['x'],y-r['pose']['y'])<=.9], key=lambda r:r['entity_id'])
                assert matches == new['association']['candidates']
                expected = 'unassociated' if not matches else 'unique_geometric_candidate' if len(matches)==1 else 'ambiguous'
                assert new['status'] == expected
                assert not new['association']['identity_verified']
    assert dict(counts) == report['status_counts'] and sum(counts.values()) == 93
    result = dict(integrity_passed=True, input_hashes_verified=len(plan['input_sha256']),
        all_boxes_retained=True, depth_estimator_replay_passed=True,
        independent_transform_arithmetic_passed=True, independent_geometric_matches_passed=True,
        actual_transform_accuracy_established=False, human_labels_generated=False,
        report_sha256=sha(OUTPUT/'report.json'), auditor_sha256=sha(__file__))
    write(OUTPUT/'audit.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
