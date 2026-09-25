#!/usr/bin/env python3
"""Portable, local-only joint review and hash-bound return; never auto-approve."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import zipfile

from export_physical_human_review import _UI, export_payload, NONHUMAN

ORIGINAL_CONSOLIDATE = _UI._INVENTORY.consolidate
RULES = {
    'category_rule': 'Judge the object under the reported pixel using the full image, not colour alone. A sphere or cylinder is not a chair, doorway or entrance. A doorway needs a visible opening/jamb context; LAB or OFFICE context must support the entrance subtype. If the image cannot establish this, choose unreviewable.',
    'entity_association_rule': 'Judge whether the visible object is the particular claimed entity and region, using camera pose, the numbered catalogue references and full scene context. Matching colour or nearest coordinates alone is not proof. If repeated objects cannot be distinguished, choose unreviewable.',
    'pose_rule': 'Proposed engineering acceptance: planar Euclidean distance between reported map-frame x/y and the claimed catalogue reference x/y is at most 0.35 m, including equality. Category and association are judged separately. Missing or ambiguous reference/position evidence is unreviewable. This defines reference-point accuracy, not surface alignment or guaranteed navigation safety.',
    'yaw_rule': 'Yaw is supplied by the catalogue, not estimated independently. Treat it only as reference-orientation metadata: it must agree with the claimed reference modulo 2*pi within 0.000001 rad. Missing reference yaw is unreviewable. No learned orientation accuracy claim is permitted.'}
COVERAGE = {'schema_version': 'research3-physical-calibration-coverage/v2',
    'outcome_coverage_scope': 'global_class', 'minimum_per_map_class_total': 1,
    'minimum_per_class_outcome': 5, 'minimum_per_class_confidence_bin': 5,
    'confidence_bin_edges': [0, 0.5, 0.8, 1],
    'unreviewable_exclusion_policy': 'allow_with_counts'}
RETURN_NAMES = {'approval.json', 'policy.json', 'requirements.json', 'progress.jsonl', 'return_manifest.json'}


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_once(path, raw):
    with Path(path).open('xb') as stream:
        stream.write(raw)


def proposal():
    return {'schema_version': 'research3-portable-review-proposal/v1', 'status': 'proposed_not_approved',
        'rules': RULES, 'coverage': COVERAGE,
        'primary_reviewer': 'one real researcher; optional independent second review, no inter-rater reliability claim',
        'rationale': {
            'pose': '0.35 m matches the existing R3 independently measured goal-error criterion. Reusing that scale is an engineering proposal, not proof it is optimal for landmarks; centroid/surface offsets may matter. Not chosen by fitting the current residuals.',
            'yaw': '1e-6 rad checks copied metadata consistency only, not detector orientation quality.',
            'coverage': 'One accepted observation per map/class prevents missing-map cells; five per pooled binary outcome and confidence bin is a modest pilot coverage floor, not a precision or sample-size guarantee. Fixed coarse bins are not tailored to the captured scores.',
            'stress': 'Four engineered distractors are diagnostic stress cases, not natural-error prevalence or automatically valid calibration negatives. This approval does not approve a calibration model or claim transfer.'},
        'limitations': ['Captures and assistant presentation checks precede this proposal; do not call the collection preregistered.',
            'Approval must precede human labels. Existing 60 targets may not satisfy coverage; do not lower thresholds after reviewing outcomes.',
            'Fit suitability, handling of engineered stress samples, validation separation, campaign design and held-out execution require separate decisions.'],
        'campaign_authorized': False, 'human_labels_generated': False}


def canonical_consolidate(*args, **kwargs):
    result = ORIGINAL_CONSOLIDATE(*args, **kwargs)
    for run in result['runs']:
        expected = Path('runs') / run['run_id']
        if Path(run['directory']).resolve() != expected.resolve():
            raise ValueError('review run is outside the portable kit')
        run['directory'] = expected.as_posix()
    return result


def activate():
    _UI._INVENTORY.consolidate = canonical_consolidate


def verify_kit(root):
    root = Path(root).resolve()
    manifest = json.loads((root / 'kit_manifest.json').read_bytes())
    if manifest.get('schema_version') != 'research3-portable-review-kit/v1':
        raise ValueError('unknown kit')
    for name, digest in manifest['files'].items():
        path = root / name
        if Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('unsafe kit member')
        if sha(path.read_bytes()) != digest:
            raise ValueError('kit checksum mismatch: ' + name)
    return manifest


def approve(root, name, role, accepted):
    verify_kit(root)
    if not accepted or role not in ('Researcher', 'Supervisor') or not name.strip() or NONHUMAN.search(name) or name.startswith('TODO'):
        raise ValueError('explicit acceptance by an authorized named human required')
    p = json.loads((root / 'proposal.json').read_bytes())
    out = root / 'review_output'
    out.mkdir(exist_ok=False)
    now = datetime.now(timezone.utc).isoformat()
    policy = {'schema_version': 'research3-joint-review-policy/v1', 'status': 'approved',
        'reviewer_type': 'human', 'approved_by': name, 'approved_at': now,
        'protected_data_used': False, **p['rules']}
    approval = {'schema_version': 'research3-portable-review-acceptance/v1',
        'reviewer_name': name, 'reviewer_role': role, 'approved_at': now,
        'proposal_sha256': sha((root / 'proposal.json').read_bytes()),
        'decisions': {key: 'accept' for key in (*RULES, 'coverage', 'primary_reviewer')},
        'overall_decision': 'approved', 'protected_outcomes_consulted': False,
        'authority_scope': 'review_rubric_and_coverage_only',
        'identity_authenticated': False, 'campaign_authorized': False}
    for file, content in [('approval.json', approval), ('policy.json', policy), ('requirements.json', p['coverage'])]:
        write_once(out / file, encoded(content))


def check_acceptance(root, out):
    p = json.loads((root / 'proposal.json').read_bytes())
    a = json.loads((out / 'approval.json').read_bytes())
    policy = json.loads((out / 'policy.json').read_bytes())
    req = json.loads((out / 'requirements.json').read_bytes())
    if (a.get('schema_version') != 'research3-portable-review-acceptance/v1'
            or a.get('proposal_sha256') != sha((root / 'proposal.json').read_bytes())
            or a.get('reviewer_role') not in ('Researcher', 'Supervisor')
            or a.get('overall_decision') != 'approved'
            or a.get('protected_outcomes_consulted') is not False
            or a.get('authority_scope') != 'review_rubric_and_coverage_only'
            or a.get('campaign_authorized') is not False
            or a.get('decisions') != {key: 'accept' for key in (*RULES, 'coverage', 'primary_reviewer')}
            or not _UI._JOINT.validate_policy(policy)
            or policy.get('approved_by') != a.get('reviewer_name')
            or policy.get('approved_at') != a.get('approved_at')
            or any(policy.get(k) != v for k, v in p['rules'].items()) or req != p['coverage']):
        raise ValueError('approval, proposal or requirements mismatch')
    return policy, req


def pilot_human_screen(reviewed, readiness):
    categories = ('chair', 'doorway', 'laboratory_entrance', 'office_entrance')
    counts = {c: {'correct': 0, 'incorrect': 0} for c in categories}
    for row in reviewed:
        if row['category'] not in counts or row['correct'] not in (0, 1):
            raise ValueError('invalid verified pilot outcome')
        counts[row['category']]['correct' if row['correct'] else 'incorrect'] += 1
    pending = readiness['excluded_counts'].get('pending_human_review', 0)
    unreviewable = readiness['excluded_counts'].get('human_unreviewable', 0)
    return dict(class_outcomes=counts, pending=pending, unreviewable=unreviewable,
                all_selected_items_reviewed=pending == 0,
                correctness_screen_passed=pending == 0 and all(n >= 2 for c in counts.values() for n in c.values()),
                calibration_eligible=False, primary_collection_authorized=False,
                unreviewable_counted_as_incorrect=False)


def check_review(root, out):
    manifest = verify_kit(root)
    check_acceptance(root, out)
    reviewed, samples, readiness = export_payload(root / 'inventory.json', root / 'qa.jsonl',
        out / 'progress.jsonl', json.loads((out / 'requirements.json').read_bytes()),
        evidence=root / 'evidence.json', policy=out / 'policy.json')
    result = {'schema_version': 'research3-portable-return-validation/v1',
        'reviewed_binary_labels': len(reviewed), 'readiness': readiness,
        'calibration_approved': False, 'campaign_authorized': False}
    if manifest.get('dataset_role') == 'design_feasibility':
        result['pilot_human_screen'] = pilot_human_screen(reviewed, readiness)
        readiness['coverage_diagnostic_status'] = readiness['status']
        readiness['status'] = 'design_only_not_calibration_eligible'
        result.update(dataset_role='design_feasibility', calibration_eligible=False,
                      note='Generic Coverage v2 diagnostics do not promote design labels to calibration data.')
    return result


def return_review(root, destination):
    out = root / 'review_output'
    result = check_review(root, out)
    files = {name: (out / name).read_bytes() for name in RETURN_NAMES - {'return_manifest.json'}}
    return_manifest = {'schema_version': 'research3-portable-review-return/v1',
        'kit_sha256': sha((root / 'kit_manifest.json').read_bytes()),
        'files': {name: sha(raw) for name, raw in files.items()},
        'complete_or_calibrated_claimed': False}
    if result.get('dataset_role') == 'design_feasibility':
        return_manifest.update(dataset_role='design_feasibility', calibration_eligible=False)
    files['return_manifest.json'] = encoded(return_manifest)
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in files.items():
            archive.writestr(name, raw)
    return result


def validate_return(root, source):
    kit_manifest = verify_kit(root)
    with zipfile.ZipFile(source) as archive:
        if set(archive.namelist()) != RETURN_NAMES or len(archive.namelist()) != len(RETURN_NAMES):
            raise ValueError('unexpected or duplicate return members')
        if any(info.file_size > 2_000_000 for info in archive.infolist()):
            raise ValueError('oversized return')
        files = {name: archive.read(name) for name in RETURN_NAMES}
    manifest = json.loads(files.pop('return_manifest.json'))
    if kit_manifest.get('dataset_role') == 'design_feasibility' and (
            manifest.get('dataset_role') != 'design_feasibility' or manifest.get('calibration_eligible') is not False):
        raise ValueError('design-only return scope missing or promoted')
    if (manifest.get('schema_version') != 'research3-portable-review-return/v1'
            or manifest.get('kit_sha256') != sha((root / 'kit_manifest.json').read_bytes())
            or manifest.get('files') != {name: sha(raw) for name, raw in files.items()}):
        raise ValueError('return is stale, modified, or belongs to another kit')
    with tempfile.TemporaryDirectory(prefix='r3-return-') as temporary:
        out = Path(temporary)
        for name, raw in files.items():
            write_once(out / name, raw)
        return check_review(root, out)


README = '''# Research 3 portable human-review kit

No ROS, Gazebo, GPU, R1/R2 checkout or web account is needed. Keep this folder
intact. Python 3.10+ is required. Commands below run in the extracted folder;
on Windows use `py` instead of `python3` if appropriate.

1. Install the two dependencies: `python3 -m pip install -r requirements.txt`.
2. Read PROPOSED_RULES.md and proposal.json BEFORE reviewing observations.
3. Preview safely: `python3 review.py preview`. Open http://127.0.0.1:8793/.
   Preview cannot save judgments. Stop the server with Ctrl-C before another command.
4. If you are authorized to approve the review rules and accept ALL proposals:
   `python3 review.py approve --name "Your real name" --role Researcher --accept-proposal`
   This records your human action, not a software-certified identity. A separate
   reviewer without protocol authority must ask the researcher to supply approval.
   To revise/reject: fill DECISIONS.template.json, return it, and STOP before labels.
   Do not edit proposal.json or other hashed inputs. A revision needs a new kit.
5. `python3 review.py review`. Review each of the 60 items using all three judgments.
   Unknown is unreviewable, not incorrect. Enter your name; save explicitly.
   Ctrl-C then the same command resumes the append-only journal. Do not move the
   folder while running; its portable paths allow relocation after stopping.
6. `python3 review.py return --output my-review-return.zip`.
   Send ONLY that ZIP to the researcher through the agreed attachment/file-sharing
   channel. It includes your name, dates, notes and judgments, but no raw images.
   Partial returns are allowed and explicitly reported as incomplete. Back up
   review_output; no upload occurs automatically. Use a new return filename each time.

The receiving researcher runs `python3 review.py validate-return --input my-review-return.zip`
inside their copy of the SAME kit. Validation does not overwrite prior reviews,
invent labels, approve calibration, or authorize experiments. Archive hashes detect
changes, not malicious impersonation; verify the reviewer through your normal channel.

Single primary human review is proposed; independent second review is optional,
must use a separate kit copy/return, and is not silently merged. No inter-rater
reliability is claimed. The existing 60 items may not meet the proposed calibration
coverage. Further evidence and separate calibration/protocol approval can be required.

This is a research evidence tool, not a completed scientific release. The kit has
no telemetry or automatic network requests; dependency installation uses pip's
configured package source. Serve it only on localhost. Images are retained RGB-D
records, not generated answers. Confidence is not a correctness verdict.
'''


def design_scope(plan_path, partition):
    """Explicit exploratory mode; never admit pilot IDs through the primary gate."""
    if partition != 'development':
        raise ValueError('design review requires development partition')
    raw = Path(plan_path).read_bytes()
    plan = json.loads(raw)
    if (plan.get('exploratory') is not True or plan.get('calibration_eligible') is not False
            or plan.get('protected_access') is not False or plan.get('scheduled') != 96
            or len(plan.get('rows', [])) != 96):
        raise ValueError('exact design-only 96-assignment plan required')
    rows = {}
    for row in plan['rows']:
        name = row.get('candidate_id', '')
        if (not re.fullmatch(r'r3-ca-v1-r(001|006)-(chair|doorway|laboratory_entrance|office_entrance)-[dv][0-9]+-y[01]-light(080|090|100)-s17', name)
                or name in rows or row.get('partition') != 'development'
                or row.get('map_id') != 'r3geo_base_r' + name.split('-r')[1][:3]
                or row.get('calibration_eligible') is not False):
            raise ValueError('nonprotected class-aware design identity required')
        rows[name] = row
    return raw, rows


def validate_design_packet(packet, design, inventory):
    audit = json.loads((packet / 'pilot_audit.json').read_bytes())
    records = audit.get('rows', [])
    if (audit.get('integrity_passed') is not True or audit.get('automatic_feasibility_passed') is not True
            or audit.get('plan_sha256') != sha(design[0]) or audit.get('scheduled') != 96
            or len(records) != 96 or {r.get('candidate_id') for r in records} != set(design[1])
            or audit.get('calibration_eligible') is not False):
        raise ValueError('complete exact design audit and confidence screen required')
    emitted = {r['candidate_id'] for r in records if r['status'] == 'emitted'}
    runs = [r['run_id'] for r in inventory['runs']]
    if not emitted or len(runs) != len(set(runs)) or set(runs) != emitted:
        raise ValueError('every design emission must be retained in the review packet')
    expected_targets = [{'run_id': name, 'entity_id': design[1][name]['entity_id'],
                         'frame': 'perception_capture/frame-000.json'} for name in sorted(emitted)]
    policy = inventory.get('sampling_policy', {})
    if (policy.get('policy_id') != 'class-aware-design-all-emissions-v1'
            or sorted(policy.get('targets', []), key=lambda r: r['run_id']) != expected_targets):
        raise ValueError('exact all-emission design sampling policy required')


def build_kit(repo, output, *, packet_directory=None, partition=None, design_plan=None):
    repo = Path(repo).resolve()
    if design_plan is not None and packet_directory is None:
        raise ValueError('design plan requires explicit packet')
    design = design_scope(design_plan, partition) if design_plan is not None else None
    if packet_directory is None and partition is not None:
        raise ValueError('partition requires an explicit expansion packet')
    packet = (Path(packet_directory).resolve() if packet_directory is not None
              else repo / 'reports/physical_review_packet_20260911_v2')
    if packet_directory is not None:
        if partition not in ('development', 'validation'):
            raise ValueError('new packet requires one explicit nonprotected partition')
        if not packet.is_relative_to(repo / 'reports'):
            raise ValueError('packet must be inside owned reports')
    inv = json.loads((packet / 'inventory.json').read_bytes())
    qa = (packet / 'combined_visual_qa.jsonl').read_bytes()
    if design is not None:
        validate_design_packet(packet, design, inv)
    if packet_directory is not None:
        if not inv['runs']:
            raise ValueError('no actual expansion captures to package')
        # Refuse protected/mixed partitions before consolidation opens evidence.
        for run in inv['runs']:
            source = Path(run['directory']).resolve()
            if source.parent != (repo / 'reports/physical_live_episodes').resolve():
                raise ValueError('unexpected source run')
            if design is not None:
                if run['run_id'] not in design[1]:
                    raise ValueError('run outside exact design plan')
            elif not re.fullmatch(r'expansion-v1-r(00[1-9]|01[0-4])-(chair|doorway|laboratory_entrance|office_entrance)-s[12]-view[0-4](-retry1)?',run['run_id']):
                raise ValueError('only prespecified primary expansion IDs may enter this kit')
            request = json.loads((source / 'request.json').read_bytes())
            number = int(run['run_id'].split('-r')[1][:3])
            expected = 'development' if number <= 10 else 'validation'
            if (request.get('partition') != partition or expected != partition
                    or request.get('map_id') != f'r3geo_base_r{number:03}'
                    or request.get('run_id') != run['run_id']
                    or request.get('protected_test_routes_used') is not False):
                raise ValueError('mixed, protected or inconsistent packet identity')
            if design is not None:
                assigned = design[1][run['run_id']]
                if (request.get('distance_lighting_pilot', {}).get('plan_sha256') != sha(design[0])
                        or request.get('capture_target_entity_id') != assigned['entity_id']
                        or request.get('capture_target_categories') != [assigned['category']]
                        or request.get('simulation_seed') != 17 or request.get('capture_only') is not True):
                    raise ValueError('design request binding mismatch')
    original = ORIGINAL_CONSOLIDATE([r['directory'] for r in inv['runs']],
        [json.loads(line) for line in qa.splitlines()], required_maps=inv['required_maps'],
        required_classes=inv['required_classes'], sampling_policy=inv['sampling_policy'])
    if original['items'] != inv['items'] or original['runs'] != inv['runs']:
        raise ValueError('original packet is stale')
    files = {}
    for run in inv['runs']:
        source = Path(run['directory'])
        if source.resolve().parent != (repo / 'reports/physical_live_episodes').resolve():
            raise ValueError('unexpected source run')
        names = ['request.json', 'runtime_scene.yaml', 'landmark_review_tasks.jsonl',
                 'perception_capture/summary.json', 'perception_capture/observation_index.json']
        summary = json.loads((source / 'perception_capture/summary.json').read_bytes())
        for frame_name in summary['frames']:
            if not re.fullmatch(r'frame-\d{3}\.json', frame_name):
                raise ValueError('unexpected frame name')
            names.append('perception_capture/' + frame_name)
            frame = json.loads((source / 'perception_capture' / frame_name).read_bytes())
            for kind in ('rgb', 'depth'):
                name = frame[kind]['file']
                if not re.fullmatch(r'frame-\d{3}-(rgb|depth)\.bin', name):
                    raise ValueError('unexpected media name')
                names.append('perception_capture/' + name)
        for name in names:
            files['runs/' + run['run_id'] + '/' + name] = (source / name).read_bytes()
        run['directory'] = 'runs/' + run['run_id']
    files['inventory.json'] = encoded(inv)
    files['qa.jsonl'] = qa
    packet_proposal = proposal()
    if design is not None:
        files['design_plan.json'] = design[0]
        for name in ('attempt_accounting.json', 'machine_visual_qa_report.json', 'pilot_audit.json'):
            files[name] = (packet / name).read_bytes()
        packet_proposal['dataset_role'] = 'design_feasibility'
        packet_proposal['calibration_eligible'] = False
        packet_proposal['design_plan_sha256'] = sha(design[0])
        packet_proposal['pilot_correctness_screen'] = {'correct_per_class': 2, 'incorrect_per_class': 2}
        packet_proposal['rationale']['stress'] = 'Fresh class-aware acquisition feasibility pilot; no engineered negative labels.'
        packet_proposal['limitations'] = [
            'Design-only observations are excluded from primary calibration fitting and validation.',
            'The design was informed by earlier failed pilots; this is exploratory, not independent confirmation.',
            'Review all selected emissions. Nondetections and infrastructure failures are not incorrect labels.',
            'Machine image checks do not establish identity or correctness. Use unreviewable when evidence is insufficient.',
            'Pilot feasibility needs two correct and two incorrect joint human outcomes per class; a deficit remains a deficit.',
            'The primary Coverage v2 floors remain unchanged and cannot be satisfied with this pilot.',
            'This return does not approve primary collection, a calibrated model, validation release or protected execution.']
    elif packet_directory is not None:
        packet_proposal['expansion_partition'] = partition
        packet_proposal['rationale']['stress'] = 'Pilot and engineered diagnostic observations are excluded from this primary expansion kit.'
        packet_proposal['limitations'] = [
            'The accepted rubric is rebound to these new evidence bytes; no previous labels transfer.',
            'This kit alone does not establish prospective capture protocol compliance or calibration coverage.',
            'Coverage floors apply separately to each primary partition. Do not lower thresholds after review.',
            'Keep validation returns outside fitting and model selection. File separation alone is not access control.',
            'Fitting protocol, calibration freeze, campaign and held-out execution require separately bound decisions.']
    files['proposal.json'] = encoded(packet_proposal)
    files['policy.draft.json'] = encoded({'schema_version': 'research3-joint-review-policy/v1',
        'status': 'draft', 'protected_data_used': False, **RULES})
    files['DECISIONS.template.json'] = encoded({'reviewer_name': None, 'reviewer_role': None,
        'reviewed_at': None, 'protected_outcomes_consulted': False, 'overall_decision': 'pending',
        'proposal_sha256': sha(files['proposal.json']),
        'decisions': {k: {'decision': 'pending', 'replacement': None, 'rationale': None}
                      for k in (*RULES, 'coverage', 'primary_reviewer')}})
    readme = README
    if design is not None:
        readme = readme.replace('60', str(inv['selected_ready_items']))
        readme = ('# DESIGN-ONLY PILOT — NOT PRIMARY CALIBRATION DATA\n\n'
                  'Judge the actual object category, specific instance and reference-point consistency. '
                  'Do not judge from colour alone, confidence, or a machine attestation. '
                  'Choose unreviewable whenever the image/context does not support a judgment. '
                  'Review every selected emission; do not manufacture negatives to fill a quota.\n\n'
                  'This fresh panel follows earlier failed exploratory designs. Its labels test acquisition '
                  'feasibility only and cannot be used to fit or validate calibration. The pilot screen asks '
                  'for two correct and two incorrect joint outcomes per class, without changing primary '
                  'Coverage v2. If it fails, report failure. Your rubric acceptance and labels do not '
                  'approve primary execution, models, validation release or held-out access.\n\n' + readme)
    elif packet_directory is not None:
        readme = readme.replace('60', str(len(inv['items'])))
        readme += ('\n## Expansion partition boundary\n\nThis kit contains only the ' + partition +
                   ' primary panel. Keep its return separate from other panels. '
                   'Validation returns must not be exposed to fitting or model selection. '
                   'File separation alone does not authenticate or enforce reviewer blinding. '
                   'Pilot and engineered diagnostic observations are excluded. '
                   'Missing detections are recorded in the attempt ledger, not invented review rows.\n')
    files['README.md'] = readme.encode()
    files['PROPOSED_RULES.md'] = ('# Proposed rules — NOT approved\n\n' +
        '\n\n'.join('## ' + k.replace('_', ' ') + '\n\n' + v for k, v in RULES.items()) +
        '\n\n## Rationale and limits\n\n' + '\n\n'.join(packet_proposal['rationale'].values()) +
        '\n\nCoverage: ' + json.dumps(COVERAGE) + '\n\n' +
        '\n\n'.join(packet_proposal['limitations'])).encode()
    files['requirements.txt'] = b'Pillow>=10,<13\nPyYAML>=6,<7\n'
    if packet_directory is not None and partition == 'validation':
        files['seal_validation_review.py'] = (repo / 'scripts/seal_validation_review.py').read_bytes()
        files['VALIDATION_DELAYED_RELEASE.md'] = (repo / 'docs/VALIDATION_DELAYED_RELEASE.md').read_bytes()
        files['requirements.txt'] += b'cryptography>=41\n'
        validation_readme = files['README.md'].decode().replace(
            'Send ONLY that ZIP to the researcher through the agreed attachment/file-sharing\n   channel.',
            'Do NOT send that plaintext ZIP. Follow VALIDATION_DELAYED_RELEASE.md to encrypt it\n   locally and send only the sealed envelope; retain the key until approved release.')
        files['README.md'] = (b'IMPORTANT: This is withheld validation. Follow VALIDATION_DELAYED_RELEASE.md; '
                             b'never send plaintext verdicts before the development freeze.\n\n' + validation_readme.encode())
    for name in ('serve_physical_review.py', 'export_physical_human_review.py',
                 'prepare_consolidated_review.py', 'join_physical_review_capture.py',
                 'prepare_joint_review_evidence.py'):
        files[name] = (repo / 'scripts' / name).read_bytes()
    files['review.py'] = Path(__file__).read_bytes()
    previous = Path.cwd()
    with tempfile.TemporaryDirectory(prefix='r3-kit-build-') as temporary:
        root = Path(temporary)
        try:
            for name, raw in files.items():
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True)
                write_once(path, raw)
            os.chdir(root)
            evidence = _UI._JOINT.build(root / 'inventory.json')
            if not all(row['evidence_complete'] for row in evidence['items']):
                raise ValueError('portable evidence incomplete')
            files['evidence.json'] = encoded(evidence)
        finally:
            os.chdir(previous)
    manifest = {'schema_version': 'research3-portable-review-kit/v1',
        'original_inventory_sha256': sha((packet / 'inventory.json').read_bytes()),
        'files': {name: sha(raw) for name, raw in files.items()},
        'targets': len(evidence['items']), 'runs': len(inv['runs']),
        'human_labels_generated': False, 'approved': False, 'publicly_hosted': False}
    if design is not None:
        manifest.update(dataset_role='design_feasibility', calibration_eligible=False,
                        design_plan_sha256=sha(design[0]), diagnostic_or_pilot_included=True)
    elif packet_directory is not None:
        manifest.update(expansion_partition=partition, diagnostic_or_pilot_included=False,
                        protects_validation_from_model_selection_by_itself=False)
    files['kit_manifest.json'] = encoded(manifest)
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in sorted(files.items()):
            archive.writestr(name, raw)
    with zipfile.ZipFile(output) as archive:
        if any(sha(archive.read(name)) != sha(raw) for name, raw in files.items()):
            raise ValueError('written kit checksum mismatch')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('build', 'preview', 'approve', 'review', 'return', 'validate-return'))
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--packet-directory', type=Path,
                        help='explicit new primary expansion packet; requires --partition')
    parser.add_argument('--partition', choices=('development', 'validation'))
    parser.add_argument('--design-plan', type=Path, help='explicit design-only class-aware pilot mode, never primary')
    parser.add_argument('--name', default='')
    parser.add_argument('--role', choices=('Researcher', 'Supervisor'), default='Researcher')
    parser.add_argument('--accept-proposal', action='store_true')
    args = parser.parse_args()
    if args.command == 'build':
        if args.output is None: parser.error('--output required')
        print(json.dumps(build_kit(args.repo, args.output, packet_directory=args.packet_directory,
                                  partition=args.partition, design_plan=args.design_plan), indent=2)); return
    root = Path(__file__).resolve().parent
    os.chdir(root); activate(); verify_kit(root)
    if args.command == 'approve':
        approve(root, args.name, args.role, args.accept_proposal)
        print('Human acceptance recorded. No observations reviewed; no calibration/campaign approved.'); return
    if args.command in ('return', 'validate-return'):
        target = args.output if args.command == 'return' else args.input
        if target is None: parser.error('--output or --input required')
        result = return_review(root, target) if args.command == 'return' else validate_return(root, target)
        print(json.dumps(result, indent=2)); return
    if args.command == 'review':
        out = root / 'review_output'; check_acceptance(root, out)
        policy = out / 'policy.json'; progress = out / 'progress.jsonl'
    else:
        policy = root / 'policy.draft.json'; progress = root / 'preview.jsonl'
    store = _UI.ReviewStore(root / 'inventory.json', root / 'qa.jsonl', progress,
        resume=progress.exists(), evidence=root / 'evidence.json', policy=policy)
    server = _UI.ThreadingHTTPServer(('127.0.0.1', 8793), _UI.handler_for(store))
    print('Open http://127.0.0.1:8793/ — Ctrl-C to stop.', flush=True)
    try: server.serve_forever()
    finally: server.server_close()


if __name__ == '__main__':
    main()
