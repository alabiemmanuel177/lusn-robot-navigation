#!/usr/bin/env python3
"""Independent fresh packet metadata audit; never creates QA or human labels."""
import argparse
from collections import Counter
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


PACK = module('capture_audit_package', 'package_physical_engineering.py')
PREP = module('capture_audit_join', 'prepare_physical_review_packet.py')
SOURCE = module('capture_audit_sources', 'prepare_current_capture_plan.py')


def read(path):
    return json.loads(Path(path).read_bytes())


def check(condition, reason):
    if not condition:
        raise ValueError(reason)


def audit(packet, plan_directory, archive, archive_sha256, *, root=ROOT):
    root = Path(root).resolve()
    packet, plan_directory, archive = [PACK.safe_path(root, path) for path in (packet, plan_directory, archive)]
    PACK.current_capture_plan_paths(root, plan_directory)
    plan = read(plan_directory/'recapture_plan.json')
    plan_ids = [row['run_id'] for row in plan['views']]
    check(len(plan_ids) == 46 and len(set(plan_ids)) == 46, 'complete unique 46-run capture plan required')
    manifest = read(packet/'packet_manifest.json')
    directories = [PACK.safe_path(root, path) for path in manifest['run_directories']]
    check(len(directories) == 46 and len(set(directories)) == 46, 'exact unique 46-run packet required')
    # Request-only nonprotected gates before any capture or provider media read.
    requests = {}
    for directory in directories:
        gate = PREP.gate_directory(directory, directory.name)
        check(gate['status'] == 'nonprotected_request_verified', 'missing or unverified nonprotected request')
        request = read(directory/'request.json')
        check(request['run_id'] not in requests, 'duplicate actual run ID')
        requests[request['run_id']] = request
    check(set(requests) == set(plan_ids), 'packet differs from exact source-bound capture cohort')
    source_report = SOURCE.audit(plan_directory, archive, archive_sha256)
    check(source_report.get('all_46_source_bound') is True, 'one or more captures lack exact archived source bindings')
    paths, packet_reference = PACK.review_packet_paths(root, packet)
    inventory, policy = read(packet/'inventory.json'), read(packet/'sampling_policy.json')
    qa = [json.loads(line) for line in (packet/'combined_visual_qa.jsonl').read_text().splitlines() if line.strip()]
    recomputed = PREP.CONSOLIDATE.consolidate(directories, qa, sampling_policy=policy)
    recomputed['qa_input_sha256'] = PACK.digest((packet/'combined_visual_qa.jsonl').read_bytes())
    check(recomputed == inventory, 'inventory differs from independently recomputed joins and QA bindings')
    check(inventory.get('status') == 'ready_for_human_review' and inventory.get('coverage_complete') is True
          and inventory.get('selected_ready_items') == 60 and inventory.get('selected_missing_items') == 0
          and len(policy['targets']) == 60, 'complete ready 60-target review required')
    check(len(inventory['coverage']) == 56, 'exact fourteen-map/four-class coverage required')
    scoped = Counter((row['run_id'], row['observation_id']) for row in inventory['items'])
    selected = Counter(row['observation_id'] for row in inventory['selected_ready'])
    check(all(count == 1 for count in scoped.values()), 'duplicate run-scoped observation identity')
    check(len(selected) == 60 and all(count == 1 for count in selected.values()), 'selected observation IDs not globally unique')
    check(all(row.get('correct') is None and row.get('human_reviewer_id', '') == '' for row in inventory['items']),
          'human labels present in supposedly unlabelled packet')
    resources, bound_runs = [], []
    for directory in directories:
        request = requests[directory.name]
        summary, guard = read(directory/'capture_summary.json'), read(directory/'resource_guard.json')
        check(request.get('capture_only') is True and summary.get('run_id') == request['run_id']
              and summary.get('complete') is True and summary.get('collision_count') == 0
              and summary.get('motion_commands_sent') is False and summary.get('navigation_episode') is False
              and summary.get('protected_test_routes_used') is False and summary.get('human_labels_generated') is False,
              'invalid stationary capture completion, motion, collision or scope claim: ' + directory.name)
        world = PACK.safe_path(root, request['world_directory'])
        for name, expected in request['asset_sha256'].items():
            path = PACK.safe_path(root, world/name)
            check(path.parent == world and PACK.digest(path.read_bytes()) == expected, 'changed or unsafe world asset')
        if request.get('runtime_scene_sha256') is not None:
            check(PACK.digest(PACK.safe_path(root, request['runtime_scene']).read_bytes()) == request['runtime_scene_sha256'],
                  'runtime scene bytes differ from capture request')
        samples = guard.get('samples', [])
        check(bool(samples), 'missing recorded resource samples')
        for sample in samples:
            check(all(type(sample.get(k)) in (float, int) and math.isfinite(sample[k]) for k in
                      ('available_memory_kib', 'cpu_pressure_avg10', 'load1')), 'unknown or invalid recorded resource metrics')
        resources.extend(samples)
        bound_runs.append({'run_id': directory.name,
            'request_sha256': PACK.digest((directory/'request.json').read_bytes()),
            'capture_summary_sha256': PACK.digest((directory/'capture_summary.json').read_bytes()),
            'resource_guard_sha256': PACK.digest((directory/'resource_guard.json').read_bytes())})
    return {'schema_version': 'research3-review-packet-provenance-audit/v1',
        'status': 'passed_with_explicit_provenance_limits', 'packet': str(packet.relative_to(root)),
        'packet_manifest_sha256': packet_reference['packet_manifest_sha256'],
        'source_archive_sha256': archive_sha256, 'source_plan_sha256': PACK.digest((plan_directory/'recapture_plan.json').read_bytes()),
        'runs': 46, 'targets': 60, 'selected_ready': 60, 'selected_missing': 0,
        'coverage_cells': 56, 'coverage_complete': True, 'all_46_source_bound': True,
        'packet_and_original_qa_files_verified': len(paths), 'qa_rows': len(qa),
        'inventory_recomputed_exactly': True, 'all_source_items_retained': len(inventory['items']),
        'selected_global_observation_id_duplicate_groups': 0, 'run_scoped_observation_id_duplicate_groups': 0,
        'stationary_capture_summaries_complete': 46, 'recorded_collision_count': 0,
        'motion_commands_sent': False, 'resource_samples': len(resources),
        'minimum_available_memory_kib': min(row['available_memory_kib'] for row in resources),
        'maximum_cpu_pressure_avg10': max(row['cpu_pressure_avg10'] for row in resources),
        'maximum_load1': max(row['load1'] for row in resources), 'run_bindings': bound_runs,
        'research2_performance_unchanged_proven': False, 'human_labels_present': 0,
        'human_labels_generated': False, 'independent_visual_inspection_performed': False,
        'protected_data_used': False, 'calibration_frozen': False, 'study_complete': False,
        'limits': ['Metadata and exact byte bindings are not an independent visual review or human correctness labels.',
                   'Four explicitly selected engineered stress views do not estimate natural error prevalence.',
                   'Stationary zero-collision records do not validate navigation collision safety.',
                   'Recorded CPU/memory samples do not prove unchanged Research 2 performance or GPU headroom.',
                   'Source checkpoints and retained named bytes are not continuous attestation or complete external model/binary/environment closure.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', type=Path, required=True)
    parser.add_argument('--plan-directory', type=Path, required=True)
    parser.add_argument('--source-archive', type=Path, required=True)
    parser.add_argument('--source-archive-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('audit report is create-once')
    result = audit(args.packet, args.plan_directory, args.source_archive, args.source_archive_sha256)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'status': result['status'], 'runs': result['runs'], 'targets': result['targets']}))


if __name__ == '__main__':
    main()
