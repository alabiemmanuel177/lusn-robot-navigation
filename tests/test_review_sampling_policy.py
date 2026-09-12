"""Synthetic sampling tests; never select or attest real detections."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    loaded=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


FIXTURES=module('sampling_synthetic_fixture',ROOT/'tests/test_consolidated_review.py')
INVENTORY=module('sampling_inventory',ROOT/'scripts/prepare_consolidated_review.py')
UI=module('sampling_ui',ROOT/'scripts/serve_physical_review.py')
EXPORT=module('sampling_export',ROOT/'scripts/export_physical_human_review.py')
capture=FIXTURES.capture


def policy():
    return {'schema_version':'research3-review-sampling-policy/v1','policy_id':'synthetic-prespecified-v1',
        'selection_basis':'prespecified_capture_views_not_confidence_or_correctness',
        'targets':[{'run_id':'synthetic','entity_id':'chair1','frame':'perception_capture/frame-000.json'}]}


def qa_for(item):
    return {**{key:item[key] for key in ('run_id','observation_id','task_sha256',
            'frame_sha256','request_sha256','provider_tasks_sha256')},
        'schema_version':'research3-machine-visual-qa/v1',
        'attested_by':'synthetic-unit-test-not-live-QA',
        **{key:True for key in INVENTORY.QA_CHECKS}}


def add_unframed_row(capture):
    path=capture/'landmark_review_tasks.jsonl'
    task=json.loads(path.read_text())
    extra={**task,'observation_id':'obs-outside-sampled-frame','entity_id':'other-chair',
           'observed_at_ns':20_000_000_000}
    path.write_text(json.dumps(task)+'\n'+json.dumps(extra)+'\n')


def inventory(capture,qa,sampling):
    return INVENTORY.consolidate([capture],qa,required_maps=['r3geo_base_r010'],
                                 required_classes=['chair'],sampling_policy=sampling)


def test_selected_complete_packet_does_not_require_every_provider_row(capture):
    add_unframed_row(capture)
    qa=FIXTURES.synthetic_qa(capture)
    original=inventory(capture,[qa],None)
    assert original['status']=='partial_human_review_handoff'
    result=inventory(capture,[qa],policy())
    assert result['status']=='ready_for_human_review'
    assert len(result['items'])==2 and result['not_selected_items']==1
    assert result['selected_ready_items']==1 and result['selected_missing_items']==0
    unselected=result['items'][1]
    assert unselected['status']=='not_selected_by_sampling_policy'
    assert unselected['pre_sampling_status']=='rejected'
    assert len(unselected['reasons'])>1
    assert result['sampling_policy_sha256']==INVENTORY.task_digest(policy())


def test_missing_planned_target_blocks_full_packet_even_with_class_coverage(capture):
    sampling=policy()
    sampling['targets'].append({'run_id':'not-yet-captured','entity_id':'chair2',
                                'frame':'perception_capture/frame-000.json'})
    result=inventory(capture,[FIXTURES.synthetic_qa(capture)],sampling)
    assert result['coverage_complete']
    assert result['status']=='partial_human_review_handoff'
    assert result['selected_missing_items']==1
    assert result['selected_missing'][0]['reason']=='selected_target_missing_or_unreviewable'


def test_stale_selected_and_nonselected_qa_cannot_enable_readiness(capture):
    add_unframed_row(capture)
    raw=inventory(capture,[],None)
    selected,unselected=[qa_for(item) for item in raw['items']]
    unselected['task_sha256']='stale'
    result=inventory(capture,[selected,unselected],policy())
    assert result['status']=='partial_human_review_handoff'
    assert 'stale_or_mismatched_visual_qa' in result['items'][1]['reasons']
    selected['frame_sha256']='stale'
    result=inventory(capture,[selected],policy())
    assert result['status']=='blocked'
    assert result['selected_missing_items']==1


def test_duplicate_observations_for_one_target_are_not_arbitrarily_selected(capture):
    tasks_path=capture/'landmark_review_tasks.jsonl'
    task=json.loads(tasks_path.read_text())
    tasks_path.write_text(json.dumps(task)+'\n'+json.dumps({**task,'observation_id':'obs2'})+'\n')
    frame_path=capture/'perception_capture/frame-000.json'
    frame=json.loads(frame_path.read_text())
    frame['trigger_observations'].append({**frame['trigger_observations'][0],'observation_id':'obs2'})
    frame_path.write_text(json.dumps(frame))
    raw=inventory(capture,[],None)
    result=inventory(capture,[qa_for(item) for item in raw['items']],policy())
    assert result['status']=='blocked'
    assert result['selected_missing'][0]['reason']=='selected_target_ambiguous'
    assert result['ready_items']==0


@pytest.mark.parametrize('mutation',[
    lambda p:p['targets'].append(copy.deepcopy(p['targets'][0])),
    lambda p:p.update(selection_basis='highest_confidence_only'),
    lambda p:p['targets'][0].update(frame='../escape.json'),
    lambda p:p['targets'][0].update(run_id='../escape'),
    lambda p:p['targets'][0].update(entity_id=''),
])
def test_invalid_selection_policy_rejected_before_capture_read(mutation):
    sampling=policy()
    mutation(sampling)
    with pytest.raises(ValueError):
        INVENTORY.consolidate([],sampling_policy=sampling)


def test_ui_and_export_automatically_revalidate_embedded_selection(capture):
    add_unframed_row(capture)
    qa=FIXTURES.synthetic_qa(capture)
    result=inventory(capture,[qa],policy())
    inventory_path,qa_path,progress=capture/'selected-inventory.json',capture/'selected-qa.jsonl',capture/'progress.jsonl'
    inventory_path.write_text(json.dumps(result))
    qa_path.write_text(json.dumps(qa)+'\n')
    store=UI.ReviewStore(inventory_path,qa_path,progress)
    assert len(store.items)==1 and store.items[0]['observation_id']=='obs1'
    EXPORT.export_payload(inventory_path,qa_path,progress)
    changed=copy.deepcopy(result)
    changed['sampling_policy']['targets'][0]['entity_id']='tampered'
    inventory_path.write_text(json.dumps(changed))
    with pytest.raises(ValueError,match='sampling policy checksum'):
        UI.ReviewStore(inventory_path,qa_path,capture/'rejected-progress.jsonl')
