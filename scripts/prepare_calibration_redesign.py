"""Prepare geometry-preserving lighting candidates and an exact non-executable plan.

Reads static development/validation geometry and an old planning manifest only;
never opens validation outcomes/labels or launches a simulator. Create-once output.
"""
import copy
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import xml.etree.ElementTree as ET

import yaml
from language_nav.capture_view import validate_capture_pose
from prepare_calibration_expansion import EXPECTED_COVERAGE
from run_stage1_feasibility import ROOT,sha,write
from snapshot_expansion_instrumentation import validate as validate_snapshot

CONFIG=ROOT/'configs/calibration_redesign_v2.yaml'
OUTPUT=ROOT/'reports/calibration_redesign_20260923_v1'


def validate_config(config):
    if config.get('schema_version')!='research3-calibration-redesign-proposal/v2':raise ValueError('schema')
    if config.get('coverage')!=EXPECTED_COVERAGE:raise ValueError('coverage floors changed')
    for flag in ('execution_authorized','primary_collection_authorized','calibration_freeze_authorized','protected_access_authorized'):
        if config.get(flag) is not False:raise ValueError('preparation only')
    if config['classes']!=['chair','doorway','laboratory_entrance','office_entrance']:raise ValueError('classes')
    if (config['feasibility']['development_maps']!=[1,6]
            or config['primary_candidate']['development_maps']!=list(range(1,11))
            or config['primary_candidate']['validation_maps']!=list(range(11,15))):
        raise ValueError('exact nonprotected map lists required before asset reads')
    c=config['conditions']
    if (c['source_view_indices']!=[0,3] or c['yaw_offsets_rad']!=[0.,-.95,.95]
            or c['lighting_scales']!=[1.,.9,.8] or c['horizontal_fov_rad']!=2.):raise ValueError('fixed design changed')
    if config['feasibility']['simulator_seeds']!=[7] or config['primary_candidate']['simulator_seeds']!=[11,12]:raise ValueError('seeds')
    if config['primary_candidate']['old_primary_pilot_diagnostic_and_feasibility_rows_pooled'] is not False:
        raise ValueError('historical pooling forbidden')
    if config['feasibility']['calibration_eligible'] is not False:raise ValueError('pilot cannot be primary')
    for name in ('noise_added','occluders_or_distractors_added','marker_materials_or_geometry_changed',
                 'provider_formula_palette_thresholds_or_association_changed','camera_fov_or_intrinsics_changed'):
        if c.get(name) is not False:raise ValueError('unapproved nonlighting change')
    if any(v is not True for v in config['preserve'].values()):raise ValueError('preservation constraints')
    if (config['feasibility']['fixed_attempts']!=144 or config['primary_candidate']['development_attempts']!=1440
            or config['primary_candidate']['validation_attempts']!=576 or config['primary_candidate']['total_attempts']!=2016):
        raise ValueError('declared counts differ')
    for name in ('nondetection_is_negative_label','infrastructure_failure_is_nondetection','outcome_conditioned_retries_or_replacements'):
        if config['sampling'].get(name) is not False:raise ValueError('sampling integrity')


def canonical(element):
    return (element.tag,tuple(sorted(element.attrib.items())),(element.text or '').strip(),
            tuple(canonical(child) for child in element))


def invariant_tree(root):
    """Remove ONLY the two declared lighting fields before structural comparison."""
    value=copy.deepcopy(root);world=value.find('world')
    if world is None:raise ValueError('world missing')
    for light in world.findall('light'):
        if light.get('name')=='sun':
            diffuse=light.find('diffuse')
            if diffuse is not None:light.remove(diffuse)
    scene=world.find('scene')
    if scene is not None:
        ambient=scene.find('ambient')
        if ambient is not None:scene.remove(ambient)
        if not list(scene) and not scene.attrib and not (scene.text or '').strip():world.remove(scene)
    return canonical(value)


def lighting_variant(raw,scale):
    if scale not in (1.,.9,.8):raise ValueError('undeclared lighting scale')
    original=ET.fromstring(raw);root=copy.deepcopy(original);world=root.find('world')
    lights=world.findall('light')
    if len(lights)!=1 or lights[0].get('name')!='sun' or lights[0].get('type')!='directional':
        raise ValueError('one declared directional sun required')
    light=lights[0];diffuse=light.find('diffuse')
    values=[float(x) for x in diffuse.text.split()]
    if values!=[.9,.9,.9,1.]:raise ValueError('unexpected source diffuse')
    scene=world.find('scene')
    if scene is not None:raise ValueError('unexpected explicit scene requires separate review')
    if scale==1.:return raw  # exact-byte control, not a reserialized approximation
    scene=ET.SubElement(world,'scene')
    ET.SubElement(scene,'ambient').text=' '.join(str(v) for v in ([.4*scale]*3+[1.]))
    diffuse.text=' '.join(str(v*scale) for v in values[:3])+' 1.0'
    if invariant_tree(root)!=invariant_tree(original):raise ValueError('nonlighting world content changed')
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)


def build():
    config=yaml.safe_load(CONFIG.read_bytes());validate_config(config)
    if OUTPUT.exists():raise FileExistsError(OUTPUT)
    snapshot=ROOT/'reports/expansion_instrumentation_snapshot_20260922_v8/snapshot.json'
    validate_snapshot(snapshot)
    old_path=ROOT/'reports/calibration_expansion_proposal_20260911_v2/plan.json'
    old=json.loads(old_path.read_bytes())
    seeds={}
    for row in old['rows']:
        if row['seed']==1 and row['view_group'].endswith(('-view0','-view3')):
            key=(row['map_id'],row['category'],int(row['view_group'][-1]))
            if key in seeds:raise ValueError('duplicate old plan identity')
            seeds[key]=row
    prepared={};assets=[];source_hashes={};errors=[]
    for number in range(1,15):
        partition='development' if number<=10 else 'validation'
        world=ROOT/f'data/physical_worlds_readable_v1/base-r{number:03}'
        scene=yaml.safe_load((world/'landmark_scene.yaml').read_bytes())
        if scene['partition']!=partition:raise ValueError('static scene partition mismatch')
        map_id=f'r3geo_base_r{number:03}'
        raw=(world/'world.sdf').read_bytes()
        for scale in config['conditions']['lighting_scales']:
            name=f'light{round(scale*100):03}'
            variant=lighting_variant(raw,scale)
            path=OUTPUT/'worlds'/f'base-r{number:03}'/name/'world.sdf'
            assets.append((path,variant,dict(map_id=map_id,partition=partition,lighting_scale=scale,
                source_world_sha256=sha(world/'world.sdf'),world_sha256=hashlib.sha256(variant).hexdigest(),
                world_path=str(path.relative_to(ROOT)),nonlighting_tree_unchanged=True,rendered_preflight_passed=False)))
        for category,view in itertools.product(config['classes'],config['conditions']['source_view_indices']):
            prior=seeds[(map_id,category,view)]
            if prior['partition']!=partition:raise ValueError('planning partition mismatch')
            for name,digest in prior['world_sha256'].items():
                if sha(world/name)!=digest:raise ValueError('original static asset drift')
                source_hashes[str((world/name).relative_to(ROOT))]=digest
            profile=ROOT/'reports'/('fresh_current_capture_20260911_v1' if number<=10 else 'engineering_camera_settings_v3')/'profiles'/f'base-r{number:03}.yaml'
            if sha(profile)!=prior['camera_profile_sha256']:raise ValueError('profile drift')
            source_hashes[str(profile.relative_to(ROOT))]=sha(profile)
            entity=next(e for e in scene['entities'] if e['entity_id']==prior['entity_id'])
            x,y=(prior['capture_pose'][k] for k in ('x','y'))
            yaw=math.atan2(entity['pose']['y']-y,entity['pose']['x']-x)
            for offset in config['conditions']['yaw_offsets_rad']:
                pose=dict(x=x,y=y,yaw=yaw+offset)
                try:validate_capture_pose(world,**pose);status='passed'
                except ValueError as exc:status='infeasible';errors.append(dict(map_id=map_id,category=category,view=view,offset=offset,error=str(exc)))
                prepared[(number,category,view,offset)]=dict(map_id=map_id,partition=partition,category=category,
                    entity_id=entity['entity_id'],source_view_index=view,capture_pose=pose,yaw_offset_rad=offset,
                    pose_preflight=status,world_directory=str(world.relative_to(ROOT)),
                    camera_profile=str(profile.relative_to(ROOT)),camera_profile_sha256=sha(profile),
                    visibility_guaranteed=False,full_context_reviewability_verified=False)
    panels={}
    for panel,numbers,sim_seeds in (
        ('design_feasibility',[1,6],[7]),('primary_candidate',list(range(1,15)),[11,12])):
        rows=[]
        for number,category,view,offset,scale,seed in itertools.product(numbers,config['classes'],
                config['conditions']['source_view_indices'],config['conditions']['yaw_offsets_rad'],config['conditions']['lighting_scales'],sim_seeds):
            base=prepared[(number,category,view,offset)]
            oi=config['conditions']['yaw_offsets_rad'].index(offset);lighting=f'light{round(scale*100):03}'
            condition=f'view{view}-yaw{oi}-{lighting}'
            rows.append(dict(base,candidate_id=f'r3-redesign-v2-{panel}-r{number:03}-{category}-{condition}-s{seed}',
                panel=panel,condition=condition,view_group=f'{base["map_id"]}-{category}-{condition}',
                simulator_seed=seed,lighting_scale=scale,
                derivative_world_path=str((OUTPUT/'worlds'/f'base-r{number:03}'/lighting/'world.sdf').relative_to(ROOT)),
                execution_authorized=False,calibration_eligible=False,human_label=None))
        random.Random(config['sampling']['order_seed']).shuffle(rows)
        panels[panel]=rows
    if len(panels['design_feasibility'])!=144 or len(panels['primary_candidate'])!=2016:raise ValueError('fixed budget')
    OUTPUT.mkdir()
    for path,raw,_ in assets:
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(raw)
    plan=dict(schema_version='research3-calibration-redesign-plan/v2',config_sha256=sha(CONFIG),
        source_plan_sha256=sha(old_path),capture_snapshot_sha256=sha(snapshot),source_sha256=source_hashes,
        generator_sha256=sha(__file__),assets=[a[2] for a in assets],panels=panels,
        static_pose_failures=errors,static_pose_checks=len(prepared),
        execution_authorized=False,primary_collection_authorized=False,protected_access_authorized=False,
        validation_outcomes_or_labels_read=False,static_validation_geometry_read=True,
        simulator_launched=False,human_labels_generated=False,coverage_complete=False,
        blockers=['rendered_feasibility_and_unchanged_provider_capture_admission_not_verified',
                  'pilot_confidence_support_then_genuine_joint_review',
                  'exact_new_primary_distribution_amendment_approval_before_collection'])
    write(OUTPUT/'plan.json',plan)
    validate_snapshot(snapshot)
    write(OUTPUT/'static_audit.json',dict(world_variants=len(assets),static_pose_checks=len(prepared),
        static_pose_failures=errors,all_nonlighting_world_content_unchanged=True,source_snapshot_unchanged=True,
        design_only_attempts=144,primary_candidate_attempts=2016,
        rendered_visibility_verified=False,coverage_complete=False,plan_sha256=sha(OUTPUT/'plan.json')))
    print(json.dumps(dict(output=str(OUTPUT),world_variants=len(assets),static_pose_checks=len(prepared),failures=errors)))


if __name__=='__main__':build()
