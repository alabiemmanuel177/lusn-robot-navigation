from dataclasses import asdict, replace
import importlib.util
import json
import math
from pathlib import Path

import pytest

from language_nav.contracts import Pose2D, RouteEligibility, SemanticObservationContract
from language_nav.grounding import SemanticRouteProposal, build_semantic_route_candidates
from language_nav.live import inspection_waypoint, observed_inspection_waypoint

NOW=10_000_000_000
PATH=((.6,0),(.8,0),(1.1,0),(1.4,0),(2.2,0),(4.68,-.16),(6.,-.16),(7.5,-2.))


def candidate():
    observation=SemanticObservationContract('semantic-observation/v1','real-frame-chair',
        'chair-entity','chair',{'color':'blue'},Pose2D(2.2,.8),(.04,0.,0.,.04),.8,
        NOW-100_000_000,'map','rgbd-provider',7,'chair-region')
    proposal=SemanticRouteProposal('r','chair-region','terminal-region',8,.1,.5,True,2,'right')
    nav=RouteEligibility('r',True,True,8,.1,'path')
    return build_semantic_route_candidates((observation,),(proposal,),(nav,))[0],observation,proposal,nav


def test_observed_anchor_selects_short_first_path_view_instead_of_far_midpoint():
    value,*_=candidate()
    result=observed_inspection_waypoint(PATH,json.dumps([asdict(value)]),'r',NOW)
    assert result[:2]==(1.1,0)
    assert result[2]==pytest.approx(math.atan2(.8,1.1))
    assert result[:2] in PATH
    assert inspection_waypoint(PATH)[0]>2.2


@pytest.mark.parametrize('changes',[
    {'anchor_x':None},{'anchor_y':float('nan')},{'anchor_x':True},
    {'anchor_x':100.},{'anchor_observed_at_ns':NOW-3_000_000_001},
    {'anchor_observed_at_ns':NOW+1},{'anchor_observed_at_ns':0},
    {'anchor_observation_sequence':-1},{'anchor_observation_sequence':True},
    {'anchor_observation_id':''},{'anchor_observation_source':' '},
    {'anchor_entity_id':'unobserved:chair-region:landmark'},
])
def test_missing_invalid_or_stale_anchor_fails_closed(changes):
    value,*_=candidate()
    row={**asdict(value),**changes}
    assert observed_inspection_waypoint(PATH,json.dumps([row]),'r',NOW) is None


def test_only_actual_map_frame_observation_populates_coordinates():
    value,observation,proposal,nav=candidate()
    assert (value.anchor_x,value.anchor_y)==(observation.pose.x,observation.pose.y)
    for observations in ((),(replace(observation,frame_id='camera'),)):
        candidate_without_pose=build_semantic_route_candidates(observations,(proposal,),(nav,))[0]
        assert candidate_without_pose.anchor_x is None
        assert candidate_without_pose.anchor_y is None
        assert observed_inspection_waypoint(PATH,json.dumps([asdict(candidate_without_pose)]),'r',NOW) is None


def test_duplicate_or_malformed_candidates_and_invalid_paths_abstain():
    value,*_=candidate()
    row=asdict(value)
    for encoded in ('bad json','{}',json.dumps([row,row]),json.dumps([None])):
        assert observed_inspection_waypoint(PATH,encoded,'r',NOW) is None
    for path in ((),((0,0),(1,0)),((0,0),(.1,0),(.2,0)),((0,0),(float('nan'),0),(2,0))):
        assert observed_inspection_waypoint(path,json.dumps([row]),'r',NOW) is None


def test_physical_adapter_dispatch_uses_observed_view_and_never_legacy_fallback():
    path=Path(__file__).with_name('test_inspection_preemption.py')
    spec=importlib.util.spec_from_file_location('inspection_fixture',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    value,*_=candidate()
    for fresh in (True,False):
        node,sent,outcomes=module.fixture()
        node.physical_world=True
        node.approved_paths['r']=PATH
        node.on_decision.__func__.__globals__['observed_inspection_waypoint']=observed_inspection_waypoint
        message=module.message('inspect')
        message.candidates_json=json.dumps([asdict(value)]) if fresh else '[]'
        node.on_decision(message)
        if fresh:
            assert len(sent)==1
            position=sent[0][0].pose.pose.position
            assert (position.x,position.y)==(1.1,0)
            assert sent[0][0].pose.pose.orientation.z==pytest.approx(math.sin(math.atan2(.8,1.1)/2))
        else:
            assert not sent
            assert 'no distinct inspection viewpoint' in outcomes[0][3]
