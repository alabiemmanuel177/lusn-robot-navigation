"""Read-only regression evidence: frozen provider is not an earliest-frame queue."""
import ast
from pathlib import Path
import threading
from types import SimpleNamespace


def test_frozen_provider_can_skip_earliest_buffered_frame():
    source = Path('/home/eao/risk-calibrated-nav/extensions/research3_landmark_bridge/research3_landmark_bridge/node.py')
    tree = ast.parse(source.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'LandmarkObservationNode')
    method = next(n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == '_try_pair')
    namespace = {}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), 'exec'), namespace)
    processed = []
    provider = SimpleNamespace(camera_info=object(), rgb={10: 'early-rgb', 20: 'late-rgb'},
        depth={10: 'early-depth', 20: 'late-depth'}, processing_lock=threading.Lock(),
        sync_tolerance_ns=0, _process=lambda rgb, depth: processed.append((rgb, depth)))
    namespace['_try_pair'](provider)
    assert processed == [('late-rgb', 'late-depth')]
    assert 10 in provider.rgb
