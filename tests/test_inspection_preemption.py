"""Exercise production action callbacks without ROS, motion, or forced policy output."""
import ast
from copy import deepcopy
import math
from pathlib import Path
from types import MethodType, SimpleNamespace as NS

import pytest


class Future:
    def __init__(self):
        self.callbacks = []
        self.value = None

    def result(self):
        return self.value

    def add_done_callback(self, callback):
        self.callbacks.append(callback)

    def finish(self, value):
        self.value = value
        for callback in self.callbacks:
            callback(self)


def fixture():
    path = Path(__file__).parents[1] / 'ros_ws/src/language_nav_runtime/language_nav_runtime/nav2_adapter.py'
    tree = ast.parse(path.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Nav2RouteAdapter')
    wanted = {'on_decision', '_nav_goal_response', '_nav_result'}
    namespace = {'LanguageNavDecision': NS, 'deepcopy': deepcopy, 'math': math,
                 'NavigateToPose': NS(Goal=lambda: NS()),
                 'GoalStatus': NS(STATUS_SUCCEEDED=4, STATUS_CANCELED=5, STATUS_UNKNOWN=0, STATUS_ABORTED=6)}
    exec(compile(ast.Module(body=[n for n in cls.body if isinstance(n, ast.FunctionDef)
                                 and n.name in wanted], type_ignores=[]), str(path), 'exec'), namespace)
    sent, outcomes = [], []

    def send(goal):
        future = Future()
        sent.append((goal, future))
        return future

    node = NS(active_instructions=set(), active_actions={}, active_goal_handles={},
              pending_inspection_preemptions={}, cancel_reasons={}, inspection_completed_ns={},
              completed_instructions=set(), executed_decisions=set(), planned_distance={'r': 8},
              inspection_poses={'r': (3, 0, 0)}, physical_world=False,
              approved_paths={'r': ((0, 0), (3, 0), (8, 0))},
              execution_started_ns={}, execution_trace=[],
              nav_client=NS(wait_for_server=lambda **kwargs: True, send_goal_async=send),
              get_clock=lambda: NS(now=lambda: NS(nanoseconds=10_000_000_000)),
              get_logger=lambda: NS(error=lambda text: None),
              _goal_pose=lambda route: NS(pose=NS(position=NS(x=8, y=0), orientation=NS(z=0, w=1))))

    def publish(decision, succeeded, infrastructure, reason):
        outcomes.append((decision, succeeded, infrastructure, reason))
        node.completed_instructions.add(decision.instruction_id)
        node.active_instructions.discard(decision.instruction_id)
        node.active_actions.pop(decision.instruction_id, None)
        node.active_goal_handles.pop(decision.instruction_id, None)
        node.pending_inspection_preemptions.pop(decision.instruction_id, None)

    node._publish_execution = publish
    for name in wanted:
        setattr(node, name, MethodType(namespace[name], node))
    return node, sent, outcomes


def message(action, decision_id=None, guard=True):
    return NS(schema_version='language-nav-decision/v1', action=action, instruction_id='i',
              decision_id=decision_id or action, route_id='r', guard_passed=guard,
              reason='policy evidence', decided_at_ns=10_000_000_000, candidates_json='[]')


def accepted(sent):
    result, cancellations = Future(), []
    handle = NS(accepted=True, cancel_goal_async=lambda: cancellations.append(True),
                get_result_async=lambda: result)
    sent[0][1].finish(handle)
    return result, cancellations


def complete(result, status=5):
    result.finish(NS(status=status, result=NS(error_code=0, error_msg='')))


def test_late_inspect_waits_for_canceled_commit_before_second_goal():
    node, sent, outcomes = fixture()
    node.on_decision(message('commit'))
    result, cancellations = accepted(sent)
    node.on_decision(message('inspect'))
    node.on_decision(message('inspect', 'repeat'))
    assert len(cancellations) == 1 and len(sent) == 1
    assert node.active_actions['i'] == 'commit' and not outcomes
    complete(result)
    assert len(sent) == 2 and node.active_actions['i'] == 'inspect'
    assert sent[1][0].pose.pose.position.x == 3
    assert not outcomes and not node.pending_inspection_preemptions


def test_inspection_cancel_request_survives_pending_goal_acceptance():
    node, sent, outcomes = fixture()
    node.on_decision(message('commit'))
    node.on_decision(message('inspect'))
    assert len(sent) == 1
    result, cancellations = accepted(sent)
    assert len(cancellations) == 1
    complete(result)
    assert len(sent) == 2 and not outcomes


@pytest.mark.parametrize('accepted_first', [False, True])
def test_stop_overrides_pending_inspection_even_with_empty_reason(accepted_first):
    node, sent, outcomes = fixture()
    node.on_decision(message('commit'))
    if accepted_first:
        result, cancellations = accepted(sent)
    node.on_decision(message('inspect'))
    stop = message('stop_and_abstain')
    stop.reason = ''
    node.on_decision(stop)
    assert not node.pending_inspection_preemptions
    if not accepted_first:
        result, cancellations = accepted(sent)
    complete(result, status=4)  # success/cancel race must not restore success after stop
    assert cancellations and len(sent) == 1
    assert len(outcomes) == 1 and outcomes[0][1] is False
    assert 'monitor-driven abstention' in outcomes[0][3]


@pytest.mark.parametrize('status', [0, 4, 6])
def test_unconfirmed_cancellation_never_dispatches_inspection(status):
    node, sent, outcomes = fixture()
    node.on_decision(message('commit'))
    result, _ = accepted(sent)
    node.on_decision(message('inspect'))
    complete(result, status)
    assert len(sent) == 1 and len(outcomes) == 1
    assert outcomes[0][1] is False and 'not confirmed' in outcomes[0][3]


def test_route_is_revalidated_after_cancellation():
    node, sent, outcomes = fixture()
    node.on_decision(message('commit'))
    result, _ = accepted(sent)
    node.on_decision(message('inspect'))
    node.planned_distance.clear()
    complete(result)
    assert len(sent) == 1 and 'dispatch validation' in outcomes[0][3]


def test_unguarded_inspect_does_not_preempt_and_noncommit_cannot_be_preempted():
    node, sent, outcomes = fixture()
    node.on_decision(message('commit'))
    _, cancellations = accepted(sent)
    node.on_decision(message('inspect', guard=False))
    assert not cancellations and not node.pending_inspection_preemptions
    node.active_actions['i'] = 'inspect'
    node.on_decision(message('inspect'))
    assert not cancellations and len(sent) == 1 and not outcomes


def test_failed_eligibility_publication_revokes_cached_execution_and_inspection():
    path = Path(__file__).parents[1] / 'ros_ws/src/language_nav_runtime/language_nav_runtime/nav2_adapter.py'
    cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef)
               and n.name == 'Nav2RouteAdapter')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_publish_eligibility')
    namespace = {'RouteEligibility': NS}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
    publications = []
    node = NS(planned_distance={'r': 8, 'other': 4}, inspection_poses={'r': (3, 0, 0), 'other': (1, 0, 0)},
              approved_paths={'r': ((0, 0), (3, 0), (8, 0)), 'other': ((0, 0), (1, 0), (4, 0))},
              get_clock=lambda: NS(now=lambda: NS(nanoseconds=10)),
              eligibility_pub=NS(publish=lambda output: publications.append(output)))
    namespace['_publish_eligibility'](node, NS(route_id='r'), False, 8, 1, 'path rejected')
    assert 'r' not in node.planned_distance
    assert 'r' not in node.inspection_poses
    assert 'r' not in node.approved_paths
    assert 'other' in node.approved_paths
    assert node.planned_distance['other'] == 4
    assert not publications[0].eligible
