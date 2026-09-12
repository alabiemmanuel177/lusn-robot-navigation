"""Synthetic-only packet assembly tests; no real review attestations generated."""
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location('review_packet', Path(__file__).resolve().parents[1] / 'scripts/prepare_physical_review_packet.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


@pytest.fixture
def plan():
    views = []
    for number in range(1, 15):
        for category in M.CATEGORIES:
            map_id = f'r3geo_base_r{number:03d}'
            entity = f'chair-{number}' if category == 'chair' else map_id + ('_left_2_entrance' if category == 'laboratory_entrance' else '_right_2_entrance')
            views.append(dict(base_instruction_id=f'base-r{number:03d}', category=category,
                              intended_entity_id=entity, run_id=f'fixture-{number}-{category}',
                              partition='development' if number <= 10 else 'validation'))
    return dict(schema_version='research3-stationary-capture-plan/v1',
                protected_content_read=False, view_count=42, views=views)


def test_fixed_complete_selection_missing_targets_blocks(plan, tmp_path):
    dirs, policy, gates = M.selection(plan, tmp_path)
    assert len(dirs) == 42 and len(policy['targets']) == 56
    assert sum(t['entity_id'].endswith('_doorway') for t in policy['targets']) == 14
    assert all(t['frame'] == M.FRAME for t in policy['targets'])
    inventory = M.CONSOLIDATE.consolidate(dirs, sampling_policy=policy)
    assert inventory['status'] == 'blocked'
    assert inventory['selected_missing_items'] == 56
    assert len(inventory['runs']) == 42
    assert not inventory['human_labels_generated']
    assert all(g['status'] == 'missing_request_no_capture_read' for g in gates)


@pytest.mark.parametrize('change', ['duplicate', 'protected', 'partition', 'entity', 'run'])
def test_invalid_plan_rejected_before_directory_reads(plan, tmp_path, monkeypatch, change):
    if change == 'duplicate':
        plan['views'][-1] = dict(plan['views'][0])
    elif change == 'protected':
        plan['views'][-1]['base_instruction_id'] = 'base-r015'
    elif change == 'partition':
        plan['views'][-1]['partition'] = 'development'
    elif change == 'entity':
        plan['views'][-1]['intended_entity_id'] = 'r3geo_base_r015_left_2_entrance'
    else:
        plan['views'][-1]['run_id'] = '../escape'
    monkeypatch.setattr(M, 'gate_directory', lambda *a: pytest.fail('scope must precede directory reads'))
    with pytest.raises(ValueError):
        M.selection(plan, tmp_path)


def test_create_once_packet_no_fake_qa(plan, tmp_path):
    source = tmp_path / 'plan.json'
    source.write_text(json.dumps(plan))
    output = tmp_path / 'packet'
    manifest = M.prepare(source, [], output, runs_root=tmp_path / 'runs')
    assert manifest['status'] == 'blocked'
    assert manifest['ordinary_targets'] == 56
    assert (output / 'combined_visual_qa.jsonl').read_bytes() == b''
    for name, digest in manifest['files'].items():
        assert M.sha((output / name).read_bytes()) == digest
    with pytest.raises(FileExistsError):
        M.prepare(source, [], output)


def test_extra_missing_request_retained_and_protected_rejected(plan, tmp_path):
    extra = dict(schema_version='research3-review-extra-selection/v1',
                 selection_basis='explicit_stress_capture_not_confidence_or_correctness',
                 targets=[dict(run_id='stress', entity_id='sphere', frame=M.FRAME)])
    dirs, policy, gates = M.selection(plan, tmp_path, extra)
    assert len(dirs) == 43 and len(policy['targets']) == 57
    assert gates[-1]['status'] == 'missing_request_no_capture_read'
    stress = tmp_path / 'stress'
    stress.mkdir()
    (stress / 'request.json').write_text(json.dumps(dict(map_id='r3geo_base_r015')))
    with pytest.raises(ValueError, match='protected'):
        M.selection(plan, tmp_path, extra)


def test_duplicate_or_outcome_based_extra_rejected(plan, tmp_path):
    _, policy, _ = M.selection(plan, tmp_path)
    extra = dict(schema_version='research3-review-extra-selection/v1',
                 selection_basis='explicit_stress_capture_not_confidence_or_correctness',
                 targets=[policy['targets'][0]])
    with pytest.raises(ValueError):
        M.selection(plan, tmp_path, extra)
    extra['targets'][0] = dict(extra['targets'][0], confidence=.2)
    with pytest.raises(ValueError):
        M.selection(plan, tmp_path, extra)


def test_all_explicit_qa_rows_pass_through_without_fabrication(plan, tmp_path, monkeypatch):
    source = tmp_path / 'plan.json'
    source.write_text(json.dumps(plan))
    qa_paths = []
    rows = [{'run_id': 'fixture', 'observation_id': str(i), 'synthetic_only': True} for i in range(2)]
    for i, row in enumerate(rows):
        path = tmp_path / f'qa{i}.jsonl'
        path.write_text(json.dumps(row) + '\n')
        qa_paths.append(path)
    def consolidate(dirs, qa, sampling_policy):
        assert len(dirs) == 42 and len(sampling_policy['targets']) == 56
        assert qa == rows
        return {'status': 'blocked', 'items': rows, 'retained_source_rows': 2}
    monkeypatch.setattr(M.CONSOLIDATE, 'consolidate', consolidate)
    output = tmp_path / 'packet'
    manifest = M.prepare(source, qa_paths, output, runs_root=tmp_path / 'runs')
    assert len(manifest['qa_inputs']) == 2
    assert json.loads((output / 'inventory.json').read_text())['items'] == rows
    assert [json.loads(line) for line in (output / 'combined_visual_qa.jsonl').read_text().splitlines()] == rows


def test_wrong_ordinary_request_map_rejected(plan, tmp_path):
    run = tmp_path / plan['views'][0]['run_id']
    run.mkdir()
    (run / 'request.json').write_text(json.dumps(dict(run_id=run.name,
        map_id='r3geo_base_r002', partition='development', protected_test_routes_used=False)))
    with pytest.raises(ValueError, match='identity'):
        M.selection(plan, tmp_path)
