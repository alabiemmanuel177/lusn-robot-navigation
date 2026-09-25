"""Describe retained development score support; never inspect validation labels."""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LABELS=ROOT/'reports/expansion_development_calibration_candidate_20260914_v1/development_labels.jsonl'


def audit():
    raw=LABELS.read_bytes()
    groups=defaultdict(list)
    bindings={}
    for line in raw.splitlines():
        row=json.loads(line)
        if row['partition']!='development' or row['panel']!='primary_expansion':
            raise ValueError('development primary evidence only')
        run=row['run_id']
        if Path(run).name!=run or not run.startswith('expansion-v1-r'):
            raise ValueError('unsafe run identity')
        folder=ROOT/'reports/physical_live_episodes'/run
        request=json.loads((folder/'request.json').read_bytes())
        if request['partition']!='development' or request['protected_test_routes_used'] is not False:
            raise ValueError('nonprotected development run required')
        path=folder/'landmark_review_tasks.jsonl'
        payload=path.read_bytes()
        matches=[json.loads(line) for line in payload.splitlines()
                 if json.loads(line).get('observation_id')==row['observation_id']]
        if len(matches)!=1:raise ValueError('unique exact observation join required')
        emission=matches[0]
        if emission['category']!=row['category'] or emission['probability']!=row['probability']:
            raise ValueError('review/provider binding differs')
        groups[row['category']].append(emission)
        bindings[str(path.relative_to(ROOT))]=hashlib.sha256(payload).hexdigest()
    summary={}
    for category,rows in sorted(groups.items()):
        pixels=[r['pixels'] for r in rows]
        summary[category]=dict(count=len(rows),probability_min=min(r['probability'] for r in rows),
            probability_max=max(r['probability'] for r in rows),pixels_min=min(pixels),pixels_max=max(pixels),
            pixel_support_at_least_72=sum(p>=72 for p in pixels),
            depth_min_m=min(r['depth_m'] for r in rows),depth_max_m=max(r['depth_m'] for r in rows))
    return dict(schema_version='research3-development-score-support-audit/v1',
        label_sha256=hashlib.sha256(raw).hexdigest(),classes=summary,provider_task_sha256=bindings,
        validation_read=False,protected_content_read=False,new_observations_generated=False,
        scope='descriptive exact-ID joins; not independent human-label verification or calibration',
        interpretation='72 pixels saturates support only with provider min_pixels=18; threshold reported explicitly, not inferred per run')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=audit()
    with args.output.open('x') as stream:json.dump(report,stream,indent=2,sort_keys=True)
    print(json.dumps(report['classes'],indent=2))
