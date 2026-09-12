#!/usr/bin/env python3
"""Independently check candidate bytes, original geometry and screen clearance.

No rendering, execution, human approval, protected asset reads or labels.
"""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(node):
    return (node.tag,tuple(sorted(node.attrib.items())),(node.text or '').strip(),tuple(canonical(c) for c in node))


def check(directory, occluder):
    match=re.fullmatch(r'expansion-v1-r(00[1-9]|010)-(chair|doorway|laboratory_entrance|office_entrance)-s1-view0',directory.name)
    if not match:raise ValueError('development-only candidate path required before source reads')
    audit_path=directory/('occluder_candidate_audit.json' if occluder else 'diagnostic_asset_audit.json')
    a=json.loads(audit_path.read_bytes())
    if a['map_id']!='r3geo_base_r'+match[1] or a['category']!=match[2] or a['execution_authorized'] is not False:
        raise ValueError('candidate identity or authority mismatch')
    source=ROOT/'data/physical_worlds_readable_v1'/('base-r'+match[1])
    expected={'world.sdf','map.pgm','map.yaml','manifest.json','execution_catalog.json',
              'landmark_scene.yaml','ordered_geometry.json','verified_ordered_geometry.json','geometry_audit.json'}
    for key,base in [('source_sha256',source),('derivative_sha256',directory)]:
        if set(a[key])!=expected:raise ValueError('exact asset hash set required')
        if any(sha(base/name)!=h for name,h in a[key].items()):raise ValueError('asset hash mismatch')
    original=ET.parse(source/'world.sdf').getroot(); derivative=ET.parse(directory/'world.sdf').getroot()
    world=derivative.find('world');prefix='expansion_occluder_' if occluder else 'expansion_diagnostic_sphere_'
    additions=[m for m in world.findall('model') if m.get('name','').startswith(prefix)]
    if len(additions)!=1:raise ValueError('exactly one diagnostic model required')
    model=additions[0]
    if model.findall('.//collision') or model.findall('.//plugin'):raise ValueError('visual-only constraint violated')
    world.remove(model)
    if canonical(derivative)!=canonical(original):raise ValueError('original SDF subtree differs')
    for name in expected-{'world.sdf','manifest.json'}:
        if (source/name).read_bytes()!=(directory/name).read_bytes():raise ValueError('non-world asset changed')
    manifest=json.loads((directory/'manifest.json').read_bytes())
    source_manifest=json.loads((source/'manifest.json').read_bytes())
    if manifest['world_sha256']!=sha(directory/'world.sdf'):raise ValueError('manifest world hash mismatch')
    source_manifest['world_sha256']=manifest['world_sha256']
    if manifest!=source_manifest:raise ValueError('unexpected manifest change')
    static_issues=[]
    if occluder:
        values=[float(v) for v in model.findtext('pose').split()];center=np.array(values[:3]);r,p,y=values[3:]
        cr,sr=math.cos(r),math.sin(r);cp,sp=math.cos(p),math.sin(p);cy,sy=math.cos(y),math.sin(y)
        R=np.array([[cy*cp,cy*sp*sr-sy*cr,cy*sp*cr+sy*sr],
                    [sy*cp,sy*sp*sr+cy*cr,sy*sp*cr-cy*sr],[-sp,cp*sr,cp*cr]])
        size=np.array([float(v) for v in model.findtext('.//visual/geometry/box/size').split()])
        pts=np.array([center+R@(np.array(s)*size/2) for s in itertools.product((-1,1),repeat=3)])
        lo,hi=pts.min(axis=0),pts.max(axis=0)
        if lo[2]<0:static_issues.append('below_ground')
        for i,w in enumerate(manifest['layout']['walls']):
            if all(lo[j]<w[k]+w[sz]/2 and hi[j]>w[k]-w[sz]/2 for j,k,sz in [(0,'x','sx'),(1,'y','sy')]):
                static_issues.append('conservative_wall_aabb_overlap_'+str(i))
        if not math.isclose(a['analytic_occluded_fraction'],.2,abs_tol=1e-10):raise ValueError('analytic area fraction differs')
        # Verify serialized SDF orientation against the bound camera transform.
        frame_path=ROOT/a['camera_transform_source']
        expected_run=f'r3-current-v1-r{match[1]}-'+('laboratory_entrance' if match[2]=='doorway' else match[2])
        expected_frame=ROOT/'reports/physical_live_episodes'/expected_run/'perception_capture/frame-000.json'
        if frame_path!=expected_frame or sha(frame_path)!=a['camera_transform_source_sha256']:
            raise ValueError('camera transform provenance mismatch')
        transform=json.loads(frame_path.read_bytes())['camera_to_map']['transform']
        q=transform['rotation'];x,y,z,w=(q[k] for k in ('x','y','z','w'))
        camera_R=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                           [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                           [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
        if not np.allclose(R,camera_R,atol=1e-7,rtol=0):
            raise ValueError('SDF screen not aligned with bound optical plane')
    return {'candidate_id':directory.name,'treatment':'occluder' if occluder else 'sphere',
            'audit_sha256':sha(audit_path),'integrity_and_geometry_passed':True,
            'static_issues':static_issues,'rendered_visual_preflight_passed':False,
            'execution_authorized':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    rows=[]
    for occluder,family in [(False,'distractor'),(True,'occluder')]:
        folder=ROOT/f'reports/calibration_expansion_{family}_assets_20260912_v1'
        index=json.loads((folder/'index.json').read_bytes())
        if len(index['results'])!=40:raise ValueError('complete 40-candidate panel required')
        ids=[r['candidate_id'] for r in index['results']]
        if len(set(ids))!=40:raise ValueError('duplicate candidate')
        rows.extend(check(folder/identifier,occluder) for identifier in ids)
    result={'schema_version':'research3-expansion-diagnostic-static-audit/v1',
            'candidates':len(rows),'rows':rows,'all_static_checks_passed':all(not r['static_issues'] for r in rows),
            'all_rendered_checks_passed':False,'human_approval_present':False,'execution_authorized':False}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,sort_keys=True)
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}))


if __name__=='__main__':main()
