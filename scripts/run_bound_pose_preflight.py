"""Four fixed serial development views, source-bound simulator truth, no motion."""
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from integrate_object_depth_candidate import ROOT,sha,write
from candidate_rendering_transform import rigid
from expansion_camera_model import rotation_from_rpy

OUT=ROOT/'reports/independent_pose_live_20260924_v1'
R1=Path('/home/eao/risk-calibrated-nav')


def mounts(sdf,urdf):
    model=ET.fromstring(sdf).find('model')
    link=model.find("link[@name='camera_link']")
    def pose(element):
        if element is None:return np.eye(4)
        if element.attrib:raise ValueError('relative pose convention requires explicit support')
        x,y,z,r,p,yaw=map(float,element.text.split())
        return rigid(rotation_from_rpy(r,p,yaw),[x,y,z])
    rendered=pose(link.find('pose'))@pose(link.find("sensor[@name='rcn_rgbd']/pose"))
    rendered=rendered@rigid(np.array([[0,0,1],[-1,0,0],[0,-1,0]]),[0,0,0])
    joints={j.find('child').attrib['link']:j for j in ET.fromstring(urdf).findall('joint')}
    child='camera_depth_frame';chain=[]
    while child!='base_footprint':
        j=joints[child]
        if j.attrib['type']!='fixed':raise ValueError('fixed optical mount required')
        origin=j.find('origin');xyz=list(map(float,origin.attrib.get('xyz','0 0 0').split()))
        rpy=list(map(float,origin.attrib.get('rpy','0 0 0').split()))
        chain.append(rigid(rotation_from_rpy(*rpy),xyz));child=j.find('parent').attrib['link']
    nominal=np.eye(4)
    for t in reversed(chain):nominal=nominal@t
    return nominal,rendered


def main():
    from language_nav.live_resources import coexistence_headroom
    from language_nav.capture_view import validate_capture_pose
    from run_physical_episode import prepare,execute
    import run_live_episode
    os.nice(19)
    source=ROOT/'reports/grounding_candidate_20260923_v3/plan.json'
    slots=json.loads(source.read_bytes())['slots'];selected={}
    for slot in slots:
        if slot['status']!='ready':continue
        path=(ROOT/slot['frame']).parent.parent/'request.json'
        old=json.loads(path.read_bytes());category=old['capture_target_categories'][0]
        if old['partition']!='development' or old['protected_test_routes_used']:raise ValueError('scope')
        selected.setdefault(category,(path,old))
    if len(selected)!=4:raise ValueError('four classes required')
    OUT.mkdir(exist_ok=False)
    write(OUT/'schedule.json',dict(selection='first intact fixed-panel view per acquisition class; no retries',
        source_plan_sha256=sha(source),views=[dict(category=c,source_request=str(p),sha256=sha(p)) for c,(p,_) in selected.items()],
        resource_sample=coexistence_headroom(),calibration_eligible=False))
    robot=R1/'src/robot_description/urdf/rcn_waffle.sdf.xacro'
    bridge=R1/'src/simulation_worlds/config/bridge.yaml'
    urdf=Path('/opt/ros/jazzy/share/nav2_minimal_tb3_sim/urdf/turtlebot3_waffle.urdf')
    expanded=subprocess.run(['xacro',str(robot),'namespace:='],capture_output=True,text=True,check=True).stdout
    tree=ET.fromstring(expanded);fovs=tree.findall('.//sensor/camera/horizontal_fov')
    if len(fovs)!=2:raise ValueError('two matched cameras required')
    for fov in fovs:fov.text='2.0'
    expanded=ET.tostring(tree,encoding='unicode');nominal,rendered=mounts(expanded,urdf.read_text())
    original_stack=run_live_episode.Stack
    for i,(category,(source_request,old)) in enumerate(selected.items()):
        root=OUT/f'view-{i:02}-{category}';root.mkdir();episode=root/'episode';episode.mkdir()
        for name,data in [('robot.sdf',expanded.encode()),('robot.urdf',urdf.read_bytes()),('bridge.yaml',bridge.read_bytes())]:
            with (root/name).open('xb') as f:f.write(data)
        pose=validate_capture_pose(old['world_directory'],**old['capture_pose'])
        request,variant,catalog=prepare(old['world_directory'],old['variant_id'],f'r3-pose-20260924-{i}',97,timeout=90,simulation_seed=29)
        request.update(capture_only=True,capture_perception=True,capture_review=False,capture_frame_budget=20,
            capture_pose=pose,camera_horizontal_fov=2.0,allow_coexistence_trial=True)
        world=Path(old['world_directory'])/'world.sdf'
        inputs=[robot,bridge,urdf,world,source_request,Path(__file__),ROOT/'scripts/bound_pose_observer.py',
            ROOT/'scripts/bound_pose_sim.launch.py',ROOT/'scripts/candidate_pose_validation.py',ROOT/'scripts/candidate_rendering_transform.py',
            ROOT/'scripts/expansion_camera_model.py',ROOT/'scripts/run_physical_episode.py',ROOT/'scripts/run_live_episode.py']
        inputs.extend(root/name for name in ('robot.sdf','robot.urdf','bridge.yaml'))
        write(root/'plan.json',dict(partition='development',capture_pose=pose,seed=29,world=str(world),
            input_sha256={str(p):sha(p) for p in inputs},nominal_mount=nominal.tolist(),rendered_mount=rendered.tolist(),
            sampling='first 100 exact RGB/depth timestamp pairs after context recorder readiness; retain absent exact truth',
            truth_source='/ground_truth_pose; evaluator only',calibration_eligible=False))
        write(episode/'request.json',request)
        os.environ['R3_POSE_BOUND_RUN']=str(root)
        class BoundStack(original_stack):
            def launch(self,name,command):
                if name=='sim':
                    result=super().launch(name,['ros2','launch',str(ROOT/'scripts/bound_pose_sim.launch.py')])
                    super().launch('pose_observer',['python3',str(ROOT/'scripts/bound_pose_observer.py'),str(root)])
                    return result
                return super().launch(name,command)
        run_live_episode.Stack=BoundStack
        try:
            coexistence_headroom();result=execute(request,variant,catalog,episode,'B5')
            write(root/'execution.json',dict(result=result))
        except Exception as exc:write(root/'execution_failure.json',dict(error=repr(exc),infrastructure_failure=True))
        finally:run_live_episode.Stack=original_stack
        print('Pose view finished:',category,flush=True)


if __name__=='__main__':main()
