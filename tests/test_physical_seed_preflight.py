import importlib.util
import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('physical_seed_preflight',
    ROOT / 'scripts/physical_seed_preflight.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize('seed', [0, -1, True, 1.5, '1', 2**32])
def test_rejects_unspecified_or_invalid_seed(seed):
    with pytest.raises(ValueError):
        MODULE.seeded_gazebo_command('/tmp/world.sdf', seed)


@pytest.mark.parametrize('seed', [1, 2**32 - 1])
def test_server_argv_preserves_exact_seed_and_path_without_shell(seed):
    world = '/tmp/world name $(not-a-command).sdf'
    command = MODULE.seeded_gazebo_command(world, seed)
    assert command[:2] == ['gz', 'sim']
    assert command[-3:] == ['--seed', str(seed), world]
    assert '--headless-rendering' in command


@pytest.mark.parametrize('world', ['world.sdf', '/tmp/world.yaml', '/tmp/bad\x00.sdf'])
def test_rejects_invalid_world_path(world):
    with pytest.raises(ValueError):
        MODULE.seeded_gazebo_command(world, 1)


def test_audit_distinguishes_cli_support_from_provider_wiring(tmp_path):
    ruby = tmp_path / 'sim.rb'
    launch = tmp_path / 'sim.launch.py'
    ruby.write_text("opts.on('--seed [arg]', Integer) do |i|\noptions['seed'] = i\nend\n")
    launch.write_text("# fixed seed (comment is not evidence)\nExecuteProcess(cmd=['gz','sim','world.sdf'])\n")
    report = MODULE.audit_seed_support(ruby, launch)
    assert report['gazebo_cli_seed_supported']
    assert not report['provider_seed_flag_present']
    assert not report['runtime_seed_acceptance_validated']
    assert not report['simulation_launched']
    assert len(report['source_sha256']) == 2
    launch.write_text("ExecuteProcess(cmd=['gz','sim','--seed',str(seed),'world.sdf'])\n")
    assert MODULE.audit_seed_support(ruby, launch)['provider_seed_flag_present']


def test_missing_cli_support_is_not_assumed(tmp_path):
    ruby, launch = tmp_path / 'sim.rb', tmp_path / 'sim.py'
    ruby.write_text('# no parser here')
    launch.write_text('pass')
    report = MODULE.audit_seed_support(ruby, launch)
    assert not report['gazebo_cli_seed_supported']
    assert not report['provider_seed_flag_present']


def test_research3_launch_seed_contract_and_explicit_flag(tmp_path):
    path = ROOT / 'ros_ws/src/language_nav_bringup/launch/physical_sim.launch.py'
    tree = ast.parse(path.read_text())
    function = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == 'seed_value')
    isolated = ast.Module(body=[function], type_ignores=[])
    namespace = {}
    exec(compile(isolated, str(path), 'exec'), namespace)
    validate = namespace['seed_value']
    for value in ('0', '-1', '1.5', '4294967296', '１', '', True):
        with pytest.raises(ValueError):
            validate(value)
    assert validate('1') == 1
    assert validate('4294967295') == 4294967295
    ruby = tmp_path / 'sim.rb'
    ruby.write_text("opts.on('--seed [arg]', Integer) do |i|\noptions['seed'] = i\nend\n")
    report = MODULE.audit_seed_support(ruby, path)
    assert report['provider_seed_flag_present']
