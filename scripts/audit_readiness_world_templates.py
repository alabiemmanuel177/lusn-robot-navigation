"""Validate the authorized prior against ten development worlds, never outcomes."""
import math
import xml.etree.ElementTree as ET
import yaml
from integrate_object_depth_candidate import ROOT,sha,write


def main():
    rows=[];pins={}
    for index in range(1,11):
        root=ROOT/f'data/physical_worlds_readable_v1/base-r{index:03}'
        scene_path=root/'landmark_scene.yaml';world_path=root/'world.sdf'
        scene=yaml.safe_load(scene_path.read_bytes())
        if scene['partition']!='development':raise ValueError('development only')
        world=ET.fromstring(world_path.read_bytes()).find('world');checked=[]
        for entity in scene['entities']:
            if entity['category'] not in ('laboratory_entrance','office_entrance'):continue
            ref=entity['pose'];model=world.find(f"model[@name='readable_{entity['entity_id']}_corridor']")
            if model is None:raise ValueError('readable template absent')
            pose=list(map(float,model.find('pose').text.split()));side=1 if ref['y']>0 else -1
            if not math.isclose(ref['x']-pose[0],.53,abs_tol=1e-8) or not math.isclose(ref['y']-pose[1],side*.40,abs_tol=1e-8):
                raise ValueError('authored reference prior changed')
            checked.append(entity['entity_id'])
        if len(checked)!=4:raise ValueError('four entrance template instances required')
        rows.append(dict(map_id=scene['map_id'],verified_entrance_instances=checked))
        pins[str(scene_path)]=sha(scene_path);pins[str(world_path)]=sha(world_path)
    pins[str(ROOT/'scripts/audit_readiness_world_templates.py')]=sha(__file__)
    write(ROOT/'reports/four_class_world_template_audit_20260924_v1.json',dict(rows=rows,input_sha256=pins,
        all_ten_development_worlds_match=True,scope='construction-prior validation only; no visual accuracy or instance label',
        protected_or_validation_data_used=False))
    print('All 40 entrance templates match the source-derived reference conversion.')


if __name__=='__main__':main()
