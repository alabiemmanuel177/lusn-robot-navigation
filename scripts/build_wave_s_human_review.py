"""Portable, score-blinded Wave S observation review; no human labels generated."""
from collections import Counter
import json
import math
from pathlib import Path
import zipfile
import numpy as np
from PIL import Image, ImageDraw
import yaml

from prepare_joint_score_protocol import ROOT, sha
from joint_score_components import digest, duplicate_accounting
from joint_score_collection import write_once
from joint_score_pipeline import decode_rgb
from bound_pose_observer import matrix
from candidate_rendering_transform import correction
from fit_joint_score_wave_s import validate_execution

OUT = ROOT/'reports/joint_score_wave_s_human_review_20260924_v2'
SOURCE = ROOT/'reports/joint_score_wave_s_primary_inference_20260924_v1'
CAPTURE = ROOT/'reports/joint_score_wave_s_primary_20260924_v1'


def read(p): return json.loads(Path(p).read_text())


def require(condition, message):
    if not condition: raise ValueError(message)


def optical_forward(camera):
    """Optical columns are right, down, forward: viewing direction is +Z."""
    return camera[:3,2]


def main():
    evidence = read(SOURCE/'evidence.json')
    complete = read(ROOT/'reports/joint_score_wave_s_supervisor_20260924_v1/complete.json')
    require(sha(SOURCE/'evidence.json') == complete['evidence_sha256'], 'evidence changed')
    authority = ROOT/'reports/joint_score_wave_s_execution_20260924_v1'
    manifest = read(authority/'execution_manifest.json')
    validate_execution(manifest, read(authority/'execution_approval.json'),
        protocol_sha=evidence['protocol_sha256'], schedule_sha=evidence['schedule_sha256'])
    require(digest(manifest)==evidence['execution_manifest_sha256'],'execution evidence binding')
    schedule = read(ROOT/'reports/joint_score_protocol_20260924_v1/schedule.json')
    slots = [r for r in schedule['rows'] if r['wave']=='S']
    require(len(slots)==len(evidence['attempts'])==400 and
        [r['attempt_id'] for r in slots]==[r['attempt_id'] for r in evidence['attempts']], 'complete ordered S ledger')
    # Verify every completion record dependency once, rather than hashing models
    # 398 times. This also verifies all raw detector arrays and source bytes.
    pins = dict(manifest['input_sha256'])
    completions = sorted((SOURCE/'integration').glob('completion-*.json'))
    require(len(completions)==400,'all completion records required')
    for p in completions:
        value = read(p)
        for engine in ('detector','ocr'):
            if value[engine] is not None:
                require(value[engine]['status']=='completed' and value[engine]['audit_passed'], 'inference completion')
                for path,h in value[engine]['input_sha256'].items():
                    require(path not in pins or pins[path]==h,'conflicting source pin')
                    pins[path]=h
    for path,h in pins.items(): require(sha(path)==h,'changed source: '+path)
    OUT.mkdir(exist_ok=False); (OUT/'images').mkdir()
    items=[]; checks=[]; accounted=duplicate_accounting(evidence['attempts'])
    for slot,row in zip(slots,accounted,strict=True):
        if not row['fitting_eligible']: continue
        run=CAPTURE/row['attempt_id']; frame=read(run/'frame-000.json'); plan=read(run/'plan.json')
        require(sha(run/'frame-000.json')==row['frame_sha256'],'frame binding')
        for channel in ('rgb','depth'):
            require(sha(run/frame[channel]['file'])==frame[channel]['sha256'],'raw image binding')
        rgb=decode_rgb((run/frame['rgb']['file']).read_bytes(),frame['rgb'])
        world=ROOT/slot['world_directory'];scene=yaml.safe_load((world/'landmark_scene.yaml').read_text())
        require(scene['partition']=='development','development only')
        refs=scene['entities'];map_spec=yaml.safe_load((world/'map.yaml').read_text())
        tf=frame['camera_to_map']['transform'];p,q=tf['translation'],tf['rotation']
        camera=correction(matrix([p[k] for k in ('x','y','z')],[q[k] for k in ('x','y','z','w')]),
                          np.array(plan['nominal_mount']),np.array(plan['rendered_mount']))
        for emission in row['emissions']:
            body=dict(emission);identity=body.pop('emission_id')
            require(digest(body)==identity,'emission identity')
            matches=[(i,e) for i,e in enumerate(refs) if e['entity_id']==emission['entity_id']]
            require(len(matches)==1,'unique catalogue reference')
            ref_index,ref=matches[0]
            box=np.array(emission['box'],float);h,w=rgb.shape[:2]
            require(box.shape==(4,) and np.isfinite(box).all() and
                0<=box[0]<box[2]<=w and 0<=box[1]<box[3]<=h,'visible valid detection box')
            require(float(rgb.std())>8,'nondegenerate frame')
            n=len(items);base=f'images/item-{n+1:03}'
            original=Image.fromarray(rgb);original.save(OUT/(base+'-original.png'))
            annotated=original.copy();ImageDraw.Draw(annotated).rectangle(box.tolist(),outline='#e27300',width=3)
            annotated.save(OUT/(base+'-target.png'))
            map_image=Image.open(world/map_spec['image']).convert('RGB').resize(
                (Image.open(world/map_spec['image']).width*3,Image.open(world/map_spec['image']).height*3),Image.Resampling.NEAREST)
            md=ImageDraw.Draw(map_image);resolution=map_spec['resolution'];origin=map_spec['origin']
            def pixel(x,y):return ((x-origin[0])/resolution*3,map_image.height-(y-origin[1])/resolution*3)
            for i,e in enumerate(refs):
                x,y=pixel(e['pose']['x'],e['pose']['y']);md.ellipse((x-4,y-4,x+4,y+4),fill='#243747');md.text((x+6,y-12),str(i+1),fill='#125c86',stroke_width=1,stroke_fill='white')
            x,y=pixel(ref['pose']['x'],ref['pose']['y']);md.ellipse((x-11,y-11,x+11,y+11),outline='#e27300',width=3)
            x,y=pixel(*emission['map_pose']);md.line((x-7,y-7,x+7,y+7),fill='#e27300',width=3);md.line((x-7,y+7,x+7,y-7),fill='#e27300',width=3)
            x,y=pixel(*camera[:2,3]);tx,ty=pixel(*(camera[:2,3]+.55*optical_forward(camera)[:2]));md.ellipse((x-5,y-5,x+5,y+5),fill='#125c86');md.line((x,y,tx,ty),fill='#125c86',width=4)
            angle=math.atan2(ty-y,tx-x)
            for delta in (-.55,.55):md.line((tx,ty,tx-12*math.cos(angle+delta),ty-12*math.sin(angle+delta)),fill='#125c86',width=3)
            map_image.save(OUT/(base+'-map.png'))
            rp=[ref['pose']['x'],ref['pose']['y']];dist=math.dist(emission['map_pose'],rp)
            require(abs(dist-emission['reference_distance_m'])<1e-9,'reference distance consistency')
            items.append(dict(emission_id=identity,emission_sha256=digest(emission),category=emission['category'],
                entity_id=emission['entity_id'],attempt_id=row['attempt_id'],original_image=base+'-original.png',
                annotated_image=base+'-target.png',map_image=base+'-map.png',map_pose=emission['map_pose'],reference_pose=rp,distance_m=dist,
                context=f"Map: {slot['map_id']}\nClaimed reference number: {ref_index+1}\nClaimed region: {ref['region_id']}\nMeasured corrected camera xyz: {camera[:3,3].tolist()}\nCamera forward vector in map: {optical_forward(camera).tolist()}\nScheduled spawn pose (context only, not measured object pose): {slot['capture_pose']}",
                catalogue='\n'.join(f"{i+1}. {e['entity_id']} | {e['category']} | region {e['region_id']} | x={e['pose']['x']:.4f}, y={e['pose']['y']:.4f}" for i,e in enumerate(refs)),
                depth_evidence=dict(support=emission['support'],box_pixels=emission['box'],frame_sha256=row['frame_sha256'],
                    rgb_sha256=frame['rgb']['sha256'],depth_sha256=frame['depth']['sha256'],
                    observed_at_ns=emission['observed_at_ns'],point_scope='Planar reference-point consistency; not full object geometry.',
                    yaw='not_applicable: no emitted yaw in this score-learning observation')))
            checks.append(dict(emission_id=identity,frame_hash_passed=True,rgb_depth_hash_passed=True,
                finite_in_frame_box=True,nondegenerate_frame=True,reference_distance_verified=True,
                human_reviewability_established=False,human_verdict=None))
    require(len(items)==287,'expected complete emission inventory, no silent omissions')
    data=dict(schema_version='research3-wave-s-blinded-review-presentation/v1',wave='S',
        evidence_sha256=digest(evidence),items=items,confidence_scores_included=False)
    # Presentation deliberately uses a whitelist, never the raw emission dict.
    raw=json.dumps(data,allow_nan=False).replace('</','<\\/')
    (OUT/'review_data.js').write_text('const DATA = '+raw+';\n')
    (OUT/'index.html').write_bytes((ROOT/'scripts/wave_s_review.html').read_bytes())
    instructions='''# Wave S human observation review

Open index.html in Chrome, Firefox or Edge. No install, server, login or network
connection is required. Keep index.html, review_data.js and images/ together.

1. Confirm/edit your name and role. Do not confirm personal review until it is true.
2. Review all 287 items using the full image, target outline, original image,
   camera/map context and numbered catalogue references.
3. Independently select category, physical instance and reference point as
   correct, incorrect or unreviewable. No answer is preselected.
4. Category/instance: judge visible evidence, not colour or nearest coordinates
   alone. Doorways require opening/jamb context; LAB/OFFICE subtype needs context.
5. Reference point: compare reported x/y with the claimed reference using the
   inclusive 0.35 m planar threshold. Do not interpret it as 3D geometry accuracy.
   Yaw is not emitted by this new scorer: it is not applicable to this review.
6. Give a reason for every item containing an unreviewable dimension. Do not
   manufacture negative labels or force a binary answer from ambiguous evidence.
7. Click Download progress backup regularly and before closing the browser.
   Browser local storage is a convenience, not a reliable backup. Restore a
   downloaded backup using Restore backup if necessary.
8. When all items are complete, confirm your personal judgments, then click
   Download final review return. Send wave-s-review-return.json back to the agent.
   It will normally be in your browser Downloads folder. Do not edit IDs/hashes.

This approves observation labels only, not a model, calibration, Wave C/V or a
campaign. Raw, learned and calibrated probabilities are absent from this kit.
All 400 attempts remain accounted for: 287 scoreable observations, 72 abstentions,
39 nondetections, 2 infrastructure failures. No duplicate frames were excluded.
Only emitted observations receive labels; non-emissions are NOT negatives.
All ten development maps have at least one emission in each class, but correct/
incorrect outcome floors and suitability cannot be established before review.

Joint logic: any incorrect dimension => incorrect; all three correct => correct;
otherwise unreviewable. The interface calculates this from your three choices.
The machine presentation audit verifies joins/bytes/box bounds, not whether a
human can identify every item. Use unreviewable whenever evidence is insufficient.
'''
    (OUT/'README.md').write_text(instructions)
    write_once(OUT/'presentation_audit.json',dict(rows=checks,items=len(items),source_files_checked=len(pins),
        class_counts=dict(Counter(r['category'] for r in items)),human_labels_generated=False,
        human_reviewability_established=False,duplicate_frames_excluded=sum(bool(r['duplicate_of']) for r in accounted)))
    write_once(OUT/'attempt_accounting.json',dict(attempts=[dict(attempt_id=r['attempt_id'],status=r['status'],
        perception_status=r.get('perception_status'),emissions=len(r['emissions']),duplicate_of=r['duplicate_of']) for r in accounted]))
    files={str(p.relative_to(OUT)):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file()}
    write_once(OUT/'kit_manifest.json',dict(schema_version='research3-wave-s-blinded-kit/v1',files=files,
        evidence_sha256=digest(evidence),source_evidence_file_sha256=sha(SOURCE/'evidence.json'),
        builder_sha256=sha(__file__),items=len(items),human_labels_generated=False))
    archive=OUT.with_suffix('.zip')
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(OUT.rglob('*')):
            if p.is_file():z.write(p,str(Path(OUT.name)/p.relative_to(OUT)))
    print(json.dumps(dict(items=len(items),directory=str(OUT),archive=str(archive),archive_sha256=sha(archive)),indent=2))


if __name__=='__main__':main()
