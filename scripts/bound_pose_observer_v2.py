"""Evaluation-only exact-time simulator pose journal; never feeds perception."""
import json
from pathlib import Path
import sys
import time
import numpy as np
from candidate_rendering_transform import rigid, correction
from candidate_pose_validation import compare_transforms
from expansion_camera_model import rotation_from_rpy
from integrate_object_depth_candidate import sha,write


def matrix(position, quaternion):
    x,y,z,w=quaternion
    norm=np.linalg.norm(quaternion)
    if not np.isfinite(norm) or abs(norm-1)>1e-5:raise ValueError('unit quaternion required')
    r=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
    return rigid(r,position)


def main(root):
    import rclpy
    from rclpy.node import Node
    from rclpy.parameter import Parameter
    from rclpy.time import Time
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import Image
    from geometry_msgs.msg import PoseStamped
    from tf2_ros import Buffer,TransformListener
    from rosidl_runtime_py.convert import message_to_ordereddict
    plan=json.loads((root/'plan.json').read_bytes())
    for path,digest in plan['input_sha256'].items():
        if sha(path)!=digest:raise ValueError('source changed')
    nominal=np.asarray(plan['nominal_mount']);rendered=np.asarray(plan['rendered_mount'])
    rclpy.init();node=Node('research3_evaluation_pose_only',parameter_overrides=[Parameter('use_sim_time',value=True)])
    buf=Buffer();listener=TransformListener(buf,node)
    truth={};rgb={};depth=set();selected=[];rows=[];complete=False
    journal=(root/'truth.jsonl').open('x')
    def stamp(msg):return msg.header.stamp.sec*10**9+msg.header.stamp.nanosec
    def ground(msg):
        s=stamp(msg);value=message_to_ordereddict(msg)
        truth[s]=value
        journal.write(json.dumps(value)+'\n');journal.flush()
        if len(truth)>3000:truth.pop(next(iter(truth)))
    def image(msg,is_depth=False):
        if complete or not (root/'episode/context_capture/request.json').exists():return
        s=stamp(msg)
        if is_depth:depth.add(s)
        else:rgb[s]=msg.header.frame_id
        if s in rgb and s in depth and s not in [v[0] for v in selected] and len(selected)<20:
            selected.append((s,rgb[s],time.monotonic()))
        if len(rgb)>200:rgb.pop(next(iter(rgb)))
        if len(depth)>200:depth.remove(min(depth))
    node.create_subscription(PoseStamped,'/ground_truth_pose',ground,100)
    node.create_subscription(Image,'/camera/image',image,qos_profile_sensor_data)
    node.create_subscription(Image,'/camera/depth_image',lambda msg:image(msg,True),qos_profile_sensor_data)
    def tick():
        nonlocal complete
        if complete:return
        while len(rows)<len(selected) and time.monotonic()-selected[len(rows)][2]>=2:
            s,frame,_=selected[len(rows)];row=dict(stamp_ns=s,camera_frame=frame,status='missing_exact_truth')
            if s in truth:
                raw=truth[s]['pose'];p=raw['position'];q=raw['orientation']
                gt=matrix([p[k] for k in ('x','y','z')],[q[k] for k in ('x','y','z','w')])@rendered
                row['truth']=truth[s];row['truth_camera_matrix']=gt.tolist()
                try:
                    tf=buf.lookup_transform('map',frame,Time(nanoseconds=s))
                    a=tf.transform.translation;b=tf.transform.rotation
                    est=matrix([a.x,a.y,a.z],[b.x,b.y,b.z,b.w])
                    corrected=correction(est,nominal,rendered)
                    row.update(status='compared',nominal_tf=message_to_ordereddict(tf),corrected_matrix=corrected.tolist(),
                        comparison=compare_transforms(corrected,gt,estimate_stamp_ns=s,truth_stamp_ns=s,
                            truth_source='simulator_world_pose',descriptions_bound=True))
                except Exception as exc:row.update(status='tf_unavailable',error=str(exc))
            rows.append(row)
        if len(rows)==20:
            write(root/'pose_results.json',dict(rows=rows,plan_sha256=sha(root/'plan.json'),
                compared=sum(r['status']=='compared' for r in rows),calibration_eligible=False))
            complete=True
    node.create_timer(.1,tick,clock=rclpy.clock.Clock(clock_type=rclpy.clock.ClockType.STEADY_TIME))
    try:rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:
        journal.close()
        if not complete:write(root/'pose_incomplete.json',dict(rows=rows,selected=len(selected),infrastructure_failure=True))
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()


if __name__=='__main__':main(Path(sys.argv[1]))
