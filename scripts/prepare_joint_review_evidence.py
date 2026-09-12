#!/usr/bin/env python3
"""Create reference evidence, never labels or a pose-acceptance policy."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import yaml


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def object_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def build(inventory_path):
    inventory_path = Path(inventory_path)
    inventory = json.loads(inventory_path.read_text())
    if inventory.get('protected_data_used') is not False:
        raise ValueError('nonprotected inventory required')
    runs = {row['run_id']: Path(row['directory']) for row in inventory['runs'] if row.get('run_id')}
    provenance = {row['run_id']: row for row in inventory['runs'] if row.get('run_id')}
    result = []
    for item in inventory['items']:
        if item['status'] != 'ready_for_human_review':
            continue
        row = {key: item[key] for key in ('run_id', 'observation_id', 'frame_sha256', 'task_sha256')}
        row['gaps'] = []
        try:
            run = runs[item['run_id']]
            request = json.loads((run / 'request.json').read_text())
            match = re.fullmatch(r'r3geo_base_r(00[1-9]|01[0-4])', request.get('map_id', ''))
            if not match or request.get('protected_test_routes_used') is not False:
                raise ValueError('protected or unidentified run')
            expected = 'development' if int(match[1]) <= 10 else 'validation'
            if request.get('partition') != expected:
                raise ValueError('partition mismatch')
            pinned = provenance[item['run_id']]
            if (digest(run / 'request.json') != pinned.get('request_sha256')
                    or digest(run / 'request.json') != item.get('request_sha256')):
                raise ValueError('request differs from immutable inventory binding')
            scene_path = run / 'runtime_scene.yaml'
            if digest(scene_path) != request['runtime_scene_sha256'] or digest(scene_path) != pinned.get('runtime_scene_sha256'):
                raise ValueError('runtime scene checksum mismatch')
            scene = yaml.safe_load(scene_path.read_text())
            if scene['map_id'] != request['map_id'] or scene['partition'] != expected:
                raise ValueError('scene identity mismatch')
            media = run / 'perception_capture'
            if digest(media / 'summary.json') != pinned.get('capture_summary_sha256'):
                raise ValueError('capture summary differs from inventory binding')
            summary = json.loads((media / 'summary.json').read_text())
            tasks_path = run / 'landmark_review_tasks.jsonl'
            if digest(tasks_path) != pinned.get('provider_tasks_sha256') or digest(tasks_path) != item.get('provider_tasks_sha256'):
                raise ValueError('provider task log differs from inventory binding')
            tasks = [json.loads(line) for line in tasks_path.read_text().splitlines() if line.strip()]
            selected_tasks = [task for task in tasks if task['observation_id'] == item['observation_id']]
            if len(selected_tasks) != 1:
                raise ValueError('selected provider task missing or ambiguous')
            task = selected_tasks[0]
            task_hash = hashlib.sha256(json.dumps(task, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
            if task_hash != item['task_sha256']:
                raise ValueError('selected task differs from inventory binding')
            index_path = media / 'observation_index.json'
            if summary['observation_index']['file'] != index_path.name or digest(index_path) != summary['observation_index']['sha256']:
                raise ValueError('observation index checksum mismatch')
            index = json.loads(index_path.read_text())
            candidates = [obs for frame in index['frames'] if frame['frame_sha256'] == item['frame_sha256']
                          for obs in frame['observations'] if obs['observation_id'] == item['observation_id']]
            if len(candidates) != 1:
                raise ValueError('exact observation missing or ambiguous')
            observation = candidates[0]
            if any(observation[k] != task[k] for k in ('category', 'entity_id', 'region_id', 'observed_at_ns', 'source')):
                raise ValueError('observation differs from original provider task')
            if any(observation[k] != item[k] for k in ('category', 'entity_id')):
                raise ValueError('observation differs from inventory claim')
            if observation['frame_id'] != 'map' or not all(math.isfinite(observation[k]) for k in ('x', 'y', 'yaw')):
                raise ValueError('map-frame finite pose required')
            refs = [{k: ent.get(k) for k in ('entity_id', 'region_id', 'category', 'pose')}
                    for ent in scene['entities']]
            selected = [ent for ent in refs if ent['entity_id'] == observation['entity_id']]
            if len(selected) != 1:
                raise ValueError('reference entity missing or ambiguous')
            row.update(observation={k: observation[k] for k in ('entity_id', 'region_id', 'category', 'x', 'y', 'yaw', 'covariance', 'frame_id')},
                       references=refs, selected_reference=selected[0], capture_pose=request['capture_pose'],
                       request_sha256=digest(run / 'request.json'), runtime_scene_sha256=digest(scene_path),
                       capture_summary_sha256=digest(media / 'summary.json'), provider_tasks_sha256=digest(tasks_path),
                       observation_index_sha256=digest(index_path),
                       yaw_provenance='catalogue supplied; not independently estimated',
                       reference_scope='nonprotected catalogue coordinates; reference only, not human correctness')
        except (ValueError, KeyError, OSError, TypeError) as exc:
            row['gaps'].append(str(exc))
        row['evidence_complete'] = not row['gaps']
        result.append(row)
    return {'schema_version': 'research3-joint-review-evidence/v1',
            'inventory_sha256': digest(inventory_path), 'protected_data_used': False,
            'human_labels_generated': False, 'items': result}


def validate_policy(policy):
    """Structural validation is not authentication of the named approver."""
    if policy.get('schema_version') != 'research3-joint-review-policy/v1':
        raise ValueError('joint review policy schema required')
    required = ('category_rule', 'entity_association_rule', 'pose_rule', 'yaw_rule')
    try:
        timestamp = datetime.fromisoformat(policy.get('approved_at', ''))
        dated = timestamp.tzinfo is not None and timestamp <= datetime.now(timezone.utc)
    except (ValueError, TypeError):
        dated = False
    approver = policy.get('approved_by', '')
    genuine_name = isinstance(approver, str) and not re.search(r'\b(bot|agent|synthetic|test|automated|assistant|codex)\b', approver, re.I)
    approved = (dated and genuine_name and policy.get('reviewer_type') == 'human'
                and policy.get('status') == 'approved' and policy.get('protected_data_used') is False
                and isinstance(policy.get('approved_by'), str) and bool(policy['approved_by'].strip())
                and all(isinstance(policy.get(k), str) and bool(policy[k].strip()) for k in required))
    return approved


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = build(args.inventory)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
