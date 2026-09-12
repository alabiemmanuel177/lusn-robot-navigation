#!/usr/bin/env python3
"""Default-deny evidence gate, distinct from archive byte integrity.

This checks explicit pinned attestations and complete physical outcome records;
it cannot authenticate a human identity or independently validate an inference
method. Nothing is executed, approved, calibrated, or inferred by this tool.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import runpy

import yaml

HERE = Path(__file__).resolve().parent
ANALYZE = runpy.run_path(str(HERE/'analyze_physical_campaign.py'))['analyze']
DESIGN = runpy.run_path(str(HERE/'check_physical_design_readiness.py'))['check']
VERIFY = runpy.run_path(str(HERE/'verify_physical_release.py'))['verify']
UNIQUE = runpy.run_path(str(HERE/'verify_physical_release.py'))['unique_object']
REQUIRED = ('calibration', 'calibration_validation', 'design', 'design_approval',
            'schedule', 'outcomes', 'heldout_authorization', 'heldout_report',
            'inference', 'inventory')
METRICS = ('navigation_success', 'instruction_completion', 'terminal_identity_correct', 'collision', 'timeout')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def human(value):
    return (value.get('reviewer_type') == 'human' and value.get('status') == 'approved_frozen'
            and isinstance(value.get('approved_by'), str) and bool(value['approved_by'].strip())
            and isinstance(value.get('approved_at_utc'), str) and bool(value['approved_at_utc'].strip()))


def check(root, candidate, *, allow_authorized_heldout_report=False):
    root = Path(root).resolve()
    blockers, verified, loaded = [], {}, {}
    result = {'schema_version': 'research3-scientific-release-readiness/v1',
              'status': 'blocked', 'scientific_release_complete': False,
              'byte_integrity_passed': False, 'protected_report_read': False,
              'human_labels_generated': False, 'approvals_generated': False,
              'inference_generated': False, 'blockers': blockers, 'verified_inputs': verified,
              'limitations': ['Machine checks attestations and consistency, not human identity authenticity or scientific validity of the approved method.',
                              'Engineering captures, graph-only outcomes and archive checksums alone do not satisfy scientific completion.']}
    if candidate.get('schema_version') != 'research3-scientific-release-candidate/v1':
        blockers.append('unsupported_candidate_schema')
        return result
    refs = candidate.get('inputs', {})
    if not isinstance(refs, dict):
        blockers.append('invalid_inputs')
        return result
    for name in REQUIRED:
        if name not in refs:
            blockers.append('missing_input:' + name)

    def read(name, yaml_format=False, raw_only=False):
        ref = refs[name]
        require(isinstance(ref, dict) and set(ref) == {'path', 'sha256'}, 'invalid pinned reference: ' + name)
        rel = ref['path']
        require(isinstance(rel, str) and bool(rel) and not Path(rel).is_absolute()
                and '\\' not in rel and all(p not in ('', '.', '..') for p in rel.split('/')),
                'unsafe reference: ' + name)
        if name not in ('heldout_authorization', 'heldout_report', 'inventory'):
            require(not re.search(r'held[-_]?out|(?:r3geo_base_r|base-r)(?:0(?:1[5-9]|[2-9]\d)|[1-9]\d\d)', rel, re.I),
                    'protected path cannot be a nonprotected prerequisite: ' + name)
        require(isinstance(ref['sha256'], str) and re.fullmatch('[a-f0-9]{64}', ref['sha256']), 'invalid digest: ' + name)
        path = root/rel
        require(not any(part.is_symlink() for part in [path, *list(path.parents)[:len(Path(rel).parts)-1]])
                and path.resolve().is_relative_to(root), 'symlink or outside reference: ' + name)
        raw = path.read_bytes()
        if name == 'heldout_report':
            result['protected_report_read'] = True
        require(hashlib.sha256(raw).hexdigest() == ref['sha256'], 'checksum mismatch: ' + name)
        verified[name] = dict(ref)
        value = raw if raw_only else yaml.safe_load(raw) if yaml_format else json.loads(raw, object_pairs_hook=UNIQUE)
        loaded[name] = value
        return value

    # Read only named nonprotected gate artifacts. The protected report and final
    # inventory members cannot be opened until authorization and prior gates pass.
    for name in ('calibration', 'calibration_validation', 'design', 'design_approval', 'schedule', 'outcomes', 'inference'):
        if name in ('outcomes', 'inference') and 'schedule' not in loaded:
            blockers.append('nonprotected_schedule_not_verified_before:' + name)
            continue
        if name in refs:
            try:
                read(name, yaml_format=name == 'design', raw_only=name == 'calibration')
                if name == 'schedule':
                    schedule = loaded.pop('schedule')
                    systems = sorted({row['system_id'] for row in schedule['episodes']})
                    ANALYZE(schedule, [], baseline=systems[0])
                    loaded['schedule'] = schedule
            except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError, yaml.YAMLError) as exc:
                blockers.append(str(exc))

    def gate(name, fn):
        try:
            fn()
        except (ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
            blockers.append(name + ':' + str(exc))

    def calibration_gate():
        c = loaded['calibration_validation']
        require(c.get('schema_version') == 'research3-physical-calibration-validation/v1'
                and all(c.get(k) is True for k in ('passed', 'frozen', 'human_review_verified'))
                and c.get('protected_labels_used') is False
                and c.get('calibration_sha256') == refs['calibration']['sha256'], 'frozen new-world human calibration validation required')

    def design_gate():
        d, a = loaded['design'], loaded['design_approval']
        require(d.get('status') == 'frozen' and DESIGN(d)['supplied_design_fields_valid_and_complete'], 'complete frozen design required')
        require(a.get('schema_version') == 'research3-physical-execution-approval/v1' and human(a)
                and a.get('authorization_scope') == 'nonprotected_campaign'
                and a.get('manifest_sha256') == refs['schedule']['sha256']
                and all(a.get(k) == refs[k] for k in ('design', 'calibration', 'calibration_validation')),
                'pinned human design approval required')

    def outcomes_gate():
        schedule, outcomes = loaded['schedule'], loaded['outcomes']
        require(isinstance(outcomes, list), 'outcomes must be an explicit JSON list')
        systems = {row['system_id'] for row in schedule['episodes']}
        require(len(systems) >= 2, 'full comparative schedule needs multiple systems')
        analysis = ANALYZE(schedule, outcomes, baseline=sorted(systems)[0])
        require(len(outcomes) == len(schedule['episodes']), 'missing scheduled outcomes')
        for row in outcomes:
            require(row.get('evaluation_mode') == 'physical_live'
                    and row.get('attempted') is True and row.get('dispatched') is True
                    and row.get('infrastructure_failure') is False
                    and all(type(row.get(k)) is bool for k in METRICS), 'partial, unknown, infrastructure or nonphysical outcome')
            require(not ((row['collision'] or row['timeout']) and row['instruction_completion']), 'unsafe outcome contradicts completion')
        result['scheduled_outcomes_verified'] = len(outcomes)
        result['comparative_systems_verified'] = len(analysis['systems']) if 'systems' in analysis else len(systems)

    def inference_gate():
        i, d = loaded['inference'], loaded['design']
        require(i.get('schema_version') == 'research3-physical-final-inference/v1' and human(i)
                and i.get('evaluation_mode') == 'physical_live'
                and i.get('design_sha256') == refs['design']['sha256']
                and i.get('schedule_sha256') == refs['schedule']['sha256']
                and i.get('outcomes_sha256') == refs['outcomes']['sha256']
                and i.get('heldout_report_sha256') == refs['heldout_report']['sha256'], 'approved pinned physical inference required')
        require(all(i.get(k) == d['analysis_proposals'][k] for k in
                    ('primary_contrast', 'multiplicity_policy', 'confirmatory_inference_method')),
                'inference differs from frozen design')
        require(i.get('scheduled_missingness_accounted') is True and i.get('limitations')
                and i.get('results') and i.get('full_schedule_analyzed') is True,
                'complete results, missingness accounting and limitations required')

    for name, fn in (('calibration', calibration_gate), ('design', design_gate),
                     ('comparative_outcomes', outcomes_gate), ('inference', inference_gate)):
        gate(name, fn)
    if not allow_authorized_heldout_report:
        blockers.append('protected_report_access_not_enabled')
    if blockers:
        return result
    try:
        a = read('heldout_authorization')
        require(a.get('schema_version') == 'research3-physical-heldout-authorization/v1' and human(a)
                and a.get('authorization_scope') == 'physical_heldout_report_verification'
                and a.get('heldout_report') == refs['heldout_report']
                and a.get('design_sha256') == refs['design']['sha256']
                and a.get('calibration_sha256') == refs['calibration']['sha256'], 'separate pinned heldout authorization required')
        ids = a.get('scheduled_episode_ids')
        require(isinstance(ids, list) and ids and all(isinstance(x, str) and x for x in ids)
                and len(ids) == len(set(ids)), 'unique authorized heldout schedule IDs required')
        heldout = read('heldout_report')
        result['protected_report_read'] = True
        require(heldout.get('schema_version') == 'research3-physical-heldout-audit/v1'
                and heldout.get('evidence_scope') == 'physical_world_heldout'
                and all(heldout.get(k) is True for k in ('passed', 'complete', 'authorized', 'independent_measurement_verified'))
                and heldout.get('unresolved') == []
                and heldout.get('design_sha256') == refs['design']['sha256']
                and heldout.get('calibration_sha256') == refs['calibration']['sha256']
                and type(heldout.get('scheduled_count')) is int
                and heldout['scheduled_count'] == heldout.get('audited_count') == len(ids)
                and sorted(heldout.get('audited_episode_ids', [])) == sorted(ids),
                'complete authorized physical heldout schedule required')
        inventory = read('inventory')
        members = {r['path']: r['sha256'] for r in inventory.get('files', [])}
        require(all(members.get(ref['path']) == ref['sha256'] for name, ref in refs.items() if name != 'inventory'),
                'final inventory omits pinned scientific evidence')
        integrity = VERIFY(root, inventory, root/refs['inventory']['path'])
        result['byte_integrity_passed'] = integrity['integrity_passed']
        require(integrity['integrity_passed'], 'final inventory integrity failed')
        result.update(status='scientific_release_gates_satisfied', scientific_release_complete=True)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        blockers.append('authorized_release_gate:' + str(exc))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True, help='explicit final staging directory')
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--allow-authorized-heldout-report', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = check(args.root, json.loads(args.candidate.read_bytes(), object_pairs_hook=UNIQUE),
                   allow_authorized_heldout_report=args.allow_authorized_heldout_report)
    text = json.dumps(result, indent=2, sort_keys=True) + '\n'
    if args.output:
        with args.output.open('x') as stream:
            stream.write(text)
    print(text, end='')
    raise SystemExit(0 if result['scientific_release_complete'] else 1)


if __name__ == '__main__':
    main()
