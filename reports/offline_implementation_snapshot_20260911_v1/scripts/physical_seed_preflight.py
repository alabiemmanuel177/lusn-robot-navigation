#!/usr/bin/env python3
"""Offline Gazebo seed audit and argv construction; never starts a simulator."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

DEFAULT_RUBY = Path('/opt/ros/jazzy/opt/gz_sim_vendor/lib/ruby/gz/cmdsim8.rb')
DEFAULT_LAUNCH = Path('/home/eao/risk-calibrated-nav/src/simulation_worlds/launch/sim.launch.py')


def validate_seed(seed: int) -> int:
    # ServerConfig uses unsigned int; zero means unspecified in its API docs.
    if type(seed) is not int or not 1 <= seed <= 2**32 - 1:
        raise ValueError('explicit simulator seed must be an integer in [1, 4294967295]')
    return seed


def seeded_gazebo_command(world: str | Path, seed: int) -> list[str]:
    """Return executable argv for a server only; robot/bridges remain separate.

    Caller must pass this list directly to a process API with shell=False, retain
    it in evidence, and independently enforce ROS/Gazebo resource isolation.
    No world content is opened here and this helper grants no execution authority.
    """
    validate_seed(seed)
    path = Path(world)
    if not path.is_absolute() or path.suffix != '.sdf' or '\x00' in str(path):
        raise ValueError('world must be an absolute .sdf path')
    return ['gz', 'sim', '-r', '-s', '--headless-rendering', '-v', '1',
            '--seed', str(seed), str(path)]


def audit_seed_support(ruby_path: Path = DEFAULT_RUBY,
                       launch_path: Path = DEFAULT_LAUNCH) -> dict:
    """Check installed CLI parser and literal ExecuteProcess command wiring.

    This conservative source audit does not prove runtime reproducibility.
    Dynamic seed wiring not recognized here remains unverified, never assumed.
    """
    ruby_raw, launch_raw = ruby_path.read_bytes(), launch_path.read_bytes()
    ruby = ruby_raw.decode()
    tree = ast.parse(launch_raw.decode())
    commands = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func.id if isinstance(node.func, ast.Name) else ''
        if function != 'ExecuteProcess':
            continue
        for keyword in node.keywords:
            if keyword.arg == 'cmd' and isinstance(keyword.value, (ast.List, ast.Tuple)):
                literals = [item.value if isinstance(item, ast.Constant) else '<dynamic>'
                            for item in keyword.value.elts]
                if literals[:2] == ['gz', 'sim']:
                    commands.append(literals)
    cli_supported = ("opts.on('--seed [arg]', Integer)" in ruby
                     and "options['seed'] = i" in ruby)
    wired = bool(commands) and all('--seed' in command for command in commands)
    return {
        'schema_version': 'research3-seed-source-preflight/v1',
        'gazebo_cli_seed_supported': cli_supported,
        'provider_literal_gazebo_commands': commands,
        'provider_seed_flag_present': wired,
        'runtime_seed_acceptance_validated': False,
        'bitwise_determinism_claimed': False,
        'simulation_launched': False,
        'source_sha256': {str(ruby_path): hashlib.sha256(ruby_raw).hexdigest(),
                          str(launch_path): hashlib.sha256(launch_raw).hexdigest()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--world', type=Path)
    parser.add_argument('--seed', type=int)
    parser.add_argument('--output', type=Path, help='optional create-once source audit report')
    parser.add_argument('--ruby-source', type=Path, default=DEFAULT_RUBY)
    parser.add_argument('--provider-launch', type=Path, default=DEFAULT_LAUNCH)
    args = parser.parse_args()
    if (args.world is None) != (args.seed is None):
        parser.error('--world and --seed must be supplied together')
    report = audit_seed_support(args.ruby_source, args.provider_launch)
    if args.world is not None:
        if not report['gazebo_cli_seed_supported']:
            parser.error('installed parser seed support could not be verified')
        report['proposed_server_argv'] = seeded_gazebo_command(args.world, args.seed)
    encoded = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        with args.output.open('x') as stream:
            stream.write(encoded + '\n')
    print(encoded)


if __name__ == '__main__':
    main()
