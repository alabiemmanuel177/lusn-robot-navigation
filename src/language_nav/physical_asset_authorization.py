"""Default-deny build-only admission for protected physical derivatives."""
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
import runpy

import yaml

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {'scripts/build_authorized_heldout_assets.py', 'src/language_nav/physical_asset_authorization.py',
           'scripts/build_readable_physical_worlds.py', 'scripts/build_physical_absence_worlds.py',
           'src/language_nav/world/physical.py', 'scripts/verify_physical_world.py',
           'src/language_nav/evaluation/ordered.py'}
FILES = {'world.sdf', 'map.pgm', 'map.yaml', 'manifest.json', 'execution_catalog.json',
         'landmark_scene.yaml', 'ordered_geometry.json', 'verified_ordered_geometry.json', 'geometry_audit.json'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def local(root, name):
    if not isinstance(name, str) or Path(name).is_absolute() or '..' in Path(name).parts:
        raise PermissionError('contained build path required')
    path = Path(root) / name
    if any(p.is_symlink() for p in (path, *path.parents) if p.is_relative_to(root)):
        raise PermissionError('symlink build paths are forbidden')
    return path


def pinned(root, ref):
    path = local(root, ref['path'])
    if sha(path) != ref['sha256']:
        raise PermissionError('build input checksum mismatch')
    return path


@dataclass
class ProtectedBuild:
    root: Path
    output: Path
    approval_hash: str
    plan: dict
    design: dict
    design_hash: str
    calibration_hash: str | None
    instructions: dict
    generated: dict = field(default_factory=dict)

    def validate_operation(self, operation, source, destination, instruction=None):
        source, destination = Path(source).resolve(), Path(destination).resolve()
        base = source.name
        if base not in self.instructions or not destination.is_relative_to(self.output.resolve()):
            raise PermissionError('derivative outside authorized map/output')
        row = next(row for row in self.plan['worlds'] if row['base_instruction_id'] == base)
        if operation == 'readable' and source in self.generated:
            hashes = self.generated[source]
        elif source == local(self.root, row['source_directory']).resolve():
            hashes = row['source_sha256']
        else:
            raise PermissionError('derivative source is not approved or generated in this build')
        if any(sha(source / name) != digest for name, digest in hashes.items()):
            raise PermissionError('protected source changed before transformation')
        if instruction is not None and instruction != self.instructions[base]['canonical']:
            raise PermissionError('canonical instruction differs from approved build input')

    def validate_generation(self, destination, instruction):
        base = instruction.get('base_instruction_id')
        if (base not in self.instructions or instruction != self.instructions[base]['canonical']
                or Path(destination).resolve() != (self.output / 'absence_base' / base).resolve()):
            raise PermissionError('protected geometry generation outside approved recipe')

    def retain_generated(self, path):
        self.generated[Path(path).resolve()] = {name: sha(Path(path) / name) for name in FILES}


def authorize_build(path, digest, *, root=ROOT):
    root = Path(root).resolve()
    raw = Path(path).read_bytes()  # Non-protected authorization metadata first.
    if hashlib.sha256(raw).hexdigest() != digest:
        raise PermissionError('build authorization checksum mismatch')
    approval = json.loads(raw)
    if (approval.get('schema_version') != 'research3-protected-asset-build-authorization/v1'
            or approval.get('status') != 'approved_frozen'
            or approval.get('authorization_scope') != 'heldout_derivative_build_only'
            or approval.get('reviewer_type') != 'human' or not approval.get('approved_by')
            or not approval.get('approved_at_utc') or approval.get('recipe') != 'readable_and_exact_chair_absence/v1'):
        raise PermissionError('explicit human build-only approval required')
    sources = approval.get('source_sha256', {})
    if set(sources) != SOURCES:
        raise PermissionError('complete exact derivative recipe source pins required')
    for name, value in sources.items():
        if sha(ROOT / name) != value:
            raise PermissionError('actual derivative recipe source changed')
    provider = Path('/home/eao/risk-calibrated-nav/rcn/shortest_path.py')
    if sha(provider) != approval.get('shortest_path_source_sha256'):
        raise PermissionError('independent geometry verifier dependency changed')
    design_path = pinned(root, approval['design'])
    design = yaml.safe_load(design_path.read_text())
    check = runpy.run_path(str(ROOT / 'scripts/check_physical_design_readiness.py'))['check'](design)
    if design.get('status') != 'frozen' or not check['supplied_design_fields_valid_and_complete']:
        raise PermissionError('complete frozen design required before protected build inputs')
    calibration_hash = None
    if approval.get('calibration') is not None:
        calibration = json.loads(pinned(root, approval['calibration']).read_text())
        if calibration.get('schema_version') != 'landmark-calibration/v1' or calibration.get('partition') not in {'development', 'validation'}:
            raise PermissionError('only non-protected calibration may bind the schedule template')
        calibration_hash = approval['calibration']['sha256']
    # Only now can protected explicit build metadata be opened.
    plan = json.loads(pinned(root, approval['plan']).read_text())
    if plan.get('schema_version') != 'research3-protected-asset-build-plan/v1':
        raise PermissionError('explicit derivative plan required')
    rows = plan.get('worlds', [])
    ids = [row.get('base_instruction_id') for row in rows]
    if not ids or len(set(ids)) != len(ids) or any(not re.fullmatch(r'base-r0(?:1[5-9]|20)', str(i)) for i in ids):
        raise PermissionError('unique protected stable world identities required')
    output = local(root, plan['output_directory'])
    if not output.is_relative_to(root / 'data') or output == root / 'data' or output.exists():
        raise PermissionError('new contained data derivative directory required')
    instructions = {}
    from language_nav.benchmark import CorruptionCondition
    for row in rows:
        base = row['base_instruction_id']
        source = local(root, row['source_directory'])
        if source.name != base or set(row.get('source_sha256', {})) != FILES:
            raise PermissionError('complete original asset pins and stable source directory required')
        record = json.loads(pinned(root, row['instructions']).read_text())
        if record.get('canonical', {}).get('base_instruction_id') != base or record['canonical'].get('partition') != 'held_out':
            raise PermissionError('authored held-out canonical instruction required')
        variants = record.get('deployed_variants', [])
        expected = {base + '-' + c.value + '-s0' for c in CorruptionCondition}
        if ({v.get('variant_id') for v in variants} != expected or len(variants) != len(expected)
                or any(set(v) != {'variant_id', 'base_instruction_id', 'raw_text', 'provenance'}
                       or v['base_instruction_id'] != base or not isinstance(v['raw_text'], str)
                       or not v['raw_text'].strip() or not isinstance(v['provenance'], str) for v in variants)):
            raise PermissionError('all eight exact deployable instructions required, without evaluator answers')
        instructions[base] = record
    return ProtectedBuild(root, output, digest, plan, design, sha(design_path), calibration_hash, instructions)
