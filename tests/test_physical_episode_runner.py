"""Offline runner safety and independent scoring; no ROS or simulator needed."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('physical_episode_runner', ROOT / 'scripts/run_physical_episode.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def prepared():
    return runner.prepare(ROOT / 'data/physical_worlds_v1/base-r010',
                          'base-r010-truthful_original-s0', 'offline-test', 89)


def trajectory(route='right_2'):
    endpoint_x = 7.5 if route.endswith('2') else 4.3
    points = [[.6 + i * .1, 0.] for i in range(round((endpoint_x - .6) * 10) + 1)]
    points.extend([[endpoint_x, -i * .1] for i in range(1, 21)])
    stamps = [1_000_000_000 + i * 100_000_000 for i in range(len(points))]
    return dict(ground_truth_positions=points, ground_truth_timestamps_ns=stamps,
                episode_started_at_ns=stamps[0], episode_ended_at_ns=stamps[-1],
                selected_route_id='r3geo_base_r010_' + route, collision_count=0,
                nav2_reported_success=True, timeout=False)


def test_preparation_and_overlay_are_deployable_only(tmp_path):
    request, variant, catalog = prepared()
    assert len(catalog.execution) == 4
    assert request['detector_calibration_transfer_validated'] is False
    assert request['protected_test_routes_used'] is False
    command = runner.overlay_command(request, tmp_path, 'B6')
    assert any('physical_catalog:=' in value for value in command)
    assert all('manifest.json' not in value and 'ordered_geometry' not in value
               and 'expected_route' not in value for value in command)
    assert not any(value.startswith('calibration:=') for value in command)
    assert variant['base_instruction_id'] == 'base-r010'


def test_camera_profile_changes_only_rendered_colours_and_keeps_associations(tmp_path):
    import yaml
    from language_nav.adapters.landmark_palette import adapt_scene_palette
    from language_nav.benchmark.physical_catalog import validate_physical_launch_inputs
    folder = ROOT / 'data/physical_worlds_v1/base-r010'
    destination = tmp_path / 'runtime_scene.yaml'
    adapt_scene_palette(folder / 'landmark_scene.yaml', destination,
                        ROOT / 'configs/physical_dev10_camera_profile_v1.yaml')
    validate_physical_launch_inputs(folder / 'execution_catalog.json', destination)
    original = yaml.safe_load((folder / 'landmark_scene.yaml').read_text())
    adapted = yaml.safe_load(destination.read_text())
    for before, after in zip(original['entities'], adapted['entities']):
        assert {k: v for k, v in before.items() if k != 'marker_rgb'} == {
            k: v for k, v in after.items() if k != 'marker_rgb'}
    request, _, _ = prepared()
    request.update(runtime_scene=str(destination), camera_color_tolerance=10.0)
    command = runner.overlay_command(request, tmp_path, 'B6')
    assert f'scene:={destination}' in command
    assert 'color_tolerance:=10.0' in command


def test_review_capture_explicitly_wires_pending_provider_tasks(tmp_path):
    request, _, _ = prepared()
    assert not any(arg.startswith('review_log:=') for arg in runner.overlay_command(request, tmp_path, 'B6'))
    request['capture_review'] = True
    assert f'review_log:={tmp_path / "landmark_review_tasks.jsonl"}' in runner.overlay_command(request, tmp_path, 'B6')


def test_missing_landmark_cannot_run_with_chair_present():
    with pytest.raises(ValueError, match='physical absence intervention'):
        runner.prepare(ROOT / 'data/physical_worlds_v1/base-r010',
                       'base-r010-missing_landmark-s0', 'absent-test', 89)


def test_capture_and_launch_implementation_are_pinned():
    request, _, _ = prepared()
    for path in ('scripts/physical_perception_capture.py',
                 'src/language_nav/live_resources.py',
                 'ros_ws/src/language_nav_bringup/launch/live_adapters.launch.py'):
        assert len(request['source_sha256'][path]) == 64


def test_missing_landmark_derivative_prepares_without_observation_oracle():
    request, _, catalog = runner.prepare(ROOT / 'data/physical_absence_worlds_v1/base-r010',
        'base-r010-missing_landmark-s0', 'absent-engineering', 89)
    assert request['environment_intervention'] == 'missing_landmark'
    assert 'absence_intervention.json' in request['asset_sha256']
    assert len(catalog.execution) == 4
    assert all(route.proposal.observation_coverage == 0 for route in catalog.semantic.routes)


def test_absent_world_cannot_impersonate_truthful_condition():
    with pytest.raises(ValueError, match='requires missing-landmark'):
        runner.prepare(ROOT / 'data/physical_absence_worlds_v1/base-r010',
                       'base-r010-truthful_original-s0', 'wrong-condition', 89)


@pytest.mark.parametrize('seed', [0, -1, True, 2**32, 1.5])
def test_invalid_simulator_seeds_fail_offline(seed):
    with pytest.raises(ValueError, match='simulation_seed'):
        runner.prepare(ROOT / 'data/physical_worlds_v1/base-r010',
                       'base-r010-truthful_original-s0', 'seed-test', 89, simulation_seed=seed)


def test_seeded_launch_is_r3_owned_and_pinned():
    request, _, _ = prepared()
    argv = request['simulation_launch_argv']
    assert argv[:4] == ['ros2', 'launch', 'language_nav_bringup', 'physical_sim.launch.py']
    assert 'simulation_seed:=1' in argv
    assert 'ros_ws/src/language_nav_bringup/launch/physical_sim.launch.py' in request['source_sha256']


@pytest.mark.parametrize('run_id', ['../escape', '/tmp/escape', '', 'two words'])
def test_unsafe_run_identity_refused(run_id):
    with pytest.raises(ValueError, match='run ID'):
        runner.prepare(ROOT / 'data/physical_worlds_v1/base-r010', 'unused', run_id, 89)


@pytest.mark.parametrize('domain', [0, -1, 102, True])
def test_requires_explicit_safe_domain(domain):
    with pytest.raises(ValueError, match='domain'):
        runner.prepare(ROOT / 'data/physical_worlds_v1/base-r010', 'unused', 'valid-id', domain)


def test_protected_and_mismatched_instruction_refused(tmp_path):
    # Exercise refusal with synthetic metadata, never an actual reserved world.
    protected = tmp_path / 'synthetic-protected'
    protected.mkdir()
    (protected / 'execution_catalog.json').write_text(json.dumps({
        'schema_version': 'research3-physical-route-catalog/v1',
        'map_id': 'r3geo_base_r020', 'partition': 'held_out',
        'map_sha256': '0' * 64, 'world_sha256': '0' * 64,
        'start': {}, 'routes': [],
    }))
    with pytest.raises(PermissionError):
        runner.prepare(protected,
                       'base-r020-truthful_original-s0', 'heldout-refused', 89)
    with pytest.raises(ValueError, match='instruction'):
        runner.prepare(ROOT / 'data/physical_worlds_v1/base-r010',
                       'base-r001-truthful_original-s0', 'mismatch-refused', 89)


def test_create_once_preserves_previous_artifact(tmp_path):
    path = tmp_path / 'request.json'
    runner.write_once(path, {'original': True})
    with pytest.raises(FileExistsError):
        runner.write_once(path, {'original': False})
    assert json.loads(path.read_text()) == {'original': True}


def test_independent_ordered_score_and_wrong_door_negative_control():
    request, _, _ = prepared()
    correct = runner.evaluate(request, trajectory())
    assert correct['navigation_success']
    assert correct['instruction_completion'] is True
    wrong = runner.evaluate(request, trajectory('right_1'))
    assert wrong['navigation_success']  # reached policy goal, but wrong semantic goal
    assert wrong['terminal_identity_correct'] is False
    assert wrong['instruction_completion'] is False


def test_bad_trajectory_invalidates_success():
    request, _, _ = prepared()
    evidence = trajectory()
    evidence['episode_ended_at_ns'] += 2_000_000_000
    score = runner.evaluate(request, evidence)
    assert not score['navigation_success']
    assert score['instruction_completion'] is None
    assert not score['semantic_outcome_measured']


def test_input_mutation_rejected():
    request, _, _ = prepared()
    request['asset_sha256']['world.sdf'] = 'tampered'
    with pytest.raises(ValueError, match='input changed'):
        runner.evaluate(request, trajectory())


@pytest.mark.parametrize('dispatched', [True, False])
def test_evidence_can_be_independently_reaudited(tmp_path, dispatched):
    audit_spec = importlib.util.spec_from_file_location('live_audit', ROOT / 'scripts/analyze_measured_live.py')
    audit = importlib.util.module_from_spec(audit_spec)
    audit_spec.loader.exec_module(audit)
    request, _, _ = prepared()
    evidence = trajectory()
    if not dispatched:
        evidence.update(selected_route_id=None, nav2_reported_success=False)
    evidence.update(schema_version='research3-live-measurements/v2', run_id=request['run_id'], predictions=[])
    summary = runner.evaluate(request, evidence)
    runner.write_once(tmp_path / 'measurements.json', evidence)
    summary.update(schema_version='research3-live-summary/v3', run_id=request['run_id'],
                   partition='development', protected_test_routes_used=False,
                   measurements_sha256=runner.hashlib.sha256((tmp_path / 'measurements.json').read_bytes()).hexdigest(),
                   episode_started_at_ns=evidence['episode_started_at_ns'],
                   episode_ended_at_ns=evidence['episode_ended_at_ns'], episode_prediction_count=0)
    runner.write_once(tmp_path / 'summary.json', summary)
    assert audit.audit_summary(tmp_path / 'summary.json')['instruction_completion'] is True
    if not dispatched:
        assert summary['goal_error_m'] is None and evidence['commanded_goal'] is None
        assert summary['navigation_success'] is False


def test_confirmed_execution_ignores_missing_or_undispatched_record(tmp_path):
    request, variant, _ = prepared()
    path = tmp_path / 'adapter.json'
    assert runner.confirmed_execution(path, request, variant['variant_id']) is None
    record = dict(schema_version='research3-live-episode/v1', run_id=request['run_id'],
                  instruction_id=variant['variant_id'], route_id='', started_at_ns=0)
    runner.write_once(path, record)
    assert runner.confirmed_execution(path, request, variant['variant_id']) is None


def test_confirmed_execution_binds_identity(tmp_path):
    request, variant, _ = prepared()
    path = tmp_path / 'adapter.json'
    record = dict(schema_version='research3-live-episode/v1', run_id=request['run_id'],
                  instruction_id=variant['variant_id'], route_id='r3geo_base_r010_right_1', started_at_ns=1)
    runner.write_once(path, record)
    assert runner.confirmed_execution(path, request, variant['variant_id'])['record']['route_id'].endswith('right_1')
    with pytest.raises(ValueError, match='identity'):
        runner.confirmed_execution(path, request, 'another-instruction')


def test_raw_capture_survives_adapter_identity_failure(tmp_path):
    request, variant, _ = prepared()
    (tmp_path / 'research3').mkdir()
    runner.write_once(tmp_path / 'research3' / (request['run_id'] + '.json'),
                      {'schema_version': 'wrong-adapter-schema'})
    evidence = trajectory()
    evidence.update(selected_route_id=None, nav2_reported_success=False,
                    raw_outcome_navigation_success=True, confirmed_adapter_execution=None)
    with pytest.raises(ValueError, match='identity'):
        runner.retain_capture_then_confirm(tmp_path, request, variant['variant_id'], evidence)
    retained = json.loads((tmp_path / 'capture.json').read_text())
    assert retained['ground_truth_positions'] == evidence['ground_truth_positions']
    assert retained['ground_truth_timestamps_ns'] == evidence['ground_truth_timestamps_ns']
    assert retained['raw_outcome_navigation_success'] is True
    assert retained['nav2_reported_success'] is False
