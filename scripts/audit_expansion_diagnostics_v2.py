#!/usr/bin/env python3
"""Independent static check of v2 diagnostic candidates: bytes, geometry, camera model.

No rendering, execution, approval or labels. Mirrors the v1 audit and adds the
rendering-camera consistency check that v1 lacked.
"""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from expansion_camera_model import rendering_camera, rotation_from_rpy  # noqa: E402

AUDIT = 'diagnostic_candidate_audit_v2.json'
EXPECTED = {'world.sdf', 'map.pgm', 'map.yaml', 'manifest.json', 'execution_catalog.json',
            'landmark_scene.yaml', 'ordered_geometry.json', 'verified_ordered_geometry.json', 'geometry_audit.json'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(node):
    return (node.tag, tuple(sorted(node.attrib.items())), (node.text or '').strip(), tuple(canonical(c) for c in node))


def check(directory, occluder):
    directory = Path(directory)
    match = re.fullmatch(r'expansion-v1-r(00[1-9]|010)-(chair|doorway|laboratory_entrance|office_entrance)-s1-view0', directory.name)
    if not match:
        raise ValueError('development-only candidate path required before source reads')
    audit = json.loads((directory / AUDIT).read_bytes())
    treatment = 'occluder' if occluder else 'sphere'
    if (audit.get('schema_version') != 'research3-expansion-diagnostic-candidate/v2' or audit.get('treatment') != treatment
            or audit['map_id'] != 'r3geo_base_r' + match[1] or audit['category'] != match[2]
            or audit.get('execution_authorized') is not False or audit.get('human_labels_generated') is not False):
        raise ValueError('candidate identity, treatment or authority mismatch')
    source = ROOT / 'data/physical_worlds_readable_v1' / ('base-r' + match[1])
    for key, base in (('source_sha256', source), ('derivative_sha256', directory)):
        if set(audit[key]) != EXPECTED:
            raise ValueError('exact asset hash set required')
        if any(sha(base / name) != digest for name, digest in audit[key].items()):
            raise ValueError('asset hash mismatch')
    original = ET.parse(source / 'world.sdf').getroot()
    derivative = ET.parse(directory / 'world.sdf').getroot()
    world = derivative.find('world')
    prefix = 'expansion_occluder_' if occluder else 'expansion_diagnostic_sphere_'
    additions = [m for m in world.findall('model') if m.get('name', '').startswith(prefix)]
    if len(additions) != 1:
        raise ValueError('exactly one diagnostic model required')
    model = additions[0]
    if model.findall('.//collision') or model.findall('.//plugin'):
        raise ValueError('visual-only constraint violated')
    world.remove(model)
    if canonical(derivative) != canonical(original):
        raise ValueError('original SDF subtree differs')
    for name in EXPECTED - {'world.sdf', 'manifest.json'}:
        if (source / name).read_bytes() != (directory / name).read_bytes():
            raise ValueError('non-world asset changed')
    manifest = json.loads((directory / 'manifest.json').read_bytes())
    source_manifest = json.loads((source / 'manifest.json').read_bytes())
    if manifest['world_sha256'] != sha(directory / 'world.sdf'):
        raise ValueError('manifest world hash mismatch')
    source_manifest['world_sha256'] = manifest['world_sha256']
    if manifest != source_manifest:
        raise ValueError('unexpected manifest change')
    centre, rotation = rendering_camera(audit['capture_pose'])
    if not np.allclose(centre, audit['camera_model']['centre'], atol=1e-9):
        raise ValueError('audit camera centre differs from the rendering camera model')
    static_issues = []
    walls = manifest['layout']['walls']
    if occluder:
        values = [float(v) for v in model.findtext('pose').split()]
        screen_centre = np.array(values[:3])
        screen_rotation = rotation_from_rpy(*values[3:])
        if not np.allclose(screen_rotation, rotation, atol=1e-7, rtol=0):
            raise ValueError('SDF screen not aligned with the rendering camera optical plane')
        size = np.array([float(v) for v in model.findtext('.//visual/geometry/box/size').split()])
        corners = np.array([screen_centre + screen_rotation @ (np.array(s) * size / 2) for s in itertools.product((-1, 1), repeat=3)])
        lo, hi = corners.min(0), corners.max(0)
        if lo[2] < 0:
            static_issues.append('below_ground')
        for i, w in enumerate(walls):
            if all(lo[j] < w[k] + w[sz] / 2 and hi[j] > w[k] - w[sz] / 2 for j, k, sz in [(0, 'x', 'sx'), (1, 'y', 'sy')]):
                static_issues.append('conservative_wall_aabb_overlap_' + str(i))
        if not math.isclose(audit['analytic_occluded_fraction'], .2, abs_tol=1e-10):
            raise ValueError('analytic area fraction differs')
        if not np.allclose(screen_centre, audit['screen_center'], atol=1e-9) or not np.allclose(size, audit['screen_size'], atol=1e-9):
            raise ValueError('screen pose/size differs from audit')
    else:
        values = [float(v) for v in model.findtext('pose').split()]
        if not np.allclose(values[:3], audit['sphere_pose'], atol=1e-9) or float(model.findtext('.//visual/geometry/sphere/radius')) != .2:
            raise ValueError('sphere pose/radius differs from audit')
        x, y = values[:2]
        clearance = min(math.hypot(max(abs(x - w['x']) - w['sx'] / 2, 0), max(abs(y - w['y']) - w['sy'] / 2, 0)) for w in walls)
        if clearance < .22:
            static_issues.append('wall_clearance')
        if math.hypot(x - centre[0], y - centre[1]) < .5:
            static_issues.append('camera_clearance')
    return dict(candidate_id=directory.name, treatment=treatment, audit_sha256=sha(directory / AUDIT),
                integrity_and_geometry_passed=True, static_issues=static_issues,
                rendered_visual_preflight_passed=False, execution_authorized=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--occluder-assets', type=Path, required=True)
    parser.add_argument('--sphere-assets', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    rows = []
    for occluder, folder in ((True, args.occluder_assets), (False, args.sphere_assets)):
        index = json.loads((folder / 'index.json').read_bytes())
        ids = [r['candidate_id'] for r in index['results'] if r['status'] == 'candidate_built']
        if len(ids) != 40 or len(set(ids)) != 40:
            raise ValueError('complete 40-candidate panel required')
        rows.extend(check(folder / identifier, occluder) for identifier in ids)
    result = dict(schema_version='research3-expansion-diagnostic-static-audit/v2', candidates=len(rows), rows=rows,
                  all_static_checks_passed=all(not r['static_issues'] for r in rows),
                  all_rendered_checks_passed=False, human_approval_present=False, execution_authorized=False)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}))


if __name__ == '__main__':
    main()
