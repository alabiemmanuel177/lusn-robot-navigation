#!/usr/bin/env python3
"""Create authorized held-out visual catalogues using frozen benchmark identities."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
R1 = Path('/home/eao/risk-calibrated-nav')
sys.path.insert(0, str(R1))
sys.path.insert(0, str(ROOT / 'src'))
from language_nav.benchmark.semantic_catalog import load_semantic_route_catalog
from rcn.landmark_bridge import load_landmark_scene, validate_scene_against_repository


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--allow-protected', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.allow_protected:
        raise SystemExit('explicit protected opt-in required')
    if args.output.exists():
        raise SystemExit('refusing to overwrite held-out catalogues')
    benchmark = ROOT / 'data/manifests/instruction_benchmark_v0.1.json'
    rows = [r for r in json.loads(benchmark.read_text())['instructions'] if r['partition'] == 'held_out']
    if len(rows) != 6:
        raise ValueError('expected six frozen held-out benchmark instructions')
    args.output.mkdir(parents=True)
    plan = {'schema_version': 'landmark-bridge-route-plan/v1', 'protected_test_routes_used': True,
            'benchmark_sha256': hashlib.sha256(benchmark.read_bytes()).hexdigest(),
            'prior_protected_graph_access': True, 'routes': []}
    for row in rows:
        plan['routes'].append({
            **{key: row[key] for key in ('base_instruction_id', 'platform_route_id', 'map_id',
               'partition', 'anchor_entity_id', 'terminal_category', 'terminal_region_id')},
            'chair_color': row['anchor_attributes']['color'], 'side': row['topology_side'],
            'partition': 'test',
        })
    plan_path = args.output / 'route_plan.yaml'
    with plan_path.open('x') as stream:
        yaml.safe_dump(plan, stream, sort_keys=False)
    builder_path = R1 / 'scripts/build_research3_landmark_catalogs.py'
    spec = importlib.util.spec_from_file_location('provider_builder', builder_path)
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    made = builder.build(R1, plan_path, args.output / 'scenes', args.output / 'semantic_routes',
                         allow_protected=True)
    counts = []
    for path in made:
        if path.parent.name == 'scenes':
            scene = load_landmark_scene(path, allow_protected=True)
            assert not validate_scene_against_repository(scene, R1, allow_protected=True)
            try:
                load_landmark_scene(path)
            except PermissionError:
                pass
            else:
                raise AssertionError('protected scene accepted without opt-in')
            counts.append(len(scene.entities))
        else:
            load_semantic_route_catalog(path, R1, allow_protected=True)
    report = {'schema_version': 'research3-heldout-catalogue-audit/v1', 'protected_test_routes_used': True,
              'prior_protected_graph_access': True, 'scene_catalogues': len(counts),
              'semantic_route_catalogues': len(counts), 'routes': len(rows), 'entities': sum(counts),
              'map_geometry_modified': False, 'runtime_capture_completed': False,
              'claim_limit': 'Visual landmark catalogues; physical doorway topology is not certified.',
              'provider_builder_sha256': hashlib.sha256(builder_path.read_bytes()).hexdigest(),
              'files': {str(p.relative_to(args.output)): hashlib.sha256(p.read_bytes()).hexdigest() for p in made}}
    with (args.output / 'audit.json').open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'files'}, sort_keys=True))


if __name__ == '__main__':
    main()
