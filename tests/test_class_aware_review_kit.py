import copy
import json
import pytest
import portable_physical_review as portable
from prepare_consolidated_review import valid_visual_check
from class_aware_acquisition_pilot import OUTPUT, rows
from finalize_class_aware_pilot import check_request


def test_exact_exploratory_scope():
    raw, scope = portable.design_scope(OUTPUT / 'plan.json', 'development')
    assert len(scope) == 96 and json.loads(raw)['calibration_eligible'] is False
    with pytest.raises(ValueError, match='development'):
        portable.design_scope(OUTPUT / 'plan.json', 'validation')


@pytest.mark.parametrize('change', ['primary', 'protected', 'duplicate', 'wrong_map', 'partial'])
def test_design_scope_rejects_promoted_or_incomplete_plan(tmp_path, change):
    plan = json.loads((OUTPUT / 'plan.json').read_bytes())
    if change == 'primary': plan['calibration_eligible'] = True
    if change == 'protected': plan['rows'][0]['candidate_id'] = 'r3-ca-v1-r015-chair-d50-y0-light090-s17'
    if change == 'duplicate': plan['rows'][1] = copy.deepcopy(plan['rows'][0])
    if change == 'wrong_map': plan['rows'][0]['map_id'] = 'r3geo_base_r002'
    if change == 'partial': plan['rows'].pop()
    path = tmp_path / 'plan.json'
    path.write_text(json.dumps(plan))
    with pytest.raises(ValueError): portable.design_scope(path, 'development')


def render_qa():
    return dict(schema_version='research3-render-integrity-qa/v1', attested_by='automated integrity checks',
        full_frame_visible=True, pixel_inside_frame=True, frame_integrity_verified=True,
        identity_decidable=None, context_sufficient=None, human_reviewability_established=False,
        human_labels_generated=False, correct=None)


def test_render_qa_does_not_establish_identity_or_enter_primary_gate():
    qa = render_qa()
    assert valid_visual_check(qa, design_only=True)
    assert not valid_visual_check(qa)
    for field in ('identity_decidable', 'context_sufficient', 'human_reviewability_established', 'correct'):
        altered = dict(qa, **{field: True})
        assert not valid_visual_check(altered, design_only=True)


@pytest.mark.parametrize('key,value', [('simulation_seed', 9), ('capture_only', False),
    ('capture_target_entity_id', 'wrong'), ('protected_test_routes_used', True)])
def test_independent_audit_rejects_request_drift(key, value):
    schedule = rows()
    request = copy.deepcopy(json.loads((OUTPUT / 'execution_plan.json').read_bytes())['rows'][0]['request'])
    check_request(request, schedule[0])
    request[key] = value
    with pytest.raises(ValueError): check_request(request, schedule[0])


def test_new_design_ids_still_rejected_by_primary_builder(tmp_path):
    packet = tmp_path / 'reports/packet'
    packet.mkdir(parents=True)
    name = rows()[0]['candidate_id']
    (packet / 'inventory.json').write_text(json.dumps({'runs': [dict(run_id=name,
        directory=str(tmp_path / 'reports/physical_live_episodes' / name))]}))
    (packet / 'combined_visual_qa.jsonl').write_text('')
    with pytest.raises(ValueError, match='prespecified primary'):
        portable.build_kit(tmp_path, tmp_path / 'out.zip', packet_directory=packet, partition='development')


@pytest.mark.parametrize('change', ['none', 'omit_emission', 'failed_screen', 'wrong_plan', 'wrong_entity'])
def test_packet_admission_requires_complete_panel(tmp_path, change):
    design = portable.design_scope(OUTPUT / 'plan.json', 'development')
    names = sorted(design[1])
    audit = dict(integrity_passed=True, automatic_feasibility_passed=True,
        plan_sha256=portable.sha(design[0]), scheduled=96, calibration_eligible=False,
        rows=[dict(candidate_id=n, status='emitted' if i < 2 else 'nondetection') for i, n in enumerate(names)])
    inv = dict(runs=[dict(run_id=n) for n in names[:2]], sampling_policy=dict(
        policy_id='class-aware-design-all-emissions-v1', targets=[dict(run_id=n,
            entity_id=design[1][n]['entity_id'], frame='perception_capture/frame-000.json') for n in names[:2]]))
    if change == 'omit_emission': inv['runs'].pop()
    if change == 'failed_screen': audit['automatic_feasibility_passed'] = False
    if change == 'wrong_plan': audit['plan_sha256'] = '0' * 64
    if change == 'wrong_entity': inv['sampling_policy']['targets'][0]['entity_id'] = 'different'
    (tmp_path / 'pilot_audit.json').write_text(json.dumps(audit))
    if change == 'none':
        portable.validate_design_packet(tmp_path, design, inv)
    else:
        with pytest.raises(ValueError): portable.validate_design_packet(tmp_path, design, inv)


def test_pilot_screen_never_promotes_or_invents_negative_labels():
    observations = [dict(category=c, correct=v) for c in ('chair', 'doorway', 'laboratory_entrance', 'office_entrance')
                    for v in (1, 1, 0, 0)]
    readiness = {'excluded_counts': {'human_unreviewable': 7}}
    result = portable.pilot_human_screen(observations, readiness)
    assert result['correctness_screen_passed'] and result['unreviewable'] == 7
    assert not result['calibration_eligible'] and not result['primary_collection_authorized']
    result = portable.pilot_human_screen(observations[:-1], readiness)
    assert not result['correctness_screen_passed']
    assert result['class_outcomes']['office_entrance']['incorrect'] == 1
    readiness['excluded_counts']['pending_human_review'] = 1
    assert not portable.pilot_human_screen(observations, readiness)['correctness_screen_passed']
