"""Production completion/deadline callback regression without ROS or motion."""
import ast
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace as NS


def callbacks():
    path = Path(__file__).parents[1] / 'ros_ws/src/language_nav_runtime/language_nav_runtime/nav2_adapter.py'
    tree = ast.parse(path.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Nav2RouteAdapter')
    wanted = {'_nav_result', '_check_inspection_timeout'}
    namespace = {'LanguageNavDecision': NS, 'deepcopy': deepcopy,
                 'GoalStatus': NS(STATUS_SUCCEEDED=4, STATUS_UNKNOWN=0, STATUS_ABORTED=6)}
    exec(compile(ast.Module(body=[n for n in cls.body if isinstance(n, ast.FunctionDef)
                                 and n.name in wanted], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace


def test_completed_inspection_without_new_observation_abstains_once():
    cb = callbacks()
    now, outcomes = [10_000_000_000], []
    decision = NS(action='inspect', instruction_id='i', route_id='r')
    node = NS(cancel_reasons={}, inspection_completed_ns={}, active_instructions={'i'},
              active_goal_handles={'i': object()}, pending_inspections={}, execution_trace=[],
              completed_instructions=set(), inspection_wait_timeout_ns=8_000_000_000,
              get_clock=lambda: NS(now=lambda: NS(nanoseconds=now[0])),
              _publish_execution=lambda *args: outcomes.append(args))
    cb['_nav_result'](node, decision, NS(result=lambda: NS(status=4, result=NS(error_code=0))))
    assert node.pending_inspections and not node.active_instructions
    now[0] += 7_999_999_999
    cb['_check_inspection_timeout'](node)
    assert not outcomes
    now[0] += 1
    cb['_check_inspection_timeout'](node)
    cb['_check_inspection_timeout'](node)
    assert len(outcomes) == 1
    stop, succeeded, infrastructure, reason = outcomes[0]
    assert stop.action == 'stop_and_abstain' and stop.route_id == ''
    assert not succeeded and not infrastructure and 'fresh anchor' in reason
    assert decision.action == 'inspect'  # original evidence remains unchanged


def test_resumed_or_completed_instruction_cannot_be_stopped_by_old_deadline():
    cb = callbacks()
    for field in ('active_instructions', 'completed_instructions'):
        node = NS(pending_inspections={'i': NS()}, completed_instructions=set(), active_instructions=set(),
                  get_clock=lambda: NS(now=lambda: NS(nanoseconds=100)))
        getattr(node, field).add('i')
        cb['_check_inspection_timeout'](node)
        assert not node.pending_inspections
