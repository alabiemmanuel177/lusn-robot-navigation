"""Independent static verification of an unapproved redesign; no execution."""
import itertools
import json
import math
from pathlib import Path
import yaml
from language_nav.capture_view import validate_capture_pose
from prepare_calibration_redesign import CONFIG,OUTPUT,lighting_variant,validate_config
from run_stage1_feasibility import ROOT,sha,write


def check_panel(rows,panel,numbers,seeds,config):
    expected=set(itertools.product(numbers,config['classes'],[0,3],[0.,-.95,.95],[1.,.9,.8],seeds))
    identities=set();seen=set()
    for row in rows:
        if (row.get('panel')!=panel or row.get('execution_authorized') is not False
                or row.get('calibration_eligible') is not False or row.get('human_label') is not None):
            raise ValueError('proposal cannot execute or supply labels')
        number=next((n for n in numbers if row['map_id']==f'r3geo_base_r{n:03}'),None)
        if number is None or row['partition']!=('development' if number<=10 else 'validation'):
            raise ValueError('map/partition scope')
        key=(number,row['category'],row['source_view_index'],row['yaw_offset_rad'],row['lighting_scale'],row['simulator_seed'])
        if key not in expected or key in seen or row['candidate_id'] in identities:raise ValueError('duplicate or unscheduled slot')
        if type(row['source_view_index']) is not int or type(row['simulator_seed']) is not int:raise ValueError('integer identities')
        seen.add(key);identities.add(row['candidate_id'])
    if seen!=expected:raise ValueError('fixed schedule incomplete')


def verify():
    config=yaml.safe_load(CONFIG.read_bytes());validate_config(config)
    plan=json.loads((OUTPUT/'plan.json').read_bytes())
    prior_audit=json.loads((OUTPUT/'static_audit.json').read_bytes())
    if sha(OUTPUT/'plan.json')!=prior_audit['plan_sha256']:raise ValueError('plan integrity')
    if plan['config_sha256']!=sha(CONFIG):raise ValueError('config binding')
    if plan['generator_sha256']!=sha(ROOT/'scripts/prepare_calibration_redesign.py'):raise ValueError('generator binding')
    for flag in ('execution_authorized','primary_collection_authorized','protected_access_authorized','coverage_complete'):
        if plan[flag] is not False:raise ValueError('unapproved proposal gate')
    for name,digest in plan['source_sha256'].items():
        path=ROOT/name
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT) or sha(path)!=digest:raise ValueError('source drift')
    old_path=ROOT/'reports/calibration_expansion_proposal_20260911_v2/plan.json'
    if sha(old_path)!=plan['source_plan_sha256']:raise ValueError('planning source drift')
    old=json.loads(old_path.read_bytes())
    base_rows={(r['map_id'],r['category'],int(r['view_group'][-1])):r for r in old['rows']
               if r['seed']==1 and r['view_group'].endswith(('-view0','-view3'))}
    assets={}
    for asset in plan['assets']:
        number=next((n for n in range(1,15) if asset['map_id']==f'r3geo_base_r{n:03}'),None)
        if number is None:raise ValueError('protected or unknown asset')
        scale=asset['lighting_scale'];source=ROOT/f'data/physical_worlds_readable_v1/base-r{number:03}/world.sdf'
        path=OUTPUT/'worlds'/f'base-r{number:03}'/f'light{round(scale*100):03}'/'world.sdf'
        if asset['world_path']!=str(path.relative_to(ROOT)) or sha(path)!=asset['world_sha256']:
            raise ValueError('derivative integrity')
        if sha(source)!=asset['source_world_sha256'] or path.read_bytes()!=lighting_variant(source.read_bytes(),scale):
            raise ValueError('change exceeds declared lighting transform')
        if (number,scale) in assets:raise ValueError('duplicate derivative')
        assets[number,scale]=path
    if set(assets)!=set(itertools.product(range(1,15),(1.,.9,.8))):raise ValueError('asset completeness')
    counts={}
    for panel,numbers,seeds in [('design_feasibility',[1,6],[7]),('primary_candidate',list(range(1,15)),[11,12])]:
        rows=plan['panels'][panel];check_panel(rows,panel,numbers,seeds,config)
        counts[panel]=len(rows)
        for row in rows:
            number=int(row['map_id'][-3:]);world=ROOT/f'data/physical_worlds_readable_v1/base-r{number:03}'
            old_row=base_rows[row['map_id'],row['category'],row['source_view_index']]
            if row['entity_id']!=old_row['entity_id'] or row['world_directory']!=str(world.relative_to(ROOT)):
                raise ValueError('stable target/world identity')
            scene=yaml.safe_load((world/'landmark_scene.yaml').read_bytes())
            entity=next(e for e in scene['entities'] if e['entity_id']==row['entity_id'])
            x,y=(old_row['capture_pose'][k] for k in ('x','y'))
            expected=dict(x=x,y=y,yaw=math.atan2(entity['pose']['y']-y,entity['pose']['x']-x)+row['yaw_offset_rad'])
            if row['capture_pose']!=expected:raise ValueError('pose assignment changed')
            validate_capture_pose(world,**expected)
            if row['derivative_world_path']!=str(assets[number,row['lighting_scale']].relative_to(ROOT)):
                raise ValueError('wrong lighting assignment')
            if row['camera_profile_sha256']!=old_row['camera_profile_sha256'] or sha(ROOT/row['camera_profile'])!=old_row['camera_profile_sha256']:
                raise ValueError('camera profile drift')
    return dict(schema_version='research3-calibration-redesign-static-verification/v1',passed=True,
        plan_sha256=sha(OUTPUT/'plan.json'),source_sha256=sha(__file__),assets_verified=len(assets),
        assignments_verified=counts,pose_checks=sum(counts.values()),geometry_and_materials_unchanged=True,
        execution_authorized=False,coverage_complete=False,validation_outcomes_or_labels_read=False)


if __name__=='__main__':
    result=verify();write(OUTPUT/'independent_verification.json',result);print(json.dumps(result))
