"""Static marker projection diagnostic; not a detector/visibility/label prediction."""
from collections import Counter
import json
import xml.etree.ElementTree as ET
from distance_lighting_pilot import ROOT,OUTPUT,rows
from expansion_camera_model import rendering_camera
from prepare_expansion_diagnostics_v2 import marker_name,silhouette_mask,intrinsics
from run_stage1_feasibility import sha,write


def main():
    records=[];seen=set();worlds={}
    for row in rows():
        key=(row['map_id'],row['category'],row['distance_fraction'],row['yaw_offset_rad'])
        if key in seen:continue
        seen.add(key);folder=ROOT/row['world_directory']
        if folder not in worlds:worlds[folder]=ET.fromstring((folder/'world.sdf').read_bytes()).find('world')
        marker=worlds[folder].find(f"model[@name='{marker_name(row)}']")
        if marker is None:raise ValueError('missing declared marker geometry')
        centre,rotation=rendering_camera(row['capture_pose'])
        mask=silhouette_mask([marker],centre,rotation,intrinsics());pixels=int(mask.sum())
        records.append(dict(map_id=row['map_id'],category=row['category'],distance_fraction=row['distance_fraction'],
            yaw_offset_rad=row['yaw_offset_rad'],projected_marker_hull_pixels=pixels,
            projected_size_band='below_component_floor' if pixels<18 else 'unsaturated_range' if pixels<72 else 'saturated_range',
            source_world_sha256=sha(folder/'world.sdf'),capture_pose=row['capture_pose']))
    report=dict(schema_version='research3-static-marker-projection-diagnostic/v1',unique_poses=len(records),
        classes={c:dict(Counter(r['projected_size_band'] for r in records if r['category']==c)) for c in sorted({r['category'] for r in records})},
        plan_sha256=sha(OUTPUT/'plan.json'),rows=records,rendered_outcomes_used=False,human_labels_generated=False,
        limitations=['Convex marker-box projection ignores occlusion, shading, palette masks and connected components',
            'Chair seat proxy excludes other same-colour chair parts',
            'Pixel rasterization is approximate; projected area is not guaranteed emitted support',
            'Static analysis does not modify the fixed live schedule or justify imputed observations'])
    write(OUTPUT/'static_projection_diagnostic.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='rows'}))


if __name__=='__main__':main()
