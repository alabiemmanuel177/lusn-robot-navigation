#!/usr/bin/env python3
"""Explicit non-protected engineering snapshot; not a completed study release."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parents[1]
WORLD_FILES = ('world.sdf', 'map.pgm', 'map.yaml', 'manifest.json', 'execution_catalog.json',
               'landmark_scene.yaml', 'ordered_geometry.json', 'verified_ordered_geometry.json',
               'geometry_audit.json')
CONFIGS = ('research_dependencies.yaml', 'physical_campaign_draft_v1.yaml',
           'physical_experiment_design_draft_v2.yaml', 'physical_dev10_camera_profile_v1.yaml',
           'instruction_schema.json', 'semantic_route_catalog.schema.json', 'ontology.yaml',
           'guards.yaml', 'evaluator_denylist.yaml')
DOCS = ('CONSOLIDATED_REVIEW_HANDOFF.md', 'CONSOLIDATED_REVIEW_RENDERING.md',
        'OFFLINE_EXPERIMENT_DESIGN.md', 'OFFLINE_ANALYSIS_RELEASE.md',
        'howto-authorized-physical-heldout.md', 'STATUS.md')
RUN_FILES = ('request.json', 'capture.json', 'capture_summary.json', 'summary.json',
             'measurements.json', 'landmark_review_tasks.jsonl', 'runtime_scene.yaml', 'nav2_params.yaml',
             'resource_guard.json', 'failure.json')
RUN_LOGS = ('logs/controller.log', 'logs/nav2.log', 'logs/research3.log')
CAMERA_FIXED = ('request.json', 'summary.json', 'observation_index.json')
NONPROTECTED_MAPS = {f'r3geo_base_r{i:03d}' for i in range(1, 15)}


def current_capture_plan_paths(root, directory):
    directory = safe_path(root, directory)
    plan_path = safe_path(root, directory/'plan.json')
    plan = json.loads(plan_path.read_bytes())
    inherited = []
    snapshot = safe_path(root, directory/'current_source_snapshot.json')
    snapshot_data = json.loads(snapshot.read_bytes())
    if snapshot_data.get('schema_version') != 'research3-capture-source-snapshot/v1':
        raise ValueError('unsupported capture source snapshot')
    if plan.get('schema_version') == 'research3-stationary-capture-plan/v1':
        rows = plan.get('views', [])
        expected = {(f'base-r{i:03d}', category) for i in range(1, 15)
                    for category in ('chair', 'laboratory_entrance', 'office_entrance')}
        if (plan.get('protected_content_read') is not False or len(rows) != 42
                or {(row.get('base_instruction_id'), row.get('category')) for row in rows} != expected
                or plan.get('runner_sha256') != snapshot_data.get('source_sha256', {}).get('scripts/run_physical_episode.py')):
            raise ValueError('complete original nonprotected plan/source binding required')
        inherited = [plan_path, snapshot] + [safe_path(root, directory/'profiles'/f'base-r{i:03d}.yaml')
                                            for i in range(1, 15)]
        recapture = safe_path(root, directory/'recapture_plan.json')
        if not recapture.exists():
            return inherited
        plan = json.loads(recapture.read_bytes())
        if plan.get('original_plan_sha256') != digest(plan_path.read_bytes()):
            raise ValueError('recapture plan must bind original plan')
        plan_path = recapture
    if (plan.get('schema_version') != 'research3-current-source-recapture-plan/v1'
            or not (plan.get('protected_content_read') is False or plan.get('protected_data_used') is False)
            or plan.get('human_labels_generated') is not False):
        raise ValueError('explicit nonprotected unlabelled current capture plan required')
    rows = plan.get('views', [])
    if (len(rows) != 46 or any(row.get('base_instruction_id') not in
            {f'base-r{i:03d}' for i in range(1, 15)} for row in rows)
            or {phase: sum(row.get('phase') == phase for row in rows)
                for phase in ('development', 'validation', 'stress')} !=
                {'development': 30, 'validation': 12, 'stress': 4}):
        raise ValueError('complete explicit 46-view nonprotected scope required')
    names = {f'profiles/base-r{i:03d}.yaml' for i in range(1, 15)} | {'profiles/stress-dev10.yaml'}
    if set(plan.get('profile_files', {})) != names:
        raise ValueError('exact fourteen ordinary and one stress profile required')
    paths = inherited + [plan_path]
    for name, expected in sorted(plan['profile_files'].items()):
        path = safe_path(root, directory/name)
        if digest(path.read_bytes()) != expected:
            raise ValueError('current capture profile checksum mismatch')
        paths.append(path)
    if digest(snapshot.read_bytes()) != plan.get('snapshot_sha256'):
        raise ValueError('current source snapshot checksum mismatch')
    paths.append(snapshot)
    stress = safe_path(root, directory/'stress_commands.json')
    if stress.exists():
        if digest(stress.read_bytes()) != plan.get('stress_commands_sha256'):
            raise ValueError('stress commands checksum mismatch')
        paths.append(stress)
    return sorted(set(paths))


def capture_settings_paths(root, directory):
    """Explicit revised settings, never a reports-tree discovery operation."""
    directory = safe_path(root, directory)
    freeze_path = safe_path(root, directory/'camera_settings_freeze.json')
    freeze = json.loads(freeze_path.read_bytes())
    if (freeze.get('schema_version') != 'research3-engineering-camera-freeze/v2'
            or freeze.get('protected_data_used') is not False
            or freeze.get('human_labels_generated') is not False
            or freeze.get('confidence_calibration_frozen') is not False
            or set(freeze.get('profiles', {})) != NONPROTECTED_MAPS):
        raise ValueError('explicit nonprotected unlabelled camera settings required')
    paths = [freeze_path]
    for map_id, expected in sorted(freeze['profiles'].items()):
        path = safe_path(root, directory/'profiles'/('base-r'+map_id[-3:]+'.yaml'))
        if digest(path.read_bytes()) != expected:
            raise ValueError('revised camera profile checksum mismatch')
        paths.append(path)
    commands = safe_path(root, directory/'validation_commands.json')
    payload = json.loads(commands.read_bytes())
    if (payload.get('schema_version') != 'research3-frozen-camera-validation-commands/v1'
            or payload.get('protected_content_used') is not False
            or any(row.get('base_instruction_id') not in {f'base-r{i:03d}' for i in range(11, 15)}
                   for row in payload.get('commands', []))):
        raise ValueError('invalid explicit validation commands')
    paths.append(commands)
    return paths


def capture_source_archive_paths(root, archive):
    from language_nav.camera_configuration import CAPTURE_SOURCE_PATHS, PROVIDER_SOURCE_FILES
    archive = safe_path(root, archive)
    manifest = verify_archive(archive)
    if (manifest.get('schema_version') != 'research3-capture-source-archive/v1'
            or manifest.get('protected_data_included') is not False
            or manifest.get('human_labels_included') is not False
            or manifest.get('external_environment_closure_complete') is not False):
        raise ValueError('explicit capture source archive schema/scope required')
    snapshot = manifest.get('capture_source_snapshot', {})
    sources = snapshot.get('source_sha256', {})
    if (not sources or any(name not in CAPTURE_SOURCE_PATHS
            and not (name.startswith('src/language_nav/') and name.endswith('.py'))
            and not (name.startswith('ros_ws/src/language_nav_interfaces/msg/') and name.endswith('.msg'))
            for name in sources)):
        raise ValueError('unrecognized frozen capture source names')
    allowed = ({'research3/' + name for name in sources}
               | {'external_provider/' + name for name in PROVIDER_SOURCE_FILES}
               | {'external_provider/active_build/' + name for name in ('__init__.py', 'core.py', 'node.py')}
               | {'external_provider/active_transforms/' + name for name in ('live_risk_node.py', 'projection.py')})
    if set(manifest['files']) != allowed:
        raise ValueError('capture snapshot differs from fixed source/config allowlist')
    if any(manifest['files']['research3/' + name]['sha256'] != expected for name, expected in sources.items()):
        raise ValueError('source archive differs from declared capture pins')
    provider = snapshot.get('provider_source_snapshot', {})
    external = provider.get('files', {})
    if set(external) != set(PROVIDER_SOURCE_FILES) or any(
            manifest['files']['external_provider/' + name]['sha256'] != expected for name, expected in external.items()):
        raise ValueError('source archive differs from declared provider pins')
    for prefix, key in (('active_build', 'active_build_files'), ('active_transforms', 'active_transform_files')):
        for name, record in provider.get(key, {}).items():
            if manifest['files'].get('external_provider/' + prefix + '/' + name, {}).get('sha256') != record.get('sha256'):
                raise ValueError('source archive differs from active provider pins')
    return [archive]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def safe_path(root, path):
    path = Path(path)
    path = path if path.is_absolute() else root/path
    if not path.is_relative_to(root) or any(part.startswith('.') for part in path.relative_to(root).parts):
        raise ValueError('hidden or outside-workspace snapshot input')
    current = root
    for part in path.relative_to(root).parts:
        current = current/part
        if current.is_symlink():
            raise ValueError('symlink snapshot input rejected')
    if not path.resolve().is_relative_to(root):
        raise ValueError('snapshot input escapes workspace')
    return path


def standard_paths(root, include_historical_settings_v1=False):
    """Enumerate known source trees and exact non-protected asset names only."""
    paths = []
    for tree, suffixes in (('src', {'.py'}), ('scripts', {'.py'}), ('tests', {'.py'}),
                           ('ros_ws/src', {'.py', '.xml', '.yaml', '.msg', '.srv', '.action', '.cfg'})):
        directory = root/tree
        if not directory.is_dir():
            raise ValueError('missing source tree: ' + tree)
        for path in sorted(directory.rglob('*')):
            if '__pycache__' in path.parts or any(part.startswith('.') for part in path.relative_to(directory).parts):
                continue
            if path.is_symlink():
                raise ValueError('symlink in source tree')
            if path.is_file() and (path.suffix in suffixes or path.name == 'CMakeLists.txt'
                                  or path.parent.name == 'resource'):
                paths.append(path)
    for family, audits in (('physical_worlds_v1', ()),
                           ('physical_worlds_readable_v1', ('visual_derivative_audit.json',)),
                           ('physical_absence_worlds_v1', ('absence_intervention.json',))):
        for index in range(1, 15):
            paths.extend(root/'data'/family/f'base-r{index:03}'/name for name in (*WORLD_FILES, *audits))
    for version in ('v1', 'v2', 'v3'):
        categories = ('chair',) if version == 'v3' else ('chair', 'doorway', 'laboratory_entrance', 'office_entrance')
        for category in categories:
            paths.extend(root/'data'/f'physical_shape_stress_dev10_{version}'/category/'base-r010'/name
                         for name in (*WORLD_FILES, 'source_readable_audit.json', 'shape_stress_audit.json'))
    paths.append(root/'pyproject.toml')
    if (root/'README.md').is_file():
        paths.append(root/'README.md')
    paths.extend(root/'configs'/name for name in CONFIGS)
    paths.extend(root/'docs'/name for name in DOCS if (root/'docs'/name).is_file())
    paths.extend(sorted((root/'docs').glob('PHYSICAL_*.md')))
    settings = [('stationary_capture_plan_v1', ('plan.json',)),
                ('engineering_camera_settings_v2', ('camera_settings_freeze.json', 'validation_commands.json'))]
    if include_historical_settings_v1:
        settings.append(('engineering_camera_settings_v1', ('camera_settings_freeze.json', 'validation_commands.json')))
    for family, names in settings:
        paths.extend(root/'reports'/family/name for name in names)
        paths.extend(root/'reports'/family/'profiles'/f'base-r{index:03}.yaml' for index in range(1, 15))
    return paths


def run_paths(root, directories):
    paths, records, identifiers = [], [], set()
    for directory in directories:
        directory = safe_path(root, directory)
        request_path = safe_path(root, directory/'request.json')
        request = json.loads(request_path.read_text())
        match = re.fullmatch(r'r3geo_base_r(\d{3})', request.get('map_id', ''))
        number = int(match[1]) if match else 0
        partition = 'development' if 1 <= number <= 10 else 'validation' if 11 <= number <= 14 else None
        if (partition is None or request.get('partition') != partition
                or request.get('protected_test_routes_used') is not False):
            raise ValueError('protected or unknown run rejected before reading its evidence')
        if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,95}', request.get('run_id', ''))
                or request['run_id'] in identifiers):
            raise ValueError('missing or duplicate run ID')
        identifiers.add(request['run_id'])
        tasks = directory/'landmark_review_tasks.jsonl'
        if tasks.is_file():
            safe_path(root, tasks)
            for line in tasks.read_text().splitlines():
                if not line.strip():
                    continue
                task = json.loads(line)
                if (task.get('schema_version') != 'landmark-review-task/v1'
                        or task.get('partition') != partition or task.get('correct') is not None
                        or task.get('review_status') != 'pending_human_review'
                        or task.get('reviewer_id') != ''):
                    raise ValueError('labelled or invalid provider task rows are not snapshot inputs')
        paths.extend(directory/name for name in RUN_FILES if (directory/name).is_file())
        # Exact owned navigation/decision diagnostics only; no shell/simulator
        # log sweep and no external Research 2 directory reads.
        diagnostics = (*RUN_LOGS, f"research3/{request['run_id']}.json",
                       f"research3/{request['run_id']}.trace.json")
        paths.extend(directory/name for name in diagnostics if (directory/name).is_file())
        for camera in ('perception_capture', 'context_capture'):
            folder = directory/camera
            if not folder.exists():
                continue
            safe_path(root, folder)
            paths.extend(folder/name for name in CAMERA_FIXED if (folder/name).is_file())
            # No arbitrary logs, rendered QA answers, reviewed labels or files
            # referenced by untrusted paths are swept into the archive.
            paths.extend(path for path in sorted(folder.iterdir()) if re.fullmatch(
                r'frame-\d{3}(?:-(?:rgb|depth)\.bin|\.json)', path.name))
        records.append({'directory': str(directory.relative_to(root)), 'run_id': request['run_id'],
                        'map_id': request['map_id'], 'partition': partition,
                        'request_sha256': digest(request_path.read_bytes()),
                        'requested_source_sha256': request.get('source_sha256', {}),
                        'requested_provider_source_snapshot': request.get('provider_source_snapshot')})
    return paths, records


def engineering_evidence_paths(root, supplied, run_records):
    """Explicit known engineering artifacts only, never review progress/labels.

Schema-less smoke journals additionally require each attempted run to be an
explicit, independently nonprotected-gated --run input. Missing/failed outcomes
are retained; a journal is not required to claim scientific success.
    """
    paths, references, seen = [], [], set()
    run_ids = {row['run_id'] for row in run_records}

    def check_content(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if ((key.startswith('protected_') and child is not False)
                        or (key in ('correct', 'human_correct', 'human_incorrect') and child is not None)
                        or (key in ('reviewer_id', 'human_reviewer_id') and child not in ('', None))
                        or (key in ('human_labels_generated', 'human_labels_present') and child not in (False, 0))):
                    raise ValueError('protected or human-labelled engineering evidence')
                if (key in ('path', 'directory', 'partition', 'world_directory', 'map_id', 'base_instruction_id')
                        and isinstance(child, str) and re.search(r'held[-_ ]?out|protected', child, re.I)):
                    raise ValueError('protected reference in engineering evidence')
                check_content(child)
        elif isinstance(value, list):
            for child in value:
                check_content(child)
        elif isinstance(value, str):
            for match in re.finditer(r'(?:r3geo_base_r|base-r)(\d{3})', value):
                if not 1 <= int(match[1]) <= 14:
                    raise ValueError('protected map reference in engineering evidence')

    for supplied_path in supplied:
        path = safe_path(root, supplied_path)
        relative = str(path.relative_to(root))
        if relative in seen:
            raise ValueError('duplicate engineering evidence path')
        seen.add(relative)
        schema = None
        journal = False
        source_audit = False
        source_comparison = False
        if re.fullmatch(r'reports/physical_review_packet_(?:ordinary_)?\d{8}_audit_v\d+\.json', relative):
            schema = 'research3-review-packet-provenance-audit/v1'
        elif re.fullmatch(r'reports/physical_engineering_smoke_plan_v\d+\.json', relative):
            schema = 'research3-physical-engineering-smoke/v1'
        elif re.fullmatch(r'reports/physical_engineering_smoke_batch_v\d+/report\.json', relative):
            schema = 'research3-physical-engineering-smoke-execution/v1'
        elif re.fullmatch(r'reports/physical_engineering_smoke_batch_v\d+/attempts\.jsonl', relative):
            journal = True
        elif re.fullmatch(r'reports/physical_engineering_smoke_audit_\d{8}_v\d+\.json', relative):
            schema = 'research3-physical-engineering-smoke-audit/v1'
        elif re.fullmatch(r'reports/current_capture_source_audit_\d{8}_v\d+\.json', relative):
            schema = 'research3-current-capture-source-audit/v1'
            source_audit = True
        elif re.fullmatch(r'reports/physical_source_comparison_\d{8}_v\d+\.json', relative):
            schema = 'research3-physical-source-comparison/v1'
            source_comparison = True
        elif re.fullmatch(r'reports/physical_nonprotected_differential_\d{8}_v\d+\.json', relative):
            schema = 'research3-nonprotected-catalog-differential/v1'
            source_comparison = True
        elif re.fullmatch(r'reports/physical_nonprotected_source_supplement_\d{8}_v\d+\.json', relative):
            schema = 'research3-nonprotected-source-supplement/v1'
            source_comparison = True
        else:
            raise ValueError('engineering evidence filename is not allowlisted')
        raw = path.read_bytes()
        value = ([json.loads(line) for line in raw.splitlines() if line.strip()]
                 if journal else json.loads(raw))
        if not journal and (not isinstance(value, dict) or value.get('schema_version') != schema
                            or (not source_audit and value.get('protected_data_used') is not False)):
            raise ValueError('invalid engineering evidence schema or scope')
        checked_value = value
        if schema == 'research3-nonprotected-catalog-differential/v1' and 'synthetic_default_refusals' in value:
            refusals = value['synthetic_default_refusals']
            if not isinstance(refusals, list) or any(
                    not isinstance(row, dict)
                    or set(row) != {'baseline', 'current', 'both_refuse_before_asset_access',
                                    'map_id', 'synthetic_partition'}
                    or row['baseline'] != 'PermissionError' or row['current'] != 'PermissionError'
                    or row['both_refuse_before_asset_access'] is not True
                    or row['map_id'] != 'r3geo_base_r015'
                    or row['synthetic_partition'] not in ('test', 'held_out', 'development')
                    for row in refusals):
                raise ValueError('invalid synthetic pre-access refusal evidence')
            checked_value = {key: child for key, child in value.items() if key != 'synthetic_default_refusals'}
        check_content(checked_value)
        if source_comparison and (value.get('deployment_eligible') is not False
                or value.get('equivalence_approved') is not False
                or value.get('study_complete', False) is not False):
            raise ValueError('source comparison must remain nonapproved engineering evidence')
        rows = value if journal else value.get('rows', []) if source_audit else value.get('attempts', [])
        if source_audit and (not isinstance(rows, list) or not rows
                or value.get('human_labels_generated') is not False
                or value.get('qa_attestations_generated') is not False):
            raise ValueError('capture source audit requires explicit unlabelled rows')
        attempted = set()
        for row in rows:
            if (not isinstance(row, dict) or row.get('run_id') not in run_ids
                    or row['run_id'] in attempted):
                raise ValueError('journal attempts require unique explicit nonprotected runs')
            attempted.add(row['run_id'])
            if source_audit:
                record = next(record for record in run_records if record['run_id'] == row['run_id'])
                if row.get('request_sha256') not in (None, record['request_sha256']):
                    raise ValueError('capture source audit request binding mismatch')
                if row.get('capture_summary_sha256') is not None:
                    summary = safe_path(root, root/record['directory']/'capture_summary.json')
                    if digest(summary.read_bytes()) != row['capture_summary_sha256']:
                        raise ValueError('capture source audit summary binding mismatch')
        paths.append(path)
        references.append({'path': relative, 'schema_version': schema,
                           'journal_scope': 'explicit_nonprotected_runs' if journal or source_audit else None,
                           'sha256': digest(raw)})
    return paths, references


def review_packet_paths(root, directory):
    directory = safe_path(root, directory)
    manifest_path = safe_path(root, directory/'packet_manifest.json')
    manifest = json.loads(manifest_path.read_text())
    required = {'inventory.json', 'combined_visual_qa.jsonl', 'sampling_policy.json'}
    if (manifest.get('schema_version') != 'research3-physical-review-packet/v1'
            or manifest.get('protected_data_used') is not False
            or manifest.get('human_labels_generated') is not False
            or set(manifest.get('files', {})) not in (required, required | {'extra_selection.json'})):
        raise ValueError('invalid non-protected unlabelled review packet inventory')
    paths = [manifest_path]
    for name, expected in manifest['files'].items():
        path = safe_path(root, directory/name)
        if digest(path.read_bytes()) != expected:
            raise ValueError('review packet member checksum mismatch')
        paths.append(path)
    inventory = json.loads((directory/'inventory.json').read_text())
    if inventory.get('protected_data_used') is not False:
        raise ValueError('protected review inventory')
    for item in inventory.get('items', []):
        match = re.fullmatch(r'r3geo_base_r(\d{3})', item.get('map_id', ''))
        number = int(match[1]) if match else 0
        partition = 'development' if 1 <= number <= 10 else 'validation' if 11 <= number <= 14 else None
        if (partition is None or item.get('partition') != partition
                or item.get('correct') is not None or item.get('human_reviewer_id', '') != ''):
            raise ValueError('protected or labelled review item rejected')
    combined_qa = [json.loads(line) for line in (directory/'combined_visual_qa.jsonl').read_text().splitlines() if line.strip()]
    for row in combined_qa:
        if row.get('correct') is not None:
            raise ValueError('human labels are not machine QA packet inputs')
    qa_inputs, original_rows, seen_inputs = [], [], set()
    items = {(item.get('run_id'), item.get('observation_id')): item for item in inventory.get('items', [])}
    for ref in manifest.get('qa_inputs', []):
        path = safe_path(root, ref['path'])
        if path in seen_inputs:
            raise ValueError('duplicate original QA input path')
        seen_inputs.add(path)
        raw = path.read_bytes()
        if digest(raw) != ref.get('sha256'):
            raise ValueError('original QA input checksum mismatch')
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
        if len(rows) != ref.get('rows'):
            raise ValueError('original QA input row count mismatch')
        for row in rows:
            item = items.get((row.get('run_id'), row.get('observation_id')))
            if (row.get('schema_version') != 'research3-machine-visual-qa/v1'
                    or row.get('correct') is not None
                    or row.get('human_labels_generated', False) is not False
                    or any(value is not False for key, value in row.items() if key.startswith('protected_'))
                    or row.get('reviewer_id', '') != '' or row.get('human_reviewer_id', '') != ''
                    or not isinstance(row.get('attested_by'), str) or not row['attested_by'].strip()
                    or item is None or any(row.get(key) != item.get(key) or not row.get(key) for key in
                        ('task_sha256', 'frame_sha256', 'request_sha256', 'provider_tasks_sha256'))):
                raise ValueError('original QA schema, unlabelled scope or exact item binding mismatch')
        original_rows.extend(rows)
        paths.append(path)
        qa_inputs.append({'path': str(path.relative_to(root)), 'sha256': ref['sha256'], 'rows': len(rows)})
    if manifest.get('qa_inputs') and original_rows != combined_qa:
        raise ValueError('combined QA differs from its explicit original inputs')
    return paths, {'directory': str(directory.relative_to(root)),
                   'packet_manifest_sha256': digest(manifest_path.read_bytes()),
                   'member_sha256': manifest['files'], 'original_qa_inputs': qa_inputs}


def joint_review_paths(root, evidence=None, policy=None, packet_reference=None):
    """Retain explicitly selected reference evidence/policy, never verdict logs."""
    paths, references = [], {}
    if evidence is not None:
        if packet_reference is None:
            raise ValueError('joint review evidence requires its explicit review packet')
        path = safe_path(root, evidence)
        raw = path.read_bytes()
        value = json.loads(raw)
        inventory_path = root/packet_reference['directory']/'inventory.json'
        inventory = json.loads(inventory_path.read_bytes())
        if (value.get('schema_version') != 'research3-joint-review-evidence/v1'
                or value.get('inventory_sha256') != digest(inventory_path.read_bytes())
                or value.get('protected_data_used') is not False
                or value.get('human_labels_generated') is not False):
            raise ValueError('joint reference evidence scope/inventory binding mismatch')
        eligible = {(row['run_id'], row['observation_id']): row for row in inventory['items']
                    if row.get('status') == 'ready_for_human_review'}
        seen = set()
        for row in value.get('items', []):
            key = (row.get('run_id'), row.get('observation_id'))
            item = eligible.get(key)
            if (item is None or key in seen
                    or any(row.get(k) != item.get(k) for k in ('frame_sha256', 'task_sha256'))
                    or row.get('correct') is not None or row.get('human_reviewer_id', '') != ''
                    or 'dimension_verdicts' in row or row.get('verdict') is not None):
                raise ValueError('joint evidence duplicate, label or exact observation mismatch')
            seen.add(key)
            if row.get('evidence_complete') is True:
                run = next((run for run in inventory['runs'] if run.get('run_id') == key[0]), None)
                if run is None:
                    raise ValueError('joint evidence run provenance missing')
                directory = safe_path(root, run['directory'])
                request = json.loads(safe_path(root, directory/'request.json').read_bytes())
                if request.get('map_id') not in NONPROTECTED_MAPS or request.get('protected_test_routes_used') is not False:
                    raise ValueError('joint evidence protected or unidentified request')
                for filename, field in (('request.json', 'request_sha256'), ('runtime_scene.yaml', 'runtime_scene_sha256'),
                                         ('perception_capture/observation_index.json', 'observation_index_sha256')):
                    if digest(safe_path(root, directory/filename).read_bytes()) != row.get(field):
                        raise ValueError('joint evidence source checksum mismatch')
        if seen != set(eligible):
            raise ValueError('joint evidence must retain every selected observation, including gaps')
        paths.append(path)
        references['evidence'] = {'path': str(path.relative_to(root)), 'sha256': digest(raw),
                                  'inventory_sha256': value['inventory_sha256']}
    if policy is not None:
        path = safe_path(root, policy)
        raw = path.read_bytes()
        value = json.loads(raw)
        if (value.get('schema_version') != 'research3-joint-review-policy/v1'
                or value.get('status') not in ('draft', 'approved')
                or value.get('protected_data_used') is not False
                or value.get('human_labels_generated', False) is not False
                or any(key in value for key in ('items', 'events', 'dimension_verdicts', 'verdict', 'correct'))):
            raise ValueError('explicit unlabelled joint review policy required')
        paths.append(path)
        references['policy'] = {'path': str(path.relative_to(root)), 'sha256': digest(raw),
                                'declared_status': value['status'], 'approval_inferred_by_packager': False}
    return paths, references


def collect(root=ROOT, runs=(), max_bytes=1024*1024*1024, environment_report=None,
            include_historical_settings_v1=False, review_packet=None, engineering_evidence=(),
            capture_settings=(), capture_source_snapshots=(), current_capture_plans=(),
            review_evidence=None, review_policy=None):
    root = Path(root).resolve()
    if type(max_bytes) is not int or max_bytes <= 0:
        raise ValueError('positive integer byte budget required')
    selected, run_records = run_paths(root, runs)
    evidence_paths, evidence_references = engineering_evidence_paths(root, engineering_evidence, run_records)
    selected.extend(evidence_paths)
    capture_references = []
    archived_capture_sources = []
    for directory in current_capture_plans:
        selected.extend(current_capture_plan_paths(root, directory))
        capture_references.append({'kind': 'current_capture_plan', 'path': str(safe_path(root, directory).relative_to(root))})
    for directory in capture_settings:
        members = capture_settings_paths(root, directory)
        selected.extend(members)
        capture_references.append({'kind': 'camera_settings', 'path': str(safe_path(root, directory).relative_to(root))})
    for archive in capture_source_snapshots:
        selected.extend(capture_source_archive_paths(root, archive))
        name = str(safe_path(root, archive).relative_to(root))
        capture_references.append({'kind': 'source_archive', 'path': name})
        archived_capture_sources.append((name, verify_archive(root/name)['capture_source_snapshot']))
    packet_reference = None
    if review_packet is not None:
        packet_paths, packet_reference = review_packet_paths(root, review_packet)
        selected.extend(packet_paths)
    joint_paths, joint_references = joint_review_paths(root, review_evidence, review_policy, packet_reference)
    selected.extend(joint_paths)
    environment_reference = None
    if environment_report is not None:
        report_path = safe_path(root, environment_report)
        report = json.loads(report_path.read_text())
        if (report.get('schema_version') != 'research3-engineering-environment/v1'
                or report.get('environment_variables_collected') is not False
                or report.get('private_package_urls_collected') is not False
                or report.get('protected_data_read') is not False):
            raise ValueError('invalid allowlisted environment report')
        selected.append(report_path)
        environment_reference = str(report_path.relative_to(root))
    standard = (standard_paths(root, include_historical_settings_v1=True)
                if include_historical_settings_v1 else standard_paths(root))
    paths = sorted(set(standard + selected))
    for path in paths:
        if path.name != 'manifest.json' or not path.is_relative_to(root/'data'):
            continue
        metadata = json.loads(safe_path(root, path).read_text())
        match = re.fullmatch(r'base-r(\d{3})', path.parent.name)
        number = int(match[1]) if match else 0
        partition = 'development' if 1 <= number <= 10 else 'validation' if 11 <= number <= 14 else None
        expected_map = f'r3geo_base_r{number:03}'
        if (partition is None or metadata.get('partition') != partition
                or metadata.get('map_id') != expected_map
                or metadata.get('base_instruction_id') != path.parent.name):
            raise ValueError('non-protected world manifest identity mismatch')
    files, total = {}, 0
    for path in paths:
        path = safe_path(root, path)
        if not path.is_file():
            raise ValueError('missing explicit snapshot member: ' + str(path.relative_to(root)))
        size = path.stat().st_size
        if total + size > max_bytes:
            raise ValueError('explicit uncompressed byte budget exceeded; choose fewer runs')
        raw = path.read_bytes()
        if len(raw) != size:
            raise ValueError('input changed during capture')
        total += len(raw)
        files[str(path.relative_to(root))] = raw
    for record in run_records:
        record['current_source_matches_request'] = {
            name: digest(files[name]) == expected if name in files else None
            for name, expected in record['requested_source_sha256'].items()}
        record['capture_source_archive_bindings'] = [
            {'archive': name, 'r3_source_pins_match': record['requested_source_sha256'] == snapshot['source_sha256'],
             'provider_source_build_pins_match': record['requested_provider_source_snapshot'] == snapshot.get('provider_source_snapshot')}
            for name, snapshot in archived_capture_sources]
    if any(digest(files[reference['path']]) != reference['sha256'] for reference in evidence_references):
        raise ValueError('engineering evidence changed after validation')
    if any(digest(files[reference['path']]) != reference['sha256'] for reference in joint_references.values()):
        raise ValueError('joint review evidence or policy changed after validation')
    if packet_reference is not None:
        bindings = {packet_reference['directory'] + '/' + name: expected
                    for name, expected in packet_reference['member_sha256'].items()}
        bindings[packet_reference['directory'] + '/packet_manifest.json'] = packet_reference['packet_manifest_sha256']
        bindings.update({entry['path']: entry['sha256'] for entry in packet_reference['original_qa_inputs']})
        if any(digest(files[name]) != expected for name, expected in bindings.items()):
            raise ValueError('review packet or original QA changed after validation')
    manifest = {'schema_version': 'research3-nonprotected-engineering-bundle/v1',
                'scope': 'current source and 51 non-protected original/derivative worlds; explicit selected capture and review-packet evidence only',
                'study_complete': False, 'calibration_validated': False, 'calibration_frozen': False,
                'protected_data_included': False, 'old_human_labels_included': False,
                'original_worlds': 14, 'readable_worlds': 14, 'absence_worlds': 14,
                'development_shape_stress_worlds': 9,
                'stress_condition_versions': {'v1': 4, 'v2': 4, 'v3': 1},
                'review_packet': packet_reference,
                'joint_review': joint_references,
                'selected_runs': run_records,
                'engineering_evidence': evidence_references,
                'explicit_capture_inputs': capture_references,
                'explicit_external_provider_source_archive_included': bool(archived_capture_sources),
                'engineering_camera_settings_versions': ['v2', 'v1'] if include_historical_settings_v1 else ['v2'],
                'environment_report': ({'path': environment_reference,
                    'sha256': digest(files[environment_reference])} if environment_reference else None),
                'historical_execution_reproducibility_complete': False,
                'limitations': ['No R2 source, model binaries, secrets or ROS environment bundled; R1 source/config bytes only in an explicitly selected nested local capture-source archive.',
                    'Engineering camera settings are not confidence calibration.',
                    'Current code may differ from historical run source hashes; comparisons are explicit.',
                    'No arbitrary reports/logs, protected catalogues or old human review files included.',
                    'Known per-run controller/Nav2/Research 3 logs are diagnostic records, not proof of outcome correctness.'],
                'files': {name: {'sha256': digest(raw), 'bytes': len(raw)} for name, raw in sorted(files.items())}}
    # Do not silently snapshot a moving source tree across incompatible revisions.
    if any(digest(safe_path(root, name).read_bytes()) != entry['sha256']
           for name, entry in manifest['files'].items()):
        raise ValueError('source changed while building snapshot; retry after work settles')
    return files, manifest


def verify_archive(path):
    with tarfile.open(path, 'r:gz') as archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        if len(names) != len(set(names)) or any(not member.isfile() for member in members):
            raise ValueError('duplicate or non-file archive members')
        manifest = json.load(archive.extractfile('MANIFEST.json'))
        if set(names) != set(manifest['files']) | {'MANIFEST.json'}:
            raise ValueError('archive inventory mismatch')
        for name, entry in manifest['files'].items():
            if Path(name).is_absolute() or '..' in Path(name).parts:
                raise ValueError('unsafe archive path')
            raw = archive.extractfile(name).read()
            if len(raw) != entry['bytes'] or digest(raw) != entry['sha256']:
                raise ValueError('archive member checksum mismatch')
    return manifest


def write_bundle(output, files, manifest):
    output = Path(output)
    checksum = Path(str(output)+'.sha256')
    if output.exists() or checksum.exists():
        raise FileExistsError('bundle and checksum are create-once')
    expected = {name: {'sha256': digest(raw), 'bytes': len(raw)} for name, raw in files.items()}
    if manifest['files'] != expected or 'MANIFEST.json' in files:
        raise ValueError('manifest does not match payload')
    payload = {**files, 'MANIFEST.json': json.dumps(manifest, sort_keys=True, indent=2).encode()+b'\n'}
    if any(Path(name).is_absolute() or '..' in Path(name).parts for name in payload):
        raise ValueError('unsafe member path')
    with output.open('xb') as stream:
        # Empty gzip filename and zero mtime remove output-name/clock variability.
        with gzip.GzipFile(filename='', mode='wb', fileobj=stream, mtime=0, compresslevel=9) as compressed:
            with tarfile.open(fileobj=compressed, mode='w', format=tarfile.USTAR_FORMAT) as archive:
                for name, raw in sorted(payload.items()):
                    if Path(name).is_absolute() or '..' in Path(name).parts:
                        raise ValueError('unsafe member path')
                    member = tarfile.TarInfo(name)
                    member.size, member.mode, member.mtime = len(raw), 0o644, 0
                    archive.addfile(member, io.BytesIO(raw))
    verify_archive(output)
    value = digest(output.read_bytes())
    with checksum.open('x') as stream:
        stream.write(value+'  '+output.name+'\n')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, action='append', default=[])
    parser.add_argument('--output', type=Path)
    parser.add_argument('--max-bytes', type=int, default=1024*1024*1024)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--environment-report', type=Path,
                        default=ROOT/'reports/engineering_environment_20260911_v2.json')
    parser.add_argument('--include-historical-settings-v1', action='store_true')
    parser.add_argument('--review-packet', type=Path)
    parser.add_argument('--review-evidence', type=Path,
                        help='explicit joint category/association/pose reference artifact bound to packet')
    parser.add_argument('--review-policy', type=Path,
                        help='explicit draft or approved joint review policy; packaging never grants approval')
    parser.add_argument('--engineering-evidence', type=Path, action='append', default=[],
                        help='explicit allowlisted audit, smoke plan/report or attempts journal; repeatable')
    parser.add_argument('--capture-settings', type=Path, action='append', default=[],
                        help='explicit v2 camera freeze directory plus exact 14 profiles; repeatable')
    parser.add_argument('--current-capture-plan', type=Path, action='append', default=[],
                        help='explicit 46-view plan/source snapshot and exact15 profiles; repeatable')
    parser.add_argument('--capture-source-snapshot', type=Path, action='append', default=[],
                        help='explicit locally retained source/config archive; repeatable')
    args = parser.parse_args()
    if not args.dry_run and args.output is None:
        parser.error('--output required unless --dry-run')
    files, manifest = collect(runs=args.run, max_bytes=args.max_bytes,
                              environment_report=args.environment_report,
                              include_historical_settings_v1=args.include_historical_settings_v1,
                              review_packet=args.review_packet,
                              engineering_evidence=args.engineering_evidence,
                              capture_settings=args.capture_settings,
                              capture_source_snapshots=args.capture_source_snapshot,
                              current_capture_plans=args.current_capture_plan,
                              review_evidence=args.review_evidence, review_policy=args.review_policy)
    result = {'members': len(files), 'uncompressed_bytes': sum(map(len, files.values())),
              'study_complete': False, 'selected_runs': len(args.run)}
    if not args.dry_run:
        result['sha256'] = write_bundle(args.output, files, manifest)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
