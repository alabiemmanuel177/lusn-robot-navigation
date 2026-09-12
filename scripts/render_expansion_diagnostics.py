#!/usr/bin/env python3
"""Render the 80 diagnostic candidates plus matched controls and build the asset-review packet.

`run` executes serial, resource-guarded stationary renders through the owned
runner: every candidate world at its bound view-0 pose, plus one control render
of the unmodified source world per map/class. `assemble` decodes the retained
frames, measures what the added visual covers, writes side-by-side PNGs, an
index page, a manifest and a decision template. `validate-decision` checks a
returned human decision file. Nothing here labels detections or authorizes
diagnostic collection; the human rendered-asset decision does that per candidate.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from expansion_rendered_checks import (decode_frame, palette_key, occluder_checks, sphere_checks,  # noqa: E402
                                       control_drift, composite, project_polygon)

RUNNER = ROOT / 'scripts/run_physical_episode.py'
RUNS = ROOT / 'reports/physical_live_episodes'
WORLDS = ROOT / 'data/physical_worlds_readable_v1'
PROFILES = ROOT / 'reports/fresh_current_capture_20260911_v1/profiles'
ASSETS = {'occluder': ROOT / 'reports/calibration_expansion_occluder_assets_20260912_v1',
          'sphere': ROOT / 'reports/calibration_expansion_distractor_assets_20260912_v1'}
ASSET_DIR = re.compile(r'calibration_expansion_(occluder|distractor)_assets_\d{8}_v(\d+)')


def asset_tag(folder):
    match = ASSET_DIR.fullmatch(Path(folder).name)
    if not match or Path(folder).resolve().parent != (ROOT / 'reports').resolve():
        raise ValueError('diagnostic assets must be a pinned reports directory')
    return 'v' + match[2]
AUDIT_FILE = {'occluder': 'occluder_candidate_audit.json', 'sphere': 'diagnostic_asset_audit.json'}
AUDIT_FILE_V2 = 'diagnostic_candidate_audit_v2.json'


def audit_file(treatment, tag):
    return AUDIT_FILE[treatment] if tag == 'v1' else AUDIT_FILE_V2
CANDIDATE = re.compile(r'expansion-v1-r(0\d\d)-(chair|doorway|laboratory_entrance|office_entrance)-s1-view0')
RUN_PREFIX = 'expansion-diag-render-v1'
DECISION_SCHEMA = 'research3-expansion-diagnostic-asset-decision/v1'
CONTEXT_FRAME = 'context_capture/frame-000.json'


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha_file(path) -> str:
    return sha(Path(path).read_bytes())


def write_once(path, payload):
    with Path(path).open('x') as stream:
        json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def candidates(assets=None):
    rows = []
    for treatment, folder in (assets or ASSETS).items():
        folder = Path(folder)
        tag = asset_tag(folder)
        index = json.loads((folder / 'index.json').read_bytes())
        ids = [row['candidate_id'] for row in index['results']]
        if len(ids) != 40 or len(set(ids)) != 40:
            raise ValueError('complete 40-candidate panel required')
        for candidate_id in ids:
            match = CANDIDATE.fullmatch(candidate_id)
            if not match:
                raise ValueError('unexpected candidate identity')
            audit = json.loads((folder / candidate_id / audit_file(treatment, tag)).read_bytes())
            rows.append(dict(candidate_id=candidate_id, treatment=treatment, assets_tag=tag, map_index=match[1],
                             category=match[2], directory=folder / candidate_id, audit=audit,
                             entity_id=audit['entity_id'], capture_pose=audit['capture_pose']))
    return rows


def render_jobs(rows, prefix=RUN_PREFIX):
    """Candidate renders plus one control per map/class at the identical pose."""
    jobs, controls = [], {}
    for row in rows:
        key = (row['map_index'], row['category'])
        pose = row['capture_pose']
        if key in controls and controls[key]['capture_pose'] != pose:
            raise ValueError('candidates sharing a view disagree on pose')
        controls.setdefault(key, dict(run_id=f'{prefix}-control-r{key[0]}-{key[1]}', kind='control',
                                      map_index=key[0], category=key[1], capture_pose=pose, derivative=None,
                                      candidate_id=None))
        jobs.append(dict(run_id=f'{prefix}-{row["treatment"]}-{row["assets_tag"]}-r{row["map_index"]}-{row["category"]}',
                         kind=row['treatment'], assets_tag=row['assets_tag'], map_index=row['map_index'],
                         category=row['category'], capture_pose=pose, derivative=str(row['directory']),
                         candidate_id=row['candidate_id']))
    return list(controls.values()) + jobs


def command(job, domain, timeout):
    base = 'base-r' + job['map_index']
    argv = ['nice', '-n', '15', 'python3', str(RUNNER), '--world', str(WORLDS / base),
            '--variant-id', f'{base}-truthful_original-s0', '--run-id', job['run_id'],
            '--ros-domain-id', str(domain), '--simulation-seed', '1', '--timeout', str(timeout),
            '--allow-coexistence-trial', '--capture-only', '--capture-frame-budget', '1',
            '--capture-pose', repr(float(job['capture_pose']['x'])), repr(float(job['capture_pose']['y'])),
            repr(float(job['capture_pose']['yaw'])),
            '--capture-target-category', job['category'],
            '--camera-profile', str(PROFILES / f'{base}.yaml'), '--camera-horizontal-fov', '2.0']
    if job['derivative']:
        argv += ['--diagnostic-derivative', job['derivative']]
    return argv


def run_owned(argv, log):
    process = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT, start_new_session=True)
    try:
        return process.wait(timeout=420)
    except BaseException:
        for sig, grace in ((signal.SIGINT, 30), (signal.SIGTERM, 15), (signal.SIGKILL, 5)):
            if process.poll() is not None:
                break
            os.killpg(process.pid, sig)
            try:
                process.wait(timeout=grace)
                break
            except subprocess.TimeoutExpired:
                continue
        raise


def run(args):
    from language_nav.live_resources import require_research2_idle, coexistence_headroom
    from language_nav.campaign_authorization import exclusive_campaign_runtime
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    if not args.run_prefix.startswith('expansion-diag-'):
        raise ValueError('render run IDs must stay in the expansion-diag- namespace')
    assets = {'occluder': args.occluder_assets or ASSETS['occluder'], 'sphere': args.sphere_assets or ASSETS['sphere']}
    jobs = render_jobs(candidates(assets), args.run_prefix)
    reused_controls = {}
    if args.controls_from:
        prior = json.loads((Path(args.controls_from) / 'jobs.json').read_bytes())
        if prior['run_prefix'] != args.run_prefix:
            raise ValueError('reused controls must share the run prefix')
        reused_controls = {run_id: record for run_id, record in load_renders(args.controls_from).items()
                           if record['kind'] == 'control' and record['exit_code'] == 0 and record['context_frame_present']}
        jobs = [job for job in jobs if job['kind'] != 'control' or job['run_id'] not in reused_controls]
    if args.only:
        jobs = [job for job in jobs if job['run_id'] in set(args.only)]
    if args.limit:
        jobs = jobs[:args.limit]
    write_once(output / 'jobs.json', dict(schema_version='research3-expansion-diagnostic-render-jobs/v1', run_prefix=args.run_prefix,
               assets={key: str(Path(value).resolve().relative_to(ROOT)) for key, value in assets.items()},
               controls_from=str(Path(args.controls_from).resolve().relative_to(ROOT)) if args.controls_from else None,
               reused_controls=sorted(reused_controls),
               jobs=[dict(job, argv=command(job, args.ros_domain_id, args.timeout)) for job in jobs],
               execution_authorized_by_this_run=False, human_labels_generated=False))
    with exclusive_campaign_runtime(), (output / 'renders.jsonl').open('x') as ledger:
        for job in jobs:
            require_research2_idle()
            headroom = coexistence_headroom()
            argv = command(job, args.ros_domain_id, args.timeout)
            with (output / f'{job["run_id"]}.log').open('x') as log:
                started = dt.datetime.now(dt.timezone.utc).isoformat()
                code = run_owned(argv, log)
            run_dir = RUNS / job['run_id']
            record = dict(job, exit_code=code, started_at_utc=started,
                          finished_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                          headroom_before=headroom, run_directory=str(run_dir),
                          context_frame_present=(run_dir / CONTEXT_FRAME).exists(),
                          perception_frame_present=(run_dir / 'perception_capture/frame-000.json').exists(),
                          request_sha256=sha_file(run_dir / 'request.json') if (run_dir / 'request.json').exists() else None,
                          failure=(json.loads((run_dir / 'failure.json').read_bytes()) if (run_dir / 'failure.json').exists() else None))
            ledger.write(json.dumps(record, sort_keys=True) + '\n')
            ledger.flush()
            os.fsync(ledger.fileno())
            print(json.dumps({k: record[k] for k in ('run_id', 'exit_code', 'context_frame_present', 'perception_frame_present')}), flush=True)


def load_renders(directory):
    records = [json.loads(line) for line in (Path(directory) / 'renders.jsonl').read_text().splitlines() if line.strip()]
    by_id = {}
    for record in records:
        if record['run_id'] in by_id:
            raise ValueError('duplicate render record')
        by_id[record['run_id']] = record
    return by_id


def scene_target_rgb(map_index, entity_id):
    profile = yaml.safe_load((PROFILES / f'base-r{map_index}.yaml').read_text())
    scene = yaml.safe_load((WORLDS / f'base-r{map_index}' / 'landmark_scene.yaml').read_text())
    entity = next(row for row in scene['entities'] if row['entity_id'] == entity_id)
    return profile['camera_palette'][palette_key(entity['category'], entity.get('attributes'))], entity


def pilot_frame(map_index, category):
    pilot_category = 'laboratory_entrance' if category == 'doorway' else category
    return RUNS / f'r3-current-v1-r{map_index}-{pilot_category}' / 'perception_capture/frame-000.json'


def assemble(args):
    renders = load_renders(args.renders)
    jobs_record = json.loads((Path(args.renders) / 'jobs.json').read_bytes())
    prefix = jobs_record['run_prefix']
    if jobs_record.get('controls_from'):
        for run_id, record in load_renders(ROOT / jobs_record['controls_from']).items():
            if record['kind'] == 'control' and run_id in jobs_record['reused_controls']:
                renders.setdefault(run_id, record)
    assets = {key: ROOT / value for key, value in jobs_record['assets'].items()}
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / 'images').mkdir()
    rows = []
    for row in candidates(assets):
        candidate_run = renders.get(f'{prefix}-{row["treatment"]}-{row["assets_tag"]}-r{row["map_index"]}-{row["category"]}')
        control_run = renders.get(f'{prefix}-control-r{row["map_index"]}-{row["category"]}')
        result = dict(candidate_key=f"{row['treatment']}/{row['candidate_id']}", candidate_id=row['candidate_id'], treatment=row['treatment'],
                      assets_directory=str(row['directory'].parent.relative_to(ROOT)), assets_tag=row['assets_tag'], map_id='r3geo_base_r' + row['map_index'],
                      category=row['category'], entity_id=row['entity_id'], capture_pose=row['capture_pose'],
                      candidate_world_sdf_sha256=row['audit']['derivative_sha256']['world.sdf'],
                      audit_sha256=sha_file(row['directory'] / audit_file(row['treatment'], row['assets_tag'])),
                      analytic_occluded_fraction=row['audit'].get('analytic_occluded_fraction'),
                      rendered=False, rendered_checks=None, rendered_preflight_passed=False, issues=[])
        for name, record in (('candidate', candidate_run), ('control', control_run)):
            if record is None:
                result['issues'].append(f'{name}_render_missing')
            elif record['exit_code'] != 0 or not record['context_frame_present']:
                result['issues'].append(f'{name}_render_failed')
        if result['issues']:
            rows.append(result)
            continue
        candidate_dir, control_dir = Path(candidate_run['run_directory']), Path(control_run['run_directory'])
        candidate_request = json.loads((candidate_dir / 'request.json').read_bytes())
        control_request = json.loads((control_dir / 'request.json').read_bytes())
        if (candidate_request.get('capture_pose') != control_request.get('capture_pose')
                or candidate_request.get('diagnostic_derivative', {}).get('world_sdf_sha256') != result['candidate_world_sdf_sha256']
                or candidate_request.get('camera_profile_sha256') != control_request.get('camera_profile_sha256')
                or candidate_request.get('camera_horizontal_fov') != 2.0 or control_request.get('camera_horizontal_fov') != 2.0):
            result['issues'].append('candidate_control_binding_mismatch')
            rows.append(result)
            continue
        candidate_image, candidate_info = decode_frame(candidate_dir / CONTEXT_FRAME)
        control_image, control_info = decode_frame(control_dir / CONTEXT_FRAME)
        target_rgb, entity = scene_target_rgb(row['map_index'], row['entity_id'])
        polygon_pixels = None
        if row['treatment'] == 'occluder':
            checks, masks = occluder_checks(control_image, candidate_image,
                                            polygon_normalized=row['audit']['polygon_normalized_camera'],
                                            camera_info=control_info['camera_info'], target_rgb=target_rgb)
            polygon_pixels = project_polygon(row['audit']['polygon_normalized_camera'], control_info['camera_info'])
        else:
            checks, masks = sphere_checks(control_image, candidate_image, target_rgb=target_rgb)
        drift = None
        pilot = pilot_frame(row['map_index'], row['category'])
        if pilot.exists():
            pilot_image, _ = decode_frame(pilot)
            drift = dict(control_drift(control_image, pilot_image), pilot_frame=str(pilot.relative_to(ROOT)),
                         pilot_frame_sha256=sha_file(pilot))
        image_name = f'{row["treatment"]}-{row["candidate_id"]}.png'
        sheet = composite(control_image, candidate_image, masks, polygon_pixels=polygon_pixels,
                          title=f'{row["candidate_id"]} [{row["treatment"]}]')
        with (output / 'images' / image_name).open('xb') as stream:
            sheet.save(stream, format='PNG')
        for name, image in (('control', control_image), ('candidate', candidate_image)):
            from PIL import Image
            with (output / 'images' / f'{row["treatment"]}-{row["candidate_id"]}.{name}.png').open('xb') as stream:
                Image.fromarray(image).save(stream, format='PNG')
        result.update(rendered=True, rendered_checks=checks, rendered_preflight_passed=bool(checks['passed']),
                      target_palette_rgb=list(target_rgb), target_attributes=entity.get('attributes', {}),
                      control_pilot_drift=drift, composite_image=f'images/{image_name}',
                      candidate_run=dict(run_id=candidate_run['run_id'], request_sha256=candidate_run['request_sha256'],
                                         context_frame_sha256=sha_file(candidate_dir / CONTEXT_FRAME),
                                         rgb_sha256=candidate_info['rgb']['sha256']),
                      control_run=dict(run_id=control_run['run_id'], request_sha256=control_run['request_sha256'],
                                       context_frame_sha256=sha_file(control_dir / CONTEXT_FRAME),
                                       rgb_sha256=control_info['rgb']['sha256']))
        rows.append(result)
    summary = dict(schema_version='research3-expansion-diagnostic-render-audit/v1',
                   candidates=len(rows), rendered=sum(r['rendered'] for r in rows),
                   rendered_preflight_passed=sum(r['rendered_preflight_passed'] for r in rows),
                   occluder_passed=sum(r['rendered_preflight_passed'] for r in rows if r['treatment'] == 'occluder'),
                   sphere_passed=sum(r['rendered_preflight_passed'] for r in rows if r['treatment'] == 'sphere'),
                   all_rendered_checks_passed=all(r['rendered_preflight_passed'] for r in rows),
                   thresholds=dict(occluder_box_coverage_tolerance=.06, sphere_min_target_retained=.97,
                                   mask_tolerance=12, change_tolerance=8),
                   measurement_scope='same-session control versus candidate pixel comparison at the bound pose; agent preflight, not human acceptance',
                   occluder_definition='20% of the projected convex silhouette of the provider marker box, not of the whole semantic object',
                   human_approval_present=False, execution_authorized=False, human_labels_generated=False,
                   rows=rows)
    write_once(output / 'rendered_audit.json', summary)
    (output / 'index.html').write_text(index_html(summary))
    (output / 'README.md').write_text(readme(summary))
    template = dict(schema_version=DECISION_SCHEMA, packet_directory=str(output.relative_to(ROOT)),
                    packet_sha256=None, reviewer_name='', reviewer_role='Researcher', reviewed_at='',
                    occluder_definition_accepted=None,
                    decisions={r['candidate_key']: dict(decision=None, note='') for r in rows},
                    human_labels_generated=False, grants_collection_by_itself=False,
                    instructions='Set each decision to accept, revise or reject after inspecting images/. '
                                 'Set occluder_definition_accepted to true or false. Fill packet_sha256 from manifest.json.sha256.')
    write_once(output / 'DECISIONS.template.json', template)
    manifest = dict(schema_version='research3-expansion-diagnostic-render-packet/v1',
                    files={str(path.relative_to(output)): sha_file(path)
                           for path in sorted(output.rglob('*')) if path.is_file()},
                    human_labels_generated=False, execution_authorized=False)
    write_once(output / 'manifest.json', manifest)
    digest = sha_file(output / 'manifest.json')
    (output / 'manifest.json.sha256').write_text(digest + '\n')
    archive = output.with_suffix('.zip')
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(output.rglob('*')):
            if path.is_file():
                zipped.write(path, str(Path(output.name) / path.relative_to(output)))
    print(json.dumps({k: v for k, v in summary.items() if k != 'rows'} | dict(packet_sha256=digest, archive=str(archive))))


def index_html(summary):
    cards = []
    for row in summary['rows']:
        checks = row['rendered_checks'] or {}
        status = 'PASS' if row['rendered_preflight_passed'] else ('NOT RENDERED' if not row['rendered'] else 'CHECK')
        details = ''.join(f'<li>{html.escape(k)}: {html.escape(json.dumps(v))}</li>' for k, v in checks.items())
        issues = ''.join(f'<li>{html.escape(i)}</li>' for i in row['issues'])
        image = f'<img src="{html.escape(row["composite_image"])}" loading="lazy">' if row.get('composite_image') else ''
        cards.append(f'''<section class="card {status.lower().replace(' ', '-')}">
<h2>{html.escape(row['candidate_key'])} <small>{html.escape(row['treatment'])} · {html.escape(row['category'])} · {html.escape(row['entity_id'])}</small> <span class="status">{status}</span></h2>
{image}
<details><summary>agent preflight measurements (not a verdict)</summary><ul>{details}{issues}</ul>
<p>analytic occluded fraction: {html.escape(json.dumps(row.get('analytic_occluded_fraction')))} · candidate world.sdf sha256 {html.escape(row['candidate_world_sdf_sha256'][:16])}…</p></details>
</section>''')
    return f'''<!doctype html><html><head><meta charset="utf-8"><title>Diagnostic asset review</title>
<style>body{{font-family:system-ui;margin:1.5rem;background:#181818;color:#eee}}.card{{border:1px solid #444;padding:.75rem;margin-bottom:1rem}}
img{{max-width:100%;image-rendering:pixelated}}.status{{float:right;padding:.1rem .5rem;border-radius:.3rem;background:#555}}
.pass .status{{background:#2a6}}.check .status{{background:#c83}}.not-rendered .status{{background:#a33}}small{{color:#aaa;font-weight:normal}}</style></head>
<body><h1>Rendered diagnostic candidates: {summary['candidates']} ({summary['rendered']} rendered)</h1>
<p>Left image: same-session control render of the unmodified source world. Middle: candidate render with overlays
(yellow: projected provider marker box silhouette for occluders; cyan: target palette pixels; magenta: sphere pixels).
Right: pixels that changed between control and candidate. The occluder definition is 20% of the projected provider
marker box silhouette, not 20% of the whole chair or entrance. Agent measurements are preflight evidence only; your
accept/revise/reject decision per candidate goes in DECISIONS.template.json.</p>
{''.join(cards)}</body></html>'''


def readme(summary):
    return f'''# Diagnostic asset review packet

Rendered candidates: {summary['rendered']} of {summary['candidates']}. Agent preflight passed:
{summary['rendered_preflight_passed']} ({summary['occluder_passed']} occluders, {summary['sphere_passed']} spheres).

Open `index.html` and inspect every card. Each shows the control render of the unmodified
world, the candidate render with overlays, and the changed-pixel map at the identical camera
pose used by the bound pilot view. `rendered_audit.json` holds the pixel measurements.

The occluder definition is 20% of the projected convex silhouette of the provider marker
box, not 20% of the whole semantic object. Accepting the definition is a separate field.

To decide: copy `DECISIONS.template.json` to `DECISIONS.json`, set every `decision` to
`accept`, `revise` or `reject`, set `occluder_definition_accepted`, fill your name, role and
an ISO-8601 `reviewed_at`, and set `packet_sha256` to the value in `manifest.json.sha256`.
Return `DECISIONS.json`. This decision authorizes diagnostic collection of accepted
candidates only; it generates no labels and grants no primary or protected execution.
'''


def validate_asset_decision(path, *, candidate_id=None, treatment=None):
    path = Path(path)
    raw = path.read_bytes()
    decision = json.loads(raw)
    if decision.get('schema_version') != DECISION_SCHEMA or decision.get('human_labels_generated') is not False:
        raise ValueError('invalid diagnostic asset decision schema')
    packet = ROOT / decision['packet_directory']
    if not packet.resolve().is_relative_to((ROOT / 'reports').resolve()):
        raise ValueError('packet directory must be a repository report')
    if sha_file(packet / 'manifest.json') != decision.get('packet_sha256'):
        raise ValueError('decision is not bound to the rendered packet')
    manifest = json.loads((packet / 'manifest.json').read_bytes())
    for name, digest in manifest['files'].items():
        if sha_file(packet / name) != digest:
            raise ValueError(f'packet file changed after review: {name}')
    if not decision.get('reviewer_name', '').strip() or decision.get('reviewer_role') not in ('Researcher', 'Supervisor'):
        raise ValueError('named human reviewer required')
    dt.datetime.fromisoformat(decision['reviewed_at'])
    audit = json.loads((packet / 'rendered_audit.json').read_bytes())
    expected = {row['candidate_key'] for row in audit['rows']}
    if set(decision.get('decisions', {})) != expected:
        raise ValueError('decision must cover exactly the rendered candidates')
    if any(row.get('decision') not in ('accept', 'revise', 'reject') for row in decision['decisions'].values()):
        raise ValueError('every candidate needs accept, revise or reject')
    if decision.get('occluder_definition_accepted') not in (True, False):
        raise ValueError('occluder definition acceptance must be explicit')
    if candidate_id is not None:
        key = f'{treatment}/{candidate_id}'
        rendered = next((row for row in audit['rows'] if row['candidate_key'] == key), None)
        if rendered is None or not rendered['rendered']:
            raise ValueError('candidate was not rendered for review')
        if decision['decisions'][key]['decision'] != 'accept':
            raise PermissionError('candidate not accepted by the human asset decision')
        if treatment == 'occluder' and decision['occluder_definition_accepted'] is not True:
            raise PermissionError('occluder definition not accepted')
    return sha(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p_run = sub.add_parser('run')
    p_run.add_argument('--output', type=Path, required=True)
    p_run.add_argument('--ros-domain-id', type=int, default=89)
    p_run.add_argument('--timeout', type=int, default=20)
    p_run.add_argument('--limit', type=int)
    p_run.add_argument('--only', action='append')
    p_run.add_argument('--run-prefix', default=RUN_PREFIX)
    p_run.add_argument('--occluder-assets', type=Path)
    p_run.add_argument('--sphere-assets', type=Path)
    p_run.add_argument('--controls-from', type=Path, help='earlier render ledger whose successful controls are reused')
    p_run.set_defaults(func=run)
    p_asm = sub.add_parser('assemble')
    p_asm.add_argument('--renders', type=Path, required=True)
    p_asm.add_argument('--output', type=Path, required=True)
    p_asm.set_defaults(func=assemble)
    p_val = sub.add_parser('validate-decision')
    p_val.add_argument('--decision', type=Path, required=True)
    p_val.set_defaults(func=lambda a: print(validate_asset_decision(a.decision)))
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
