import ast
from pathlib import Path
from threading import RLock
from types import SimpleNamespace as NS


def test_diagnostic_pairing_is_bounded_and_does_not_guess_stale_truth():
    tree = ast.parse((Path(__file__).parents[1] / 'scripts/run_live_episode.py').read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'TimestampedEpisodeMonitor')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_on_amcl')
    class Base:
        def _on_amcl(self, message):
            pass
    namespace = {'Base': Base}
    minimal = ast.ClassDef(name='Monitor', bases=[ast.Name(id='Base', ctx=ast.Load())],
                           keywords=[], body=[method], decorator_list=[])
    exec(compile(ast.fix_missing_locations(ast.Module(body=[minimal], type_ignores=[])), '<diagnostic>', 'exec'), namespace)
    node = namespace['Monitor']()
    node.capture_lock, node._lock = RLock(), RLock()
    node._active = True
    node.localization_diagnostics = []
    node._gt_stamps, node._gt_hist = [1.], [(2., 3.)]
    node._stamp_s = lambda message: message.header.stamp.sec
    node._yaw = lambda orientation: 0.
    message = NS(header=NS(stamp=NS(sec=1, nanosec=0)), pose=NS(pose=NS(position=NS(x=2.2, y=3.), orientation=NS())))
    node._on_amcl(message)
    assert node.localization_diagnostics[-1]['ground_truth_xy'] == [2., 3.]
    message.header.stamp.sec = 2
    node._on_amcl(message)
    assert node.localization_diagnostics[-1]['ground_truth_xy'] is None
    node.localization_diagnostics = [{}] * 2048
    node._on_amcl(message)
    assert len(node.localization_diagnostics) == 2048
