#!/usr/bin/env python3
"""Construct diagnostic occluder candidates with explicit analytic area scope.

Area is the projected convex silhouette of the exact provider marker box, not
the full semantic object. This operational definition needs human asset review.
No rendered visibility or observed occlusion is claimed by this offline builder.
"""
import argparse
import itertools
import json
import math
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

import numpy as np
from prepare_expansion_distractors import build as checked_source_build, ROOT
from build_readable_physical_worlds import FILES, canonical, digest


def hull(points):
    points = sorted(set(map(tuple, points)))
    def cross(o,a,b): return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lower=[]; upper=[]
    for sequence,half in ((points,lower),(list(reversed(points)),upper)):
        for p in sequence:
            while len(half)>=2 and cross(half[-2],half[-1],p)<=0:half.pop()
            half.append(p)
    return lower[:-1]+upper[:-1]


def area(poly):
    if len(poly)<3:return 0.
    return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1])))/2


def clip_left(poly, boundary):
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        inside_a,inside_b=a[0]<=boundary,b[0]<=boundary
        if inside_a:result.append(a)
        if inside_a != inside_b:
            ratio=(boundary-a[0])/(b[0]-a[0])
            result.append((boundary,a[1]+ratio*(b[1]-a[1])))
    return result


def area_cut(poly, fraction=.2):
    total=area(poly)
    if total<=1e-12 or not 0<fraction<1:raise ValueError('nondegenerate silhouette and area fraction required')
    left,right=min(p[0] for p in poly),max(p[0] for p in poly)
    for _ in range(70):
        mid=(left+right)/2
        if area(clip_left(poly,mid))/total < fraction:left=mid
        else:right=mid
    return (left+right)/2


def rotation(q):
    x,y,z,w=(q[k] for k in ('x','y','z','w'))
    if not math.isclose(x*x+y*y+z*z+w*w,1.,abs_tol=1e-5):raise ValueError('unit camera quaternion required')
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])


def build(row, output):
    # Reuse complete source identity/hash/pose checks, without changing that tool.
    with tempfile.TemporaryDirectory(prefix='r3-occluder-source-') as temporary:
        prior=checked_source_build(ROOT,row,Path(temporary)/'checked')
    base=row['map_id'].removeprefix('r3geo_').replace('_','-')
    source=ROOT/'data/physical_worlds_readable_v1'/base
    raw={name:(source/name).read_bytes() for name in FILES}
    tree=ET.fromstring(raw['world.sdf']); world=tree.find('world'); original=canonical(tree)
    marker=world.find(f"model[@name='{prior['source_marker_model']}']")
    pose=[float(v) for v in marker.findtext('pose').split()]
    size=[float(v) for v in marker.findtext('.//visual/geometry/box/size').split()]
    if any(abs(v)>1e-10 for v in pose[3:]):raise ValueError('rotated marker needs separate projection implementation')
    visual=marker.find('.//visual')
    if visual.find('pose') is not None:raise ValueError('local marker pose not supported')
    category='laboratory_entrance' if row['category']=='doorway' else row['category']
    run=ROOT/'reports/physical_live_episodes'/f'r3-current-v1-r{base[-3:]}-{category}'
    request_raw=(run/'request.json').read_bytes()
    if digest(request_raw)!=row['pilot_request_sha256']:raise ValueError('pilot request changed')
    frame_raw=(run/'perception_capture/frame-000.json').read_bytes()
    frame=json.loads(frame_raw)
    if frame.get('transform_error') is not None:raise ValueError('missing usable camera transform')
    transform=frame['camera_to_map']['transform']
    R=rotation(transform['rotation']); camera=np.array([transform['translation'][k] for k in ('x','y','z')])
    points=np.array([np.array(pose[:3])+np.array(signs)*np.array(size)/2
                     for signs in itertools.product((-1,1),repeat=3)])
    optical=(points-camera)@R
    if np.min(optical[:,2])<=.10:raise ValueError('target behind or too close to camera')
    poly=hull(optical[:,:2]/optical[:,2,None]); boundary=area_cut(poly)
    x0=min(p[0] for p in poly); y0=min(p[1] for p in poly); y1=max(p[1] for p in poly)
    distance=float(np.min(optical[:,2])*.7)
    center=camera+R@np.array([(x0+boundary)*distance/2,(y0+y1)*distance/2,distance])
    # A camera-facing rectangular neutral visual. Its front plane is exactly
    # at the analytic projection depth, with thickness extending away from camera.
    thickness=.002
    center=center+R[:,2]*thickness/2
    pitch=math.asin(max(-1.,min(1.,-float(R[2,0]))))
    roll=math.atan2(R[2,1],R[2,2]); yaw=math.atan2(R[1,0],R[0,0])
    model=ET.SubElement(world,'model',name='expansion_occluder_'+row['entity_id'])
    ET.SubElement(model,'static').text='true'
    ET.SubElement(model,'pose').text=' '.join(str(float(v)) for v in (*center,roll,pitch,yaw))
    link=ET.SubElement(model,'link',name='visual_only'); vis=ET.SubElement(link,'visual',name='neutral_occluder')
    geo=ET.SubElement(vis,'geometry')
    dimensions=[(boundary-x0)*distance,(y1-y0)*distance,thickness]
    ET.SubElement(ET.SubElement(geo,'box'),'size').text=' '.join(map(str,dimensions))
    material=ET.SubElement(vis,'material')
    for key in ('ambient','diffuse'):ET.SubElement(material,key).text='.45 .45 .45 1'
    ET.SubElement(vis,'cast_shadows').text='false'
    world.remove(model)
    if canonical(tree)!=original:raise AssertionError('original geometry changed')
    world.append(model)
    if model.findall('.//collision') or model.findall('.//plugin'):raise AssertionError('visual-only required')
    raw['world.sdf']=ET.tostring(tree,encoding='utf-8',xml_declaration=True)
    manifest=json.loads(raw['manifest.json']); manifest['world_sha256']=digest(raw['world.sdf'])
    raw['manifest.json']=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()
    audit={
        'schema_version':'research3-expansion-occluder-candidate/v1',
        'status':'analytic_candidate_pending_rendered_preflight_and_human_definition_approval',
        'map_id':row['map_id'],'entity_id':row['entity_id'],'category':row['category'],
        'capture_pose':row['capture_pose'],'marker_model':prior['source_marker_model'],
        'area_reference':'projected_convex_silhouette_of_provider_marker_box_not_full_semantic_object',
        'analytic_occluded_fraction':area(clip_left(poly,boundary))/area(poly),
        'requested_fraction':.2,'polygon_normalized_camera':poly,'cut_x':boundary,
        'camera_transform_source_sha256':digest(frame_raw),'camera_transform_source':str(run.relative_to(ROOT)/'perception_capture/frame-000.json'),
        'screen_center':center.tolist(),'screen_size':dimensions,
        'camera_plane_depth':distance,'screen_rpy':[roll,pitch,yaw],
        'screen_wall_intersection_checked':False,'rendered_fraction_verified':False,
        'full_object_occlusion_claimed':False,'execution_authorized':False,
        'included_in_primary_calibration':False,'human_labels_generated':False,
        'original_sdf_subtree_unchanged':True,'source_sha256':prior['source_sha256'],
        'derivative_sha256':{k:digest(v) for k,v in raw.items()},
    }
    if any(digest((source/k).read_bytes())!=v for k,v in prior['source_sha256'].items()):raise ValueError('source changed during build')
    output.mkdir(parents=True,exist_ok=False)
    for name,value in raw.items():
        with (output/name).open('xb') as stream:stream.write(value)
    with (output/'occluder_candidate_audit.json').open('x') as stream:json.dump(audit,stream,indent=2,sort_keys=True)
    return audit


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    plan_raw=(ROOT/'reports/calibration_expansion_proposal_20260911_v2/plan.json').read_bytes()
    approval=json.loads((ROOT/'reports/calibration_expansion_handoff_20260912_v1/amendment_review_decision.json').read_bytes())
    if digest(plan_raw)!=approval['plan_sha256']:raise ValueError('accepted plan hash mismatch')
    rows=[r for r in json.loads(plan_raw)['rows'] if r['partition']=='development' and r['seed']==1 and r['candidate_id'].endswith('-view0')]
    if len(rows)!=40:raise ValueError('40 development targets required')
    args.output.mkdir(parents=True,exist_ok=False);results=[]
    for row in rows:
        try:
            a=build(row,args.output/row['candidate_id'])
            results.append({'candidate_id':row['candidate_id'],'status':'candidate_built','analytic_fraction':a['analytic_occluded_fraction']})
        except ValueError as exc:results.append({'candidate_id':row['candidate_id'],'status':'blocked','reason':str(exc)})
    with (args.output/'index.json').open('x') as stream:json.dump({'results':results,'execution_authorized':False},stream,indent=2)
    print(json.dumps({'built':sum(r['status']=='candidate_built' for r in results),'blocked':[r for r in results if r['status']=='blocked']}))


if __name__=='__main__':main()
