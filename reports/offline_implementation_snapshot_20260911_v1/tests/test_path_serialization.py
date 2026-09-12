"""Exercise production scheduling methods with action-client doubles, no ROS."""
import ast
from pathlib import Path
from types import SimpleNamespace as NS


def methods():
    source = Path(__file__).parents[1] / 'ros_ws/src/language_nav_runtime/language_nav_runtime/nav2_adapter.py'
    tree = ast.parse(source.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Nav2RouteAdapter')
    wanted = {'on_proposal', '_start_next_path'}
    namespace = {'SemanticRouteProposal': NS, 'ComputePathToPose': NS(Goal=NS)}
    module = ast.Module(body=[n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in wanted], type_ignores=[])
    exec(compile(module, str(source), 'exec'), namespace)
    return namespace


def test_four_proposals_never_overlap_path_goals():
    functions = methods()
    sent = []
    def send(goal):
        sent.append(goal.goal)
        return NS(add_done_callback=lambda callback: None)
    node = NS(routes={str(i): None for i in range(4)}, proposals={}, planning=set(),
              path_queue=[], active_path_route=None,
              path_client=NS(wait_for_server=lambda **kw: True, send_goal_async=send),
              _goal_pose=lambda route: route, _path_goal_response=lambda *args: None)
    for route in node.routes:
        functions['on_proposal'](node, NS(schema_version='semantic-route-proposal/v1', route_id=route))
    for index in range(4):
        functions['_start_next_path'](node)
        functions['_start_next_path'](node)
        assert len(sent) == index + 1
        assert node.active_path_route == str(index)
        node.active_path_route = None  # completion callback releases the slot
    assert sent == ['0', '1', '2', '3']
