"""Exercise capture callback logic without importing or launching ROS."""
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace


def capture_class():
    tree = ast.parse((Path(__file__).parents[1] /
                      'scripts/physical_perception_capture.py').read_text())
    node = next(item for item in tree.body if isinstance(item, ast.ClassDef))
    node.bases = []
    def save_once(path, value):
        with path.open('x') as stream:
            json.dump(value, stream)
    namespace = {'message_to_ordereddict': lambda message: vars(message),
                 'hashlib': hashlib, '_json_once': save_once}
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<capture>', 'exec'), namespace)
    return namespace['PhysicalPerceptionCapture']


def recorder(tmp_path):
    obj = capture_class().__new__(capture_class())
    obj.output = tmp_path
    obj.finished = False
    obj.max_frames = 5
    obj.frames = []
    obj.info = SimpleNamespace(k=[1] * 9)
    obj.last_stamp = None
    obj.interval_ns = 100
    obj.tolerance_ns = 3
    obj.rgb, obj.depth = {}, {}
    obj.pending_observations = {}
    obj.observation_triggered = True
    obj.missed_observation_frames = 0
    obj.observation_messages_received = 0
    obj.capture_categories = frozenset()
    obj.observation_index = {}
    obj.max_observations_per_frame = 64
    obj.observation_overflow = 0
    obj.observation_conflicts = 0
    obj.counts = {}
    return obj


def image():
    return SimpleNamespace(data=b'abc', width=1, height=1, step=3,
                           encoding='rgb8', is_bigendian=False,
                           header=SimpleNamespace(frame_id=''))


def test_no_observation_does_not_consume_early_frames(tmp_path):
    obj = recorder(tmp_path)
    obj.rgb[10] = image()
    obj.depth[10] = image()
    obj._pair()
    assert obj.frames == []
    assert 10 in obj.rgb


def test_exact_timestamp_not_nearest_and_late_rgb_arrival(tmp_path):
    obj = recorder(tmp_path)
    obj.rgb[10], obj.depth[10] = image(), image()
    obj._observation(SimpleNamespace(observed_at_ns=11, observation_id='obs'))
    assert obj.frames == []
    obj.rgb[11] = image()
    obj._pair()
    assert len(obj.frames) == 1
    assert obj.frames[0]['rgb_stamp_ns'] == 11
    assert obj.frames[0]['depth_stamp_ns'] == 10
    assert obj.frames[0]['trigger_observations'][0]['observation_id'] == 'obs'
    assert obj.frames[0]['transform_error'] is not None


def test_pending_buffer_bounded_and_counts_unmatched(tmp_path):
    obj = recorder(tmp_path)
    for stamp in range(1, 41):
        obj._observation(SimpleNamespace(observed_at_ns=stamp))
    assert len(obj.pending_observations) == 32
    assert obj.missed_observation_frames == 8


def test_depth_sync_tolerance_is_enforced(tmp_path):
    obj = recorder(tmp_path)
    obj.rgb[100], obj.depth[90] = image(), image()
    obj._observation(SimpleNamespace(observed_at_ns=100))
    assert obj.frames == []


def test_sampling_interval_does_not_relabel_repeated_messages(tmp_path):
    obj = recorder(tmp_path)
    obj.last_stamp = 100
    obj._observation(SimpleNamespace(observed_at_ns=110))
    assert obj.pending_observations == {}


def test_same_frame_batch_survives_budget_and_preserves_immutable_frame(tmp_path):
    obj = recorder(tmp_path)
    obj.max_frames = 1
    obj.rgb[100], obj.depth[100] = image(), image()
    obj._observation(SimpleNamespace(observed_at_ns=100, observation_id='chair', category='chair'))
    before = (tmp_path / 'frame-000.json').read_bytes()
    obj._observation(SimpleNamespace(observed_at_ns=100, observation_id='door', category='doorway'))
    obj.finish()
    assert (tmp_path / 'frame-000.json').read_bytes() == before
    index = json.loads((tmp_path / 'observation_index.json').read_text())
    assert {row['observation_id'] for row in index['frames'][0]['observations']} == {'chair', 'door'}
    assert index['frames'][0]['frame_sha256'] == hashlib.sha256(before).hexdigest()
    summary = json.loads((tmp_path / 'summary.json').read_text())
    assert summary['observation_index']['sha256'] == hashlib.sha256(
        (tmp_path / 'observation_index.json').read_bytes()).hexdigest()
    saved = (tmp_path / 'observation_index.json').read_bytes()
    obj._observation(SimpleNamespace(observed_at_ns=100, observation_id='after-finish'))
    obj.finish()
    assert (tmp_path / 'observation_index.json').read_bytes() == saved


def test_category_filter_waits_for_target_and_retains_other_sameframe_objects(tmp_path):
    obj = recorder(tmp_path)
    obj.capture_categories = frozenset({'doorway'})
    obj.rgb[100], obj.depth[100] = image(), image()
    obj._observation(SimpleNamespace(observed_at_ns=100, observation_id='chair', category='chair'))
    assert not obj.frames
    obj._observation(SimpleNamespace(observed_at_ns=100, observation_id='door', category='doorway'))
    assert len(obj.frames) == 1
    obj._observation(SimpleNamespace(observed_at_ns=100, observation_id='entrance', category='office_entrance'))
    assert len(obj.observation_index[100]['observations']) == 3
    obj.finish()
    assert json.loads((tmp_path / 'summary.json').read_text())['capture_categories'] == ['doorway']


def test_late_previous_frame_duplicate_conflict_and_overflow(tmp_path):
    obj = recorder(tmp_path)
    obj.max_observations_per_frame = 2
    first = SimpleNamespace(observed_at_ns=100, observation_id='chair', category='chair')
    obj.rgb[100], obj.depth[100] = image(), image()
    obj._observation(first)
    obj.rgb[200], obj.depth[200] = image(), image()
    obj._observation(SimpleNamespace(observed_at_ns=200, observation_id='new'))
    obj._observation(first)
    obj._observation(SimpleNamespace(observed_at_ns=100, observation_id='chair', category='doorway'))
    assert obj.observation_index[100]['conflicting_observation_ids'] == ['chair']
    obj._observation(SimpleNamespace(observed_at_ns=100, observation_id='door'))
    obj._observation(SimpleNamespace(observed_at_ns=100, observation_id='overflow'))
    assert len(obj.observation_index[100]['observations']) == 2
    assert obj.observation_conflicts == 1
    assert obj.observation_overflow == 1


def test_full_budget_does_not_accept_a_new_timestamp(tmp_path):
    obj = recorder(tmp_path)
    obj.max_frames = 1
    obj.rgb[100], obj.depth[100] = image(), image()
    obj._observation(SimpleNamespace(observed_at_ns=100, observation_id='one'))
    obj._observation(SimpleNamespace(observed_at_ns=101, observation_id='different'))
    assert list(obj.observation_index) == [100]
    assert obj.pending_observations == {}


def test_independent_capture_needs_no_detector_and_respects_interval(tmp_path):
    obj = recorder(tmp_path)
    obj.observation_triggered = False
    obj.rgb[100], obj.depth[100] = image(), image()
    obj._pair()
    assert len(obj.frames) == 1
    assert obj.frames[0]['trigger_observations'] == []
    obj.rgb[150], obj.depth[150] = image(), image()
    obj._pair()
    assert len(obj.frames) == 1
    obj.rgb[200], obj.depth[200] = image(), image()
    obj._pair()
    assert len(obj.frames) == 2


def test_independent_capture_stops_at_requested_budget(tmp_path):
    obj = recorder(tmp_path)
    obj.observation_triggered = False
    obj.max_frames = 1
    obj.rgb[100], obj.depth[100] = image(), image()
    obj._pair()
    obj.rgb[200], obj.depth[200] = image(), image()
    obj._pair()
    assert obj.done and len(obj.frames) == 1
