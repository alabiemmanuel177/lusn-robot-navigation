#!/usr/bin/env python3
"""Independently inspect SDF collision geometry and footprint-feasible grid routes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np

sys.path.insert(0, '/home/eao/risk-calibrated-nav')
from rcn.shortest_path import load_map, inflate, dijkstra_field, world_to_cell, cell_to_world, NEIGHBOURS
from language_nav.evaluation.ordered import score_ordered_instruction


def verify(folder):
    manifest = json.loads((folder/'manifest.json').read_text())
    annotation = json.loads((folder/'ordered_geometry.json').read_text())
    assert hashlib.sha256((folder/'map.pgm').read_bytes()).hexdigest() == manifest['map_sha256']
    assert hashlib.sha256((folder/'world.sdf').read_bytes()).hexdigest() == manifest['world_sha256']
    if 'map_metadata_sha256' in manifest:
        assert hashlib.sha256((folder/'map.yaml').read_bytes()).hexdigest() == manifest['map_metadata_sha256']
    blocked, meta = load_map(folder/'map.yaml')
    h = blocked.shape[0]
    grid = inflate(blocked, 6)  # Conservative 0.30m robot footprint radius.
    start = world_to_cell(manifest['start']['x'], manifest['start']['y'], meta, h)
    field = dijkstra_field(grid, start, meta['resolution'])
    collisions = []
    for model in ET.parse(folder/'world.sdf').findall('.//world/model'):
        if model.attrib['name'] == 'ground_plane':
            continue
        pose = [float(v) for v in model.findtext('pose').split()]
        for collision in model.findall('./link/collision'):
            size = [float(v) for v in collision.findtext('./geometry/box/size').split()]
            if pose[2]-size[2]/2 < .9:
                collisions.append((pose[0], pose[1], size[0], size[1]))
    # Gate centre lies in an actual SDF aperture, bounded by collision-wall jambs.
    gate = next(g for g in annotation['gates'] if g['gate_id']=='second_doorway')
    cx, cy = [(a+b)/2 for a,b in zip(gate['a'], gate['b'])]
    def collision_at(x,y):
        return any(abs(x-bx) <= sx/2+1e-8 and abs(y-by) <= sy/2+1e-8 for bx,by,sx,sy in collisions)
    assert not collision_at(cx,cy), 'doorway aperture is physically blocked'
    assert collision_at(cx-.82,cy) and collision_at(cx+.82,cy), 'doorway lacks physical jambs'
    annotation['geometry_verified'] = True
    annotation['geometry_evidence'] = 'geometry_audit.json: SDF aperture/jamb and footprint connectivity verification'
    paths = []
    for candidate in manifest['candidates']:
        goal = world_to_cell(candidate['goal']['x'], candidate['goal']['y'], meta, h)
        assert np.isfinite(field[goal]), f"unreachable candidate {candidate['route_id']}"
        cell, cells = goal, [goal]
        while cell != start:
            neighbors = [(cell[0]+dr,cell[1]+dc) for dr,dc,_ in NEIGHBOURS]
            neighbors = [q for q in neighbors if 0<=q[0]<h and 0<=q[1]<grid.shape[1]
                         and not grid[q] and field[q]<field[cell]-1e-9
                         and not (grid[cell[0],q[1]] or grid[q[0],cell[1]])]
            assert neighbors, 'grid reconstruction failed'
            cell = min(neighbors, key=lambda q:(field[q],q))
            cells.append(cell)
        positions = [cell_to_world(*q,meta,h) for q in reversed(cells)]
        # Sample each segment against SDF collision boxes, independently of raster generation.
        assert not any(collision_at(x,y) for x,y in positions), 'grid path intersects physical wall'
        expected = candidate['route_id']==manifest['expected_route_id']
        score = score_ordered_instruction(positions,annotation,terminal_identity_correct=expected)
        assert score['instruction_completion'] is expected, 'ordered gate semantics mismatch'
        paths.append({'route_id': candidate['route_id'], 'expected': expected,
                      'positions': positions, 'ordered_score': score})
    report = {'schema_version': 'research3-physical-geometry-audit/v1',
              'passed': True, 'candidate_count': len(paths), 'footprint_radius_m': .30,
              'world_sha256': manifest['world_sha256'], 'map_sha256': manifest['map_sha256'],
              'paths': paths, 'live_validation_completed': False}
    for name, data in [('geometry_audit.json',report), ('verified_ordered_geometry.json',annotation)]:
        with (folder/name).open('x') as stream:
            json.dump(data,stream,indent=2,sort_keys=True)
            stream.write('\n')
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--world',type=Path,required=True)
    args=parser.parse_args()
    report=verify(args.world)
    print(json.dumps({k:v for k,v in report.items() if k!='paths'}))


if __name__=='__main__':
    main()
