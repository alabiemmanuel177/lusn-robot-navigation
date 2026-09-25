"""Account for all fixed feasibility assignments without creating human labels."""
import json
from collections import Counter
from pathlib import Path
import run_stage1_four_workers as runner
RESUMED = runner.ROOT / 'reports/stage1_four_workers_20260922_v2'
TWO_WORKERS = runner.ROOT / 'reports/stage1_two_workers_20260922_v4'
RESULT_DIRECTORIES = (runner.OUTPUT, RESUMED, TWO_WORKERS)


def summarize():
    rows = []
    classes = {}
    for target in runner.base.assignments():
        name = target['candidate_id']
        matches = [p / (name + '.result.json') for p in RESULT_DIRECTORIES
                   if (p / (name + '.result.json')).exists()]
        if len(matches)>1:raise ValueError('duplicate attempt across historical and resumed schedules')
        result = matches[0] if matches else runner.OUTPUT / (name + '.result.json')
        item = dict(candidate_id=name, category=target['category'], entity_id=target['entity_id'],
                    status='not_started', confidence=None, human_verdict=None)
        if result.exists():
            data = json.loads(result.read_bytes())
            item.update(status=data['status'], result_sha256=runner.base.sha(result))
            if data['status'] != 'infrastructure_failure':
                audit = runner.audit_capture(runner.ROOT / 'reports/physical_live_episodes' / name)
                selected = audit['selected_observation']
                if selected is not None:
                    if selected['entity_id'] != target['entity_id'] or selected['category'] != target['category']:
                        raise ValueError('assigned entity/category mismatch')
                    item['confidence'] = selected['confidence']
        elif any((p / (name + '.start.json')).exists() for p in RESULT_DIRECTORIES):
            item['status'] = 'started_without_terminal_record'
        stats = classes.setdefault(target['category'], dict(scheduled=0, raw_confidence_bins=[0,0,0], statuses={}))
        stats['scheduled'] += 1
        stats['statuses'][item['status']] = stats['statuses'].get(item['status'],0) + 1
        probability = item['confidence']
        if probability is not None:
            stats['raw_confidence_bins'][0 if probability < .5 else 1 if probability < .8 else 2] += 1
        rows.append(item)
    counts = dict(Counter(r['status'] for r in rows))
    return dict(schema_version='research3-stage1-feasibility-summary/v1', scheduled=80,
                complete=not any(r['status'] in {'not_started','started_without_terminal_record'} for r in rows),
                status_counts=counts, classes=classes, rows=rows,
                confidence_bin_intervals=['[0,0.5)','[0.5,0.8)','[0.8,1]'],
                human_labels_generated=False, calibration_eligible=False, validation_used=False,
                coverage_certified=False, note='Design-only observations; confidence coverage is not correctness or calibration certification.')


if __name__ == '__main__':
    report = summarize()
    if not report['complete']:
        print(json.dumps(dict(complete=False,status_counts=report['status_counts'])))
    else:
        destination = next(p for p in reversed(RESULT_DIRECTORIES) if p.exists()) / 'summary.json'
        runner.base.write(destination, report)
        print(json.dumps(dict(complete=True,status_counts=report['status_counts'],classes=report['classes'])))
