#!/usr/bin/env python3
"""Generate Research 3-owned worlds; never overwrite existing world revisions."""
import argparse
import hashlib
import json
from pathlib import Path

from language_nav.world.physical import build_world

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--base-id')
    p.add_argument('--allow-protected', action='store_true')
    args = p.parse_args()
    benchmark = ROOT/'data/manifests/instruction_benchmark_v0.1.json'
    rows = json.loads(benchmark.read_text())['instructions']
    if args.base_id:
        rows = [r for r in rows if r['base_instruction_id'] == args.base_id]
    if not args.allow_protected:
        rows = [r for r in rows if r['partition'] != 'held_out']
    if not rows:
        raise SystemExit('no authorized instructions selected')
    args.output.mkdir(parents=True, exist_ok=False)
    manifests = [build_world(args.output/r['base_instruction_id'], r) for r in rows]
    report = {'schema_version': 'research3-physical-world-build/v1', 'worlds': len(manifests),
              'benchmark_sha256': hashlib.sha256(benchmark.read_bytes()).hexdigest(),
              'protected_geometry_included': any(m['partition']=='held_out' for m in manifests),
              'research1_geometry_modified': False,
              'world_ids': [m['map_id'] for m in manifests]}
    (args.output/'build.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
