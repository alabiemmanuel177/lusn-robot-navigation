"""Development-only replay audit; old frames remain diagnostic, never Wave S."""
import argparse
from collections import Counter
import json
from pathlib import Path

from integrate_object_depth_candidate import ROOT, sha, checked_child, decode_depth
from joint_score_components import emissions
from joint_score_collection import write_once


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    readiness = ROOT/'reports/four_class_perception_readiness_20260924_v1/manifest.json'
    pins = json.loads(readiness.read_text())['input_sha256']
    for path, expected in pins.items():
        if sha(ROOT/path) != expected:
            raise ValueError('changed readiness source: '+path)
    sources = ['four_class_broad_integration_20260924_v3',
               'four_class_live_integration_20260924_v3', 'four_class_repeated_integration_20260924_v3']
    output_rows, counts, eligibility = [], Counter(), Counter()
    for source in sources:
        path = ROOT/'reports'/source/'results.json'
        if str(path.relative_to(ROOT)) not in pins:
            raise ValueError('replay panel not pinned by readiness')
        for row in json.loads(path.read_text())['rows']:
            report = dict(panel=source, source_index=row['source_index'], primary_eligible=False)
            if row['status'] != 'completed':
                report['status'] = 'retained_infrastructure_failure'
            else:
                frame = ROOT/row['frame']
                meta = json.loads(frame.read_text())
                depth = decode_depth(checked_child(frame.parent, meta['depth']['file']).read_bytes(), meta['depth'])
                category = row['acquisition_category']
                result = emissions(dict(frame_id=sha(frame), observed_at_ns=meta['rgb_stamp_ns'],
                                        hypotheses=row['observations']), depth=depth, acquisition_class=category)
                report.update(status='replayed', acquisition_class=category,
                              emission_count=len(result['emissions']), perception_status=result['status'],
                              proposal_status_counts=dict(Counter(r['primary_status'] for r in result['hypotheses'])))
                eligibility[category] += len(result['emissions'])
            counts[report['status']] += 1
            output_rows.append(report)
    write_once(args.output, dict(schema_version='research3-jsc-component-replay-audit/v1',
        readiness_manifest_sha256=sha(readiness), rows=output_rows, counts=dict(counts),
        diagnostic_emissions_by_class=dict(eligibility), human_labels_read=False,
        primary_eligible=False, new_model_fitted=False, validation_or_protected_read=False,
        sources={str(ROOT/'reports'/s/'results.json'): sha(ROOT/'reports'/s/'results.json') for s in sources},
        implementation_sha256={str(ROOT/'scripts'/s): sha(ROOT/'scripts'/s) for s in
                              ('joint_score_components.py', 'audit_joint_score_components.py')}))
    print(json.dumps(dict(counts=counts, diagnostic_emissions_by_class=eligibility), indent=2))


if __name__ == '__main__':
    main()
