"""Exercise actual wrapper methods with synthetic messages, without ROS."""
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
from expansion_sampling import classify_attempt


def wrapper(tmp_path, *, failure=False):
    source=Path(__file__).parents[1]/'scripts/physical_expansion_capture_candidate.py'
    tree=ast.parse(source.read_text())
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_frame_provider')
    cls=next(n for n in function.body if isinstance(n,ast.ClassDef))
    class Provider:
        def __init__(self):
            self.publisher=NS(publish=lambda m:None)
            self.tf_buffer=NS(can_transform=lambda *a:True)
            self.review_handle=None
            self.calls=[]
        def get_parameter(self,key):return NS(value='/r3_expansion_unused/'+key)
        def create_timer(self,*a):pass
        def _process(self,*messages):
            self.calls.append(messages)
            if failure:raise RuntimeError('synthetic processing exception')
    def write(path,value):
        with path.open('x') as stream:json.dump(value,stream)
    import time
    namespace=dict(LandmarkObservationNode=Provider,output=tmp_path,json=json,hashlib=hashlib,time=time,
        base=NS(Time=lambda **kw:kw,_json_once=write,message_to_ordereddict=vars),
        Image=lambda:NS(header=NS(stamp=NS(),frame_id='')),CameraInfo=lambda:NS(),
        set_message_fields=lambda obj,fields:obj.__dict__.update(fields))
    exec(compile(ast.Module(body=[cls],type_ignores=[]),'<wrapper>','exec'),namespace)
    folder=tmp_path/'perception_capture';folder.mkdir()
    frame=dict(rgb_stamp_ns=10,depth_stamp_ns=10,camera_info={'k':[1.]*9})
    for kind in ('rgb','depth'):
        raw=b'synthetic';name=f'frame-000-{kind}.bin';(folder/name).write_bytes(raw)
        frame[kind]=dict(file=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
                        width=1,height=1,step=9,encoding='synthetic',is_bigendian=0,frame_id='camera')
    write(folder/'frame-000.json',frame)
    return namespace['AuditedProvider']()


def test_zero_emission_completion_and_duplicate_poll(tmp_path):
    node=wrapper(tmp_path);node.process_retained();node.process_retained()
    assert len(node.calls)==1
    assert node.calls[0][0].data==b'synthetic'
    audit=json.loads((tmp_path/'provider_frame_completion.json').read_text())
    assert audit['status']=='completed' and audit['observations']==[]
    assert (tmp_path/'provider_frame_done.json').exists()


def test_exception_never_acknowledged_as_completed(tmp_path):
    node=wrapper(tmp_path,failure=True);node.process_retained()
    assert json.loads((tmp_path/'provider_frame_completion.json').read_text())['status']=='failed'


def test_corrupt_input_not_processed(tmp_path):
    node=wrapper(tmp_path);(tmp_path/'perception_capture/frame-000-rgb.bin').write_bytes(b'changed')
    node.process_retained()
    assert not node.calls
    assert json.loads((tmp_path/'provider_frame_completion.json').read_text())['status']=='failed'


@pytest.mark.parametrize('mutation,expected', [({},'nondetection'),({'status':'failed'},'infrastructure_failure'),
    ({'frame_stamp_ns':11},'infrastructure_failure'),({'frame_sha256':'wrong'},'infrastructure_failure'),
    ({'observations':[{'observation_id':'missing'}]},'infrastructure_failure')])
def test_completion_binding_and_missing_delivery(mutation,expected):
    audit=dict(status='completed',frame_stamp_ns=10,frame_sha256='a'*64,observations=[])
    audit.update(mutation)
    result=classify_attempt([],frame_stamp_ns=10,entity_id='fixture',category='chair',armed=True,
        frame_present=True,synchronization_valid=True,transform_valid=True,
        observation_window_complete=True,interrupted=False,processing_evidence=audit,frame_sha256='a'*64)
    assert result['status']==expected


def test_transform_wait_is_bounded_then_processing_proceeds(tmp_path, monkeypatch):
    node=wrapper(tmp_path);node.tf_buffer=NS(can_transform=lambda *a:False)
    clock=[0.0]
    import time as _time
    monkeypatch.setattr(_time,'monotonic',lambda:clock[0])
    node.process_retained()
    assert not node.calls and not (tmp_path/'provider_frame_started.json').exists()
    clock[0]=node.transform_wait_s+.1
    node.process_retained()
    assert len(node.calls)==1
    audit=json.loads((tmp_path/'provider_frame_started.json').read_text())
    assert audit['transform_available_before_processing'] is False and audit['transform_wait_s']>=node.transform_wait_s
