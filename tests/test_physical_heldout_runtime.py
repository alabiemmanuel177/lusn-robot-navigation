"""Synthetic held-out fixtures only; no actual protected catalogues are opened."""
import ast
import json
from pathlib import Path
import runpy

import pytest

from language_nav import physical_heldout_authorization as auth
from language_nav.benchmark.physical_catalog import load_physical_runtime_catalog, validate_physical_launch_inputs

ROOT = Path(__file__).parents[1]
RUNTIME = runpy.run_path(str(ROOT / 'scripts/run_physical_episode.py'))


def test_active_parser_belief_and_monitor_implementations_require_pins():
    assert {'ros_ws/src/language_interface/language_interface/node.py',
            'ros_ws/src/semantic_belief_map/semantic_belief_map/node.py',
            'ros_ws/src/language_nav_runtime/language_nav_runtime/monitor_bridge.py',
            'src/language_nav/parsing/rule_based.py','src/language_nav/belief/store.py',
            'src/language_nav/belief/update.py','src/language_nav/adapters/ros.py',
            'src/language_nav/models.py','src/language_nav/contracts.py',
            'src/language_nav/safety.py'} <= auth.SOURCE_FILES


def test_active_provider_control_measurement_and_config_inputs_require_pins():
    assert {'src/experiment_controller/experiment_controller/run_episode.py',
            'src/experiment_controller/experiment_controller/preflight.py',
            'src/episode_logger/episode_logger/monitor.py',
            'rcn/collisions.py','rcn/perception_metrics.py',
            'configs/nav2/nav2_common.yaml','configs/systems/s0.yaml'} <= auth.PROVIDER_FILES


@pytest.fixture
def synthetic(tmp_path):
    def save(name, data):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
        return {'path': name, 'sha256': auth.sha(path)}
    design = {'schema_version': 'research3-physical-experiment-design-draft/v2', 'status': 'frozen',
        'analysis_proposals': {'candidate_contrasts': ['B6_minus_B1'], 'primary_contrast': 'B6_minus_B1',
            'multiplicity_policy': 'synthetic-only', 'confirmatory_inference_method': 'synthetic-only'},
        'simulator_seed': {'confirmatory_seed_list': [1]}, 'replication': {'confirmatory_replications': 1},
        'power_inputs_requiring_freeze': {'repetitions_per_world': 1, 'target_effect': .1, 'target_power': .8,
            'alpha': .05, 'baseline_completion': .5, 'paired_discordance': .3, 'world_intracluster_correlation': .2}}
    design_ref = save('design.json', design)
    calibration_ref = save('calibration.json', {'schema_version': 'landmark-calibration/v1', 'partition': 'validation'})
    world = tmp_path / 'synthetic_world'
    world.mkdir()
    (world / 'world.sdf').write_text('<sdf><world name="synthetic"/></sdf>')
    (world / 'map.pgm').write_bytes(b'P2\n1 1\n255\n255\n')
    save('synthetic_world/map.yaml', {'image': 'map.pgm', 'resolution': .05, 'origin': [-1., -5., 0.],
        'negate': 0, 'occupied_thresh': .65, 'free_thresh': .196})
    map_id = 'r3geo_base_r015'
    routes = [{'route_id': f'{map_id}_{side}_{ordinal}', 'goal': {'x': ordinal + 1, 'y': 1, 'yaw': 0},
        'side': side, 'ordinal': ordinal, 'terminal_entity_id': f'{map_id}_{side}_{ordinal}_entrance'}
        for side in ('left', 'right') for ordinal in (1, 2)]
    save('synthetic_world/execution_catalog.json', {'schema_version': 'research3-physical-route-catalog/v1',
        'map_id': map_id, 'partition': 'held_out', 'map_sha256': auth.sha(world / 'map.pgm'),
        'world_sha256': auth.sha(world / 'world.sdf'), 'start': {'x': 0, 'y': 0, 'yaw': 0}, 'routes': routes})
    entities = [{'entity_id': map_id + '_chair', 'region_id': map_id + '_chair_region', 'category': 'chair',
                 'route_ids': [row['route_id'] for row in routes]}]
    entities += [{'entity_id': row['terminal_entity_id'], 'region_id': row['terminal_entity_id'] + '_region',
                  'category': 'office_entrance', 'route_ids': [row['route_id']]} for row in routes]
    save('synthetic_world/landmark_scene.yaml', {'schema_version': 'landmark-scene/v1', 'map_id': map_id,
        'map_hash': auth.sha(world / 'map.pgm'), 'partition': 'test', 'entities': entities})
    # Not valid evaluator content: opening these during prepare is itself a bug.
    for name in auth.EVALUATOR_ASSETS:
        save('synthetic_world/' + name, {'synthetic_evaluator_sentinel': True})
    row = {'episode_id': 'synthetic-heldout-only', 'run_id': 'synthetic-heldout-run',
        'map_id': map_id, 'partition': 'held_out', 'runtime_partition': 'test', 'system_id': 'B6',
        'simulation_seed': 1, 'timeout_s': 25, 'world_directory': 'synthetic_world',
        'variant_id': 'base-r015-truthful_original-s0', 'camera_horizontal_fov': 2., 'camera_color_tolerance': 10.,
        'asset_sha256': {name: auth.sha(world / name) for name in auth.ASSETS},
        'instruction': {'variant_id': 'base-r015-truthful_original-s0', 'base_instruction_id': 'base-r015',
                        'raw_text': 'Synthetic instruction fixture only', 'provenance': 'synthetic'}}
    schedule = {'schema_version': 'research3-physical-heldout-schedule/v1', 'evidence_scope': 'physical_world_heldout',
        'design_sha256': design_ref['sha256'], 'calibration_sha256': calibration_ref['sha256'], 'episodes': [row]}
    approval = {'schema_version': 'research3-physical-heldout-runtime-authorization/v1', 'status': 'approved_frozen',
        'authorization_scope': 'physical_heldout_live_execution', 'reviewer_type': 'human',
        'approved_by': 'synthetic-not-a-real-attestation', 'approved_at_utc': 'synthetic-only',
        'gates': {gate: True for gate in auth.GATES}, 'design': design_ref, 'calibration': calibration_ref,
        'schedule': save('schedule.json', schedule), 'ros_domain_id': 89,
        'execution_source_sha256': {name: auth.sha(ROOT / name) for name in auth.SOURCE_FILES},
        'provider_source_sha256': {name: auth.sha(auth.R1 / name) for name in auth.PROVIDER_FILES}}
    save('approval.json', approval)
    return tmp_path, approval, row, save


def admitted(fixture):
    root, _, row, _ = fixture
    path = root / 'approval.json'
    return auth.authorize(path, auth.sha(path), row['episode_id'], root=root)


@pytest.mark.parametrize('provider,name',[
    (False,'src/language_nav/parsing/rule_based.py'),
    (False,'src/language_nav/belief/store.py'),
    (False,'ros_ws/src/language_nav_runtime/language_nav_runtime/monitor_bridge.py'),
    (True,'src/experiment_controller/experiment_controller/run_episode.py'),
    (True,'src/episode_logger/episode_logger/monitor.py'),
    (True,'configs/nav2/nav2_common.yaml'),(True,'configs/systems/s0.yaml')])
def test_changed_named_dependency_rejected_before_schedule_read(synthetic,monkeypatch,provider,name):
    root,approval,row,save=synthetic
    field='provider_source_sha256' if provider else 'execution_source_sha256'
    approval[field][name]='0'*64
    save('approval.json',approval)
    original=Path.read_bytes
    def guarded(path):
        if path.name=='schedule.json':pytest.fail('changed dependency must reject before protected schedule')
        return original(path)
    monkeypatch.setattr(Path,'read_bytes',guarded)
    with pytest.raises(PermissionError,match='checksum'):
        admitted(synthetic)


def test_authorized_synthetic_catalog_has_four_routes_but_no_evaluator_access(synthetic, monkeypatch):
    context = admitted(synthetic)
    world = context.root / 'synthetic_world'
    original = Path.read_bytes
    def guarded(path):
        if path.name in auth.EVALUATOR_ASSETS:
            pytest.fail('evaluator content opened during policy admission')
        return original(path)
    monkeypatch.setattr(Path, 'read_bytes', guarded)
    catalog = validate_physical_launch_inputs(world / 'execution_catalog.json', world / 'landmark_scene.yaml',
                                              heldout_authorization=context)
    assert len(catalog.execution) == 4 and catalog.semantic.partition == 'held_out'
    with pytest.raises(PermissionError):
        load_physical_runtime_catalog(world / 'execution_catalog.json')


@pytest.mark.parametrize('change', [lambda a: a.update(status='draft'),
    lambda a: a.update(reviewer_type='machine'), lambda a: a['gates'].update(heldout_launch_authorized=False),
    lambda a: a.update(execution_source_sha256={}), lambda a: a.update(provider_source_sha256={})])
def test_unapproved_metadata_fails_before_any_protected_schedule_or_asset_open(synthetic, monkeypatch, change):
    root, approval, row, save = synthetic
    change(approval)
    save('approval.json', approval)
    original = Path.read_bytes
    def guarded(path):
        if path.name == 'schedule.json' or 'synthetic_world' in path.parts:
            pytest.fail('protected data opened before authorization')
        return original(path)
    monkeypatch.setattr(Path, 'read_bytes', guarded)
    with pytest.raises(PermissionError):
        admitted(synthetic)


def test_unknown_episode_and_changed_source_or_asset_rejected(synthetic):
    root, approval, _, save = synthetic
    with pytest.raises(PermissionError, match='not explicitly authorized'):
        auth.authorize(root / 'approval.json', auth.sha(root / 'approval.json'), 'unknown', root=root)
    context = admitted(synthetic)
    (root / 'synthetic_world/world.sdf').write_text('changed')
    with pytest.raises(PermissionError, match='checksum'):
        context.asset(root / 'synthetic_world/world.sdf')
    approval['execution_source_sha256']['src/language_nav/live.py'] = '0' * 64
    save('approval.json', approval)
    with pytest.raises(PermissionError, match='checksum'):
        admitted(synthetic)


def test_evaluator_refuses_raw_protected_request_before_any_file_open(tmp_path, monkeypatch):
    def forbidden(*a, **k):
        pytest.fail('protected evaluator asset opened without authorized sealed context')
    monkeypatch.setattr(Path, 'read_bytes', forbidden)
    with pytest.raises(PermissionError):
        RUNTIME['evaluate']({'world_directory': str(tmp_path), 'partition': 'held_out'}, {})


def test_evaluator_context_rejects_changed_measurement_before_assets(tmp_path):
    sealed = tmp_path / 'measurements.json'
    sealed.write_text('{}')
    context = auth.HeldoutEvaluationContext('run', 'map', {}, sealed, auth.sha(sealed), 'a' * 64)
    sealed.write_text('{"changed":true}')
    with pytest.raises(PermissionError):
        RUNTIME['evaluate']({'world_directory': str(tmp_path), 'partition': 'held_out',
            'run_id': 'run', 'map_id': 'map', 'asset_sha256': {}}, {}, heldout_context=context)


def test_overlay_preserves_scene_and_passes_all_authorization_fields(tmp_path):
    request = {'world_directory': str(tmp_path), 'partition': 'held_out', 'runtime_partition': 'test',
        'run_id': 'run', 'heldout_authorization': {'path': '/approval', 'sha256': 'a' * 64, 'episode_id': 'ep'}}
    argv = RUNTIME['overlay_command'](request, tmp_path, 'B6')
    assert argv[:4] == ['ros2', 'launch', 'language_nav_bringup', 'heldout_adapters.launch.py']
    assert f'scene:={tmp_path}/landmark_scene.yaml' in argv
    assert 'partition:=test' in argv and 'heldout_episode_id:=ep' in argv
    assert not any('review_log' in arg for arg in argv)


def test_valid_seal_does_not_authorize_a_different_supplied_trajectory(tmp_path):
    sealed = tmp_path / 'measurements.json'
    record = {'schema_version': 'research3-live-measurements/v2', 'run_id': 'run',
              'ground_truth_positions': [[0, 0], [1, 1]]}
    sealed.write_text(json.dumps(record))
    context = auth.HeldoutEvaluationContext('run', 'map', {}, sealed, auth.sha(sealed), 'a' * 64)
    changed = dict(record, ground_truth_positions=[[0, 0], [9, 9]])
    with pytest.raises(PermissionError, match='differs from sealed'):
        RUNTIME['evaluate']({'world_directory': str(tmp_path / 'never_opened'), 'partition': 'held_out',
            'run_id': 'run', 'map_id': 'map', 'asset_sha256': {}}, changed, heldout_context=context)


def test_real_prepare_uses_approved_instruction_and_never_opens_evaluator(synthetic, monkeypatch):
    context = admitted(synthetic)
    real_authorize = auth.authorize
    monkeypatch.setattr(auth, 'authorize', lambda p, h, e: real_authorize(p, h, e, root=context.root))
    original_bytes, original_text = Path.read_bytes, Path.read_text
    def guarded_bytes(path):
        if path.name in auth.EVALUATOR_ASSETS:
            pytest.fail('prepare opened evaluator assets')
        return original_bytes(path)
    def guarded_text(path, *args, **kwargs):
        if path.name in auth.EVALUATOR_ASSETS or path.name == 'instruction_benchmark_v0.1.json':
            pytest.fail('prepare opened evaluator or unrelated benchmark schedule')
        return original_text(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_bytes', guarded_bytes)
    monkeypatch.setattr(Path, 'read_text', guarded_text)
    request, variant, catalog = RUNTIME['prepare'](context.root / 'synthetic_world',
        context.episode['variant_id'], context.episode['run_id'], 89, 25, 1, heldout_authorization=context)
    assert request['partition'] == 'held_out' and request['runtime_partition'] == 'test'
    assert request['protected_test_routes_used'] is True
    assert request['source_sha256'] == context.approval['execution_source_sha256']
    assert variant == context.episode['instruction'] and len(catalog.execution) == 4


def test_separate_wrapper_reconstructs_camera_and_provenance_without_live_import(synthetic, monkeypatch):
    context = admitted(synthetic)
    real_authorize = auth.authorize
    monkeypatch.setattr(auth, 'authorize', lambda p, h, e: real_authorize(p, h, e, root=context.root))
    wrapper = runpy.run_path(str(ROOT / 'scripts/run_authorized_heldout_episode.py'))
    _, _, request, variant, catalog = wrapper['prepare_authorized'](context.path, context.digest, context.episode_id)
    assert request['protected_test_routes_used'] is True
    assert request['evidence_scope'] == 'physical_world_heldout'
    assert request['runtime_partition'] == 'test'
    assert request['catalog_partition'] == catalog.semantic.partition == 'held_out'
    assert request['camera_horizontal_fov'] == 2. and request['camera_color_tolerance'] == 10.
    assert 'camera_horizontal_fov:=2.0' in request['simulation_launch_argv']
    assert request['capture_review'] is False and request['capture_only'] is False
    assert request['allow_coexistence_trial'] is False


def test_heldout_missing_condition_requires_actual_absence_intervention(synthetic, monkeypatch):
    root, approval, row, save = synthetic
    row['variant_id'] = 'base-r015-missing_landmark-s0'
    row['instruction']['variant_id'] = row['variant_id']
    schedule = json.loads((root / 'schedule.json').read_text())
    schedule['episodes'] = [row]
    approval['schedule'] = save('schedule.json', schedule)
    save('approval.json', approval)
    context = admitted(synthetic)
    real_authorize = auth.authorize
    monkeypatch.setattr(auth, 'authorize', lambda p, h, e: real_authorize(p, h, e, root=root))
    with pytest.raises(ValueError, match='validated physical absence'):
        RUNTIME['prepare'](root / 'synthetic_world', row['variant_id'], row['run_id'], 89, 25, 1,
                           heldout_authorization=context)


def test_authorized_absence_keeps_four_routes_and_rejects_unprotected_provenance(synthetic):
    root, approval, row, save = synthetic
    world = root / 'synthetic_world'
    scene = json.loads((world / 'landmark_scene.yaml').read_text())
    scene['entities'] = [entity for entity in scene['entities'] if entity['category'] != 'chair']
    save('synthetic_world/landmark_scene.yaml', scene)
    report = {'schema_version': 'research3-physical-absence-intervention/v1',
        'base_instruction_id': 'base-r015', 'partition': 'held_out', 'protected_content_used': True,
        'geometry_audit_passed': True, 'map_policy': 'remove_chair_occupancy_for_all_systems',
        'removed_entity_id': row['map_id'] + '_chair',
        'removed_models': ['chair_seat', 'chair_back'] +
            [f'chair_leg_{dx}_{dy}' for dx in (-.16, .16) for dy in (-.16, .16)],
        'asset_sha256': {name: auth.sha(world / name) for name in
            ('world.sdf', 'map.pgm', 'map.yaml', 'execution_catalog.json', 'landmark_scene.yaml')}}
    save('synthetic_world/absence_intervention.json', report)
    row['variant_id'] = row['instruction']['variant_id'] = 'base-r015-missing_landmark-s0'
    row['asset_sha256'] = {name: auth.sha(world / name) for name in auth.ASSETS | {'absence_intervention.json'}}
    schedule = json.loads((root / 'schedule.json').read_text())
    schedule['episodes'] = [row]
    approval['schedule'] = save('schedule.json', schedule)
    save('approval.json', approval)
    context = admitted(synthetic)
    runtime = validate_physical_launch_inputs(world / 'execution_catalog.json', world / 'landmark_scene.yaml',
                                              heldout_authorization=context)
    assert len(runtime.execution) == 4
    report['protected_content_used'] = False
    save('synthetic_world/absence_intervention.json', report)
    row['asset_sha256']['absence_intervention.json'] = auth.sha(world / 'absence_intervention.json')
    schedule['episodes'] = [row]
    approval['schedule'] = save('schedule.json', schedule)
    save('approval.json', approval)
    with pytest.raises(ValueError, match='identity/policy'):
        validate_physical_launch_inputs(world / 'execution_catalog.json', world / 'landmark_scene.yaml',
                                        heldout_authorization=admitted(synthetic))


def test_empty_node_authorization_defaults_do_not_open_files(monkeypatch):
    from types import SimpleNamespace
    class Node:
        def __init__(self):
            self.values = {}
        def declare_parameter(self, key, value):
            self.values.setdefault(key, value)
        def get_parameter(self, key):
            return SimpleNamespace(value=self.values[key])
    monkeypatch.setattr(auth, 'authorize', lambda *args: pytest.fail('default node requested protected access'))
    assert auth.node_authorization(Node()) is None
    partial = Node()
    partial.values['heldout_authorization'] = '/missing'
    with pytest.raises(PermissionError, match='complete'):
        auth.node_authorization(partial)


def test_synthetic_launch_authenticates_before_creating_all_nodes(synthetic, monkeypatch):
    import sys
    from types import ModuleType
    context = admitted(synthetic)
    monkeypatch.setenv('ROS_DOMAIN_ID', '89')
    for name in ('RCN_WORKER_ID', 'GZ_PARTITION', 'IGN_PARTITION'):
        monkeypatch.setenv(name, 'research3-' + context.episode['run_id'])
    modules = {name: ModuleType(name) for name in
               ('launch', 'launch.actions', 'launch.substitutions', 'launch_ros', 'launch_ros.actions')}
    modules['launch'].LaunchDescription = list
    modules['launch.actions'].DeclareLaunchArgument = lambda name: name
    modules['launch.actions'].OpaqueFunction = lambda **kwargs: kwargs
    class Configuration:
        def __init__(self, name):
            self.name = name
        def perform(self, values):
            return values[self.name]
    modules['launch.substitutions'].LaunchConfiguration = Configuration
    modules['launch_ros.actions'].Node = lambda **kwargs: kwargs
    for name, value in modules.items():
        monkeypatch.setitem(sys.modules, name, value)
    monkeypatch.setattr(auth, 'authorize', lambda *args: context)
    launch = runpy.run_path(str(ROOT / 'ros_ws/src/language_nav_bringup/launch/heldout_adapters.launch.py'))
    world = context.root / 'synthetic_world'
    values = {'heldout_authorization': str(context.path), 'heldout_authorization_sha256': context.digest,
        'heldout_episode_id': context.episode_id, 'partition': 'test', 'run_id': context.episode['run_id'],
        'system_id': 'B6', 'color_tolerance': '10', 'scene': str(world / 'landmark_scene.yaml'),
        'physical_catalog': str(world / 'execution_catalog.json'), 'calibration': str(context.root / 'calibration.json'),
        'research2_output_dir': str(context.root / 'reports/physical_live_episodes' / context.episode['run_id'] / 'research2'),
        'research3_output_dir': str(context.root / 'reports/physical_live_episodes' / context.episode['run_id'] / 'research3')}
    nodes = launch['launch_setup'](values)
    assert len(nodes) == 8
    guarded = [node for node in nodes if node['executable'] in
               {'heldout_landmark_bridge', 'semantic_route_node', 'nav2_route_adapter', 'planner_node'}]
    assert len(guarded) == 4
    assert all(node['parameters'][0]['heldout_episode_id'] == context.episode_id for node in guarded)
    values['system_id'] = 'B1'
    with pytest.raises(PermissionError, match='options differ'):
        launch['launch_setup'](values)
    values['system_id'] = 'B6'
    values['research2_output_dir'] = '/synthetic/foreign-research2-dataset'
    with pytest.raises(PermissionError, match='outputs must stay'):
        launch['launch_setup'](values)
    monkeypatch.setenv('ROS_DOMAIN_ID', '0')
    with pytest.raises(PermissionError, match='actual ROS domain'):
        launch['launch_setup'](values)


def test_protected_node_rejects_wrong_actual_domain(synthetic, monkeypatch):
    from types import SimpleNamespace
    context = admitted(synthetic)
    class Node:
        def declare_parameter(self, *args):
            pass
        def get_parameter(self, key):
            return SimpleNamespace(value={'heldout_authorization': str(context.path),
                'heldout_authorization_sha256': context.digest, 'heldout_episode_id': context.episode_id}[key])
    monkeypatch.setattr(auth, 'authorize', lambda *args: context)
    monkeypatch.delenv('ROS_DOMAIN_ID', raising=False)
    with pytest.raises(PermissionError, match='actual ROS domain'):
        auth.node_authorization(Node())


def test_three_ros_consumers_propagate_validated_context_and_provider_inherits_only_callbacks():
    for name in ('ros_ws/src/language_nav_runtime/language_nav_runtime/nav2_adapter.py',
                 'ros_ws/src/language_nav_runtime/language_nav_runtime/semantic_routes.py',
                 'ros_ws/src/language_nav_planner/language_nav_planner/node.py'):
        tree = ast.parse((ROOT / name).read_text())
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        assert any(isinstance(c.func, ast.Name) and c.func.id == 'node_authorization' for c in calls)
        loaders = [c for c in calls if isinstance(c.func, ast.Name) and c.func.id == 'load_physical_runtime_catalog']
        assert loaders and all(any(k.arg == 'heldout_authorization' for k in c.keywords) for c in loaders)
    tree = ast.parse((ROOT / 'ros_ws/src/language_nav_bringup/language_nav_bringup/heldout_landmark_bridge.py').read_text())
    klass = next(n for n in tree.body if isinstance(n, ast.ClassDef))
    assert klass.bases[0].id == 'LandmarkObservationNode'
    assert {n.name for n in klass.body if isinstance(n, ast.FunctionDef)} == {'__init__'}


@pytest.mark.parametrize('args,expected', [
    (['python', str(ROOT / 'scripts/run_authorized_heldout_episode.py')], True),
    (['/opt/ros/jazzy/bin/ros2', 'launch', 'language_nav_bringup', 'heldout_adapters.launch.py'], True),
    (['python3', '/opt/ros/jazzy/bin/ros2', 'launch', 'language_nav_bringup', 'physical_sim.launch.py'], True),
    (['ros2', 'launch', 'failure_monitor', 'physical_sim.launch.py'], False),
    (['python', '-c', 'run_authorized_heldout_episode.py'], False),
])
def test_exact_orphan_runner_and_launch_detection(args, expected):
    from language_nav.campaign_authorization import owned_physical_process
    assert owned_physical_process(args) is expected


def test_orphan_r3_launch_blocks_campaign_lock_without_touching_r2(tmp_path):
    from language_nav.campaign_authorization import exclusive_campaign_runtime
    (tmp_path / 'reports').mkdir()
    proc = tmp_path / 'proc'
    (proc / '912345').mkdir(parents=True)
    (proc / '912345/cmdline').write_bytes(b'ros2\0launch\0language_nav_bringup\0heldout_adapters.launch.py\0')
    with pytest.raises(RuntimeError, match='live runner exists'):
        with exclusive_campaign_runtime(tmp_path, proc):
            pytest.fail('orphan launch admitted')
