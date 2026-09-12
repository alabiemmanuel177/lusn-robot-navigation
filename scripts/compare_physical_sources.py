#!/usr/bin/env python3
"""Compare explicit archived/current inputs; never grant source equivalence."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    'scripts/run_physical_episode.py',
    'src/language_nav/benchmark/physical_catalog.py',
    'ros_ws/src/language_nav_runtime/language_nav_runtime/nav2_adapter.py',
    'ros_ws/src/language_nav_planner/language_nav_planner/node.py',
    'ros_ws/src/language_nav_runtime/language_nav_runtime/semantic_routes.py',
)
PROFILE_PATTERN = r'(?:reports/(?:engineering_camera_settings_v[0-9]+|stationary_capture_plan_v1)/profiles/base-r0(?:0[1-9]|1[0-4])\.yaml|configs/physical_dev10_camera_profile_v1\.yaml)'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def file_digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def relative(name):
    if (not isinstance(name, str) or not name or Path(name).is_absolute()
            or str(Path(name)) != name or any(p.startswith('.') for p in Path(name).parts)
            or any(int(number) >= 15 for number in re.findall(r'base[-_]r(\d+)', name))
            or re.search(r'(^|/)test_', name)):
        raise ValueError('unsafe or protected input path')
    return name


def compare(archive_path, spec, root=ROOT):
    root = Path(root).resolve()
    if spec.get('schema_version') != 'research3-source-comparison-request/v1':
        raise ValueError('unsupported comparison request')
    archive_hash = file_digest(archive_path)
    if archive_hash != spec.get('archive_sha256'):
        raise ValueError('baseline archive checksum mismatch')
    current_hashes, selected = {}, {}

    def current(name):
        path = root / relative(name)
        if (not path.resolve().is_relative_to(root) or not path.is_file()
                or any((root / Path(*Path(name).parts[:n])).is_symlink()
                       for n in range(1, len(Path(name).parts) + 1))):
            raise ValueError('current input missing, symlinked or outside workspace')
        raw = path.read_bytes()
        current_hashes[name] = digest(raw)
        return raw

    with tarfile.open(archive_path, 'r:gz') as archive:
        entries = archive.getmembers()
        names = [entry.name for entry in entries]
        if len(names) != len(set(names)):
            raise ValueError('duplicate archive member')
        by_name = {entry.name: entry for entry in entries}

        def raw_member(name):
            entry = by_name.get(relative(name))
            if entry is None or not entry.isfile() or not 0 <= entry.size <= 16 * 1024 * 1024:
                raise ValueError('missing, nonregular or oversized selected archive member')
            return archive.extractfile(entry).read()

        manifest_raw = raw_member('MANIFEST.json')
        manifest = json.loads(manifest_raw)
        if (manifest.get('schema_version') != 'research3-nonprotected-engineering-bundle/v1'
                or manifest.get('protected_data_included') is not False):
            raise ValueError('verified nonprotected engineering archive required')

        cache = {}
        def baseline(name):
            relative(name)
            if name in cache:
                return cache[name]
            pin = manifest.get('files', {}).get(name)
            if pin is None:
                raise ValueError('selected member not manifest-pinned')
            raw = raw_member(name)
            if digest(raw) != pin['sha256'] or len(raw) != pin['bytes']:
                raise ValueError('selected member checksum/size mismatch')
            selected[name] = digest(raw)
            cache[name] = raw
            return raw

        # Two forward-ordered read batches avoid repeated gzip rewinds. Validate
        # every request's nonprotected identity before preloading any scene.
        request_names = [relative(row['request_member']) for row in spec.get('runs', [])]
        if any(not re.fullmatch(r'reports/physical_live_episodes/[A-Za-z0-9_-]+/request.json', name)
               for name in request_names):
            raise ValueError('explicit owned capture request required')
        for name in sorted(set((*SOURCES, *request_names)), key=lambda name: by_name[name].offset_data):
            baseline(name)
        additional = set()
        for record in spec.get('runs', []):
            request_name = record['request_member']
            request = json.loads(baseline(request_name))
            match = re.fullmatch(r'r3geo_base_r(\d{3})', request.get('map_id', ''))
            number = int(match[1]) if match else 0
            partition = 'development' if 1 <= number <= 10 else 'validation' if 11 <= number <= 14 else None
            if (partition is None or request.get('partition') != partition
                    or request.get('protected_test_routes_used') is not False):
                raise ValueError('non-protected request required before any scene/media access')
            if record.get('scene_member'):
                if record['scene_member'] != str(Path(request_name).parent / 'runtime_scene.yaml'):
                    raise ValueError('only selected run retained runtime scene may be compared')
                additional.add(record['scene_member'])
            if record.get('profile_member'):
                if not re.fullmatch(PROFILE_PATTERN, record['profile_member']):
                    raise ValueError('explicit nonprotected frozen camera profile required')
                additional.add(record['profile_member'])
        for name in sorted(additional, key=lambda name: by_name[name].offset_data):
            baseline(name)

        sources = []
        for name in SOURCES:
            old, new = baseline(name), current(name)
            sources.append({'path': name, 'baseline_sha256': digest(old), 'current_sha256': digest(new),
                            'changed': old != new,
                            'capture_request_pin_expected': name != SOURCES[-1]})
        runs, gaps = [], []
        seen = set()
        for record in spec.get('runs', []):
            name = relative(record['request_member'])
            if not re.fullmatch(r'reports/physical_live_episodes/[A-Za-z0-9_-]+/request.json', name):
                raise ValueError('explicit owned capture request required')
            old_request_raw = baseline(name)
            request = json.loads(old_request_raw)
            match = re.fullmatch(r'r3geo_base_r(\d{3})', request.get('map_id', ''))
            index = int(match[1]) if match else 0
            partition = 'development' if 1 <= index <= 10 else 'validation' if 11 <= index <= 14 else None
            if (partition is None or request.get('partition') != partition
                    or request.get('protected_test_routes_used') is not False):
                raise ValueError('non-protected request required before any scene/media access')
            if name in seen:
                raise ValueError('duplicate capture request')
            seen.add(name)
            if record.get('current_request_path', name) != name:
                raise ValueError('historical request path must not be remapped')
            new_request_raw = current(name)
            result = {'request_member': name, 'map_id': request['map_id'], 'partition': partition,
                      'request_unchanged': old_request_raw == new_request_raw,
                      'camera_horizontal_fov': request.get('camera_horizontal_fov'),
                      'camera_color_tolerance': request.get('camera_color_tolerance'),
                      'capture_source_sha256': request.get('source_sha256', {}),
                      'source_archive_matches_capture': {
                          source['path']: request.get('source_sha256', {}).get(source['path']) == source['baseline_sha256']
                          if source['path'] in request.get('source_sha256', {}) else None for source in sources}}
            for role, pin_name in [('scene', 'runtime_scene_sha256'), ('profile', 'camera_profile_sha256')]:
                member = record.get(role + '_member')
                if not member:
                    gaps.append('missing_explicit_' + role + ':' + name)
                    continue
                if role == 'scene' and member != str(Path(name).parent / 'runtime_scene.yaml'):
                    raise ValueError('only the selected run retained runtime scene may be compared')
                if role == 'profile' and not re.fullmatch(PROFILE_PATTERN, member):
                    raise ValueError('explicit nonprotected frozen camera profile required')
                current_name = record.get('current_' + role + '_path', member)
                if current_name != member:
                    raise ValueError('historical scene/profile path must not be remapped')
                old, new = baseline(member), current(current_name)
                if digest(old) != request.get(pin_name):
                    raise ValueError('selected ' + role + ' does not match captured request')
                result[role] = {'baseline_sha256': digest(old), 'current_sha256': digest(new),
                                'unchanged': old == new}
            runs.append(result)
        environment = None
        old_env_name, new_env_name = spec.get('baseline_environment_member'), spec.get('current_environment_path')
        if old_env_name and new_env_name:
            if not all(re.fullmatch(r'reports/engineering_environment_[A-Za-z0-9_-]+\.json', n)
                       for n in (old_env_name, new_env_name)):
                raise ValueError('explicit engineering environment reports required')
            old_env, new_env = json.loads(baseline(old_env_name)), json.loads(current(new_env_name))
            if any(env.get('schema_version') != 'research3-engineering-environment/v1' for env in (old_env, new_env)):
                raise ValueError('unsupported environment provenance report')
            provider = lambda env: {key: value for group in ('source_files', 'installed_files')
                                   for key, value in env.get(group, {}).items() if 'research3_landmark_bridge' in key}
            old_provider, new_provider = provider(old_env), provider(new_env)
            provider_hashes = lambda records: {key: row.get('sha256') for key, row in records.items()}
            environment = {'baseline_captured_at': old_env.get('captured_at_utc'),
                           'current_captured_at': new_env.get('captured_at_utc'),
                           'dependencies_unchanged': all(old_env.get(key) == new_env.get(key)
                               for key in ('python', 'python_packages', 'ros_packages')),
                           'baseline_provider_hashes': provider_hashes(old_provider),
                           'current_provider_hashes': provider_hashes(new_provider),
                           'provider_hashes_unchanged': provider_hashes(old_provider) == provider_hashes(new_provider),
                           'live_environment_reverified': False}
            if not old_provider or not new_provider or not any(provider_hashes(old_provider).values()):
                gaps.append('provider_provenance_incomplete')
            if any(not env.get(key) for env in (old_env, new_env)
                   for key in ('python', 'python_packages', 'ros_packages')):
                gaps.append('dependency_provenance_incomplete')
        else:
            gaps.append('explicit_baseline_and_current_environment_reports_required')
    if file_digest(archive_path) != archive_hash:
        raise ValueError('baseline archive changed during comparison')
    for name, expected in current_hashes.items():
        if file_digest(root / name) != expected:
            raise ValueError('current input changed during comparison')
    unchanged = bool(runs) and all(row['request_unchanged'] and all(row.get(role, {}).get('unchanged')
                                  for role in ('scene', 'profile')) for row in runs)
    reconstruction = {name: {'matching_runs': sum(row['source_archive_matches_capture'][name] is True for row in runs),
                             'different_version_runs': sum(row['source_archive_matches_capture'][name] is False for row in runs),
                             'unrecorded_runs': sum(row['source_archive_matches_capture'][name] is None for row in runs)}
                      for name in SOURCES}
    if any(row['different_version_runs'] for row in reconstruction.values()):
        gaps.append('baseline_archive_does_not_reconstruct_all_capture_source_versions')
    if any(row['unrecorded_runs'] for row in reconstruction.values()):
        gaps.append('capture_request_source_provenance_incomplete_for_compared_files')
    return {'schema_version': 'research3-physical-source-comparison/v1',
            'status': 'blocked_for_equivalence_approval', 'equivalence_approved': False,
            'deployment_eligible': False, 'human_labels_generated': False, 'study_complete': False,
            'protected_data_used': False, 'archive_sha256': archive_hash,
            'archive_manifest_sha256': digest(manifest_raw), 'selected_archive_members': selected,
            'current_file_sha256': current_hashes, 'source_files': sources,
            'source_files_changed': [row['path'] for row in sources if row['changed']],
            'runs': runs, 'environment_comparison': environment,
            'capture_source_reconstruction': reconstruction,
            'capture_evidence_validity': ('selected_bindings_unchanged_full_media_review_not_reaudited' if unchanged
                else 'selected_bindings_changed_or_incomplete' if runs else 'not_assessed_no_explicit_runs'),
            'blockers': sorted(set(gaps + ['differential_nonprotected_behavior_evidence_required',
                'explicit_external_equivalence_approval_required', 'deployment_gate_remains_exact_source_only'])),
            'limitations': ['No historical request hashes are rewritten.',
                'semantic_routes.py archive presence is not proof it was capture-request-pinned or executed.',
                'Environment report hashes compare recorded metadata, not fresh live dependency measurements.',
                'Existing RGB/claim judgments remain historical evidence; source equality is not calibration efficacy.',
                'No map, scene, profile, heldout world or error-prevalence transfer is authorized.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = compare(args.archive, json.loads(args.request.read_text()), args.root)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    raise SystemExit(2)


if __name__ == '__main__':
    main()
