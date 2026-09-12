"""Actual candidate methods exercised without ROS or a simulator."""
import ast
import hashlib
import json
import re
import threading
from pathlib import Path
from types import SimpleNamespace
from test_observation_capture import capture_class, recorder, image
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from expansion_sampling import first_synchronized_pair


def candidate(tmp_path):
    tree=ast.parse((Path(__file__).parents[1]/'scripts/physical_expansion_capture_candidate.py').read_text())
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef))
    def save(path,value):
        with path.open('x') as stream:json.dump(value,stream)
    namespace={'base':SimpleNamespace(PhysicalPerceptionCapture=capture_class(),
                _json_once=save,message_to_ordereddict=lambda m:vars(m)),
               'hashlib':hashlib,'first_synchronized_pair':first_synchronized_pair,
               're':re,'threading':threading}
    exec(compile(ast.Module(body=[cls],type_ignores=[]),'<expansion-candidate>','exec'),namespace)
    obj=recorder(tmp_path);obj.__class__=namespace['ExpansionCaptureCandidate']
    obj.armed=False;obj.max_frames=1;obj.armed_at_ns=0;obj._capture_lock=threading.RLock()
    return obj


def test_unarmed_does_not_capture(tmp_path):
    obj=candidate(tmp_path);obj.rgb[10]=image();obj.depth[10]=image();obj._pair()
    assert not obj.frames


def test_no_detection_still_captures_earliest_frame(tmp_path):
    obj=candidate(tmp_path);obj.armed=True
    obj.rgb={20:image(),10:image()};obj.depth={20:image(),10:image()};obj._pair()
    assert obj.frames[0]['rgb_stamp_ns']==10
    assert obj.frames[0]['observation_triggered'] is False
    assert obj.observation_index[10]['observations']==[]


def test_late_exact_frame_emission_retained(tmp_path):
    obj=candidate(tmp_path);obj.armed=True;obj.rgb[10]=image();obj.depth[10]=image();obj._pair()
    obj._observation(SimpleNamespace(observed_at_ns=10,observation_id='fixture'))
    assert obj.observation_index[10]['observations'][0]['observation_id']=='fixture'
    assert len(obj.frames)==1


def test_arm_requires_readiness_and_positive_clock(tmp_path):
    import pytest
    obj=candidate(tmp_path)
    with pytest.raises(ValueError,match='readiness'):obj.arm({})
    obj.get_clock=lambda:SimpleNamespace(now=lambda:SimpleNamespace(nanoseconds=100))
    evidence={k:True for k in ('localization_converged','provider_ready','transforms_ready','isolated_domain_verified')}
    evidence['source_snapshot_sha256']='a'*64
    obj.rgb[10]=image();obj.depth[10]=image()
    obj.arm(evidence)
    assert not obj.rgb and not obj.depth and obj.armed_at_ns==100
    with pytest.raises(ValueError,match='exactly once'):obj.arm(evidence)


def test_delayed_prearm_frames_and_observations_excluded(tmp_path):
    obj=candidate(tmp_path);obj.armed=True;obj.armed_at_ns=100
    obj.rgb={90:image(),110:image()};obj.depth={90:image(),110:image()}
    obj._observation(SimpleNamespace(observed_at_ns=90,observation_id='stale'))
    assert not obj.pending_observations
    obj._pair()
    assert obj.frames[0]['rgb_stamp_ns']==110
