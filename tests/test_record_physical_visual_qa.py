"""Synthetic unit fixtures only; these tests create no live QA attestations."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def helper(tmp_path,monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT/'scripts'))
    spec=importlib.util.spec_from_file_location('visual_qa_unit',ROOT/'scripts/record_physical_visual_qa.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tasks=[{'observation_id':'synthetic-obs1','entity_id':'unit-chair'},
           {'observation_id':'synthetic-obs2','entity_id':'unit-door'}]
    (tmp_path/'landmark_review_tasks.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in tasks))
    joined={'run_id':'synthetic-unit-only','request_sha256':'a'*64,'provider_tasks_sha256':'b'*64,
        'observations':[{'status':'awaiting_individual_visual_qa','reasons':[],
            'frame':'perception_capture/frame-000.json','frame_sha256':'c'*64} for _ in tasks]}
    monkeypatch.setattr(module,'join_capture',lambda directory:joined)
    return module,joined


def test_attest_binds_only_explicit_ids_without_correctness_label(helper,tmp_path):
    module,_=helper
    rows=module.attest(tmp_path,['synthetic-obs1'],'synthetic test note',
                       'synthetic-unit-test-not-live-review')
    assert len(rows)==1
    row=rows[0]
    assert row['observation_id']=='synthetic-obs1'
    assert row['request_sha256']=='a'*64 and row['frame_sha256']=='c'*64
    assert row['correct'] is None
    assert row['human_labels_generated'] is False


@pytest.mark.parametrize('identifiers,note,operator',[
    ([], 'note','operator'),(['synthetic-obs1','synthetic-obs1'],'note','operator'),
    (['not-present'],'note','operator'),(['synthetic-obs1'],' ','operator'),
    (['synthetic-obs1'],'note',' '),
])
def test_explicit_unique_present_identity_note_operator_required(helper,tmp_path,identifiers,note,operator):
    module,_=helper
    with pytest.raises(ValueError):
        module.attest(tmp_path,identifiers,note,operator)


def test_invalid_exact_join_cannot_be_attested(helper,tmp_path):
    module,joined=helper
    joined['observations'][0]['reasons']=['synthetic_timestamp_mismatch']
    with pytest.raises(ValueError,match='valid exact frame join'):
        module.attest(tmp_path,['synthetic-obs1'],'unit note','unit operator')


def test_cli_entity_resolves_single_observation_and_create_once(helper,tmp_path,monkeypatch):
    module,_=helper
    selected=[]
    monkeypatch.setattr(module,'attest',lambda run,ids,note,operator:selected.extend(ids) or [])
    output=tmp_path/'synthetic-empty-output.jsonl'
    argv=['record_physical_visual_qa.py','--run',str(tmp_path),'--entity-id','unit-chair',
        '--note','synthetic test only','--attested-by','synthetic-test',
        '--each-image-and-pixel-inspected','--output',str(output)]
    monkeypatch.setattr(sys,'argv',argv)
    module.main()
    assert selected==['synthetic-obs1']
    assert output.read_text()==''
    with pytest.raises(FileExistsError):
        module.main()


def test_cli_entity_with_multiple_frame_matches_rejected(helper,tmp_path,monkeypatch):
    module,_=helper
    (tmp_path/'landmark_review_tasks.jsonl').write_text(
        '{"observation_id":"synthetic-obs1","entity_id":"unit-chair"}\n'
        '{"observation_id":"synthetic-obs2","entity_id":"unit-chair"}\n')
    monkeypatch.setattr(sys,'argv',['record_physical_visual_qa.py','--run',str(tmp_path),
        '--entity-id','unit-chair','--note','synthetic','--attested-by','unit-test',
        '--each-image-and-pixel-inspected','--output',str(tmp_path/'should-not-exist')])
    with pytest.raises(ValueError,match='exactly one observation'):
        module.main()
