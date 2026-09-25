from copy import deepcopy
import json

import pytest

from prepare_joint_score_protocol import ROOT, SOURCE, make_schedule, validate_schedule


@pytest.fixture
def source():
    # Pose metadata only; no observations, outcomes or validation plaintext.
    return json.loads((ROOT / SOURCE).read_text())


def test_fixed_counts_roles_and_disjoint_attempt_ids(source):
    plan = make_schedule(source)
    assert plan['counts'] == {'S': 400, 'C': 400, 'V': 160}
    assert len({r['attempt_id'] for r in plan['rows']}) == 960
    assert {r['seed'] for r in plan['rows']} == {101, 102, 201, 202, 301, 302}
    assert all(r['human_label'] is None and not r['execution_authorized'] for r in plan['rows'])
    assert validate_schedule(plan, source)['execution_armed'] is False
    assert plan == make_schedule(source)


@pytest.mark.parametrize('mutation', ['seed', 'pose', 'label', 'authority', 'order', 'map', 'drop'])
def test_tampered_schedule_rejected(source, mutation):
    plan = make_schedule(source)
    row = plan['rows'][0]
    if mutation == 'seed':
        row['seed'] = 301
    elif mutation == 'pose':
        row['capture_pose']['x'] += 0.1
    elif mutation == 'label':
        row['human_label'] = 'correct'
    elif mutation == 'authority':
        plan['execution_authorized'] = True
    elif mutation == 'order':
        plan['rows'].reverse()
    elif mutation == 'map':
        row['map_id'] = 'r3geo_base_r015'
    else:
        plan['rows'].pop()
    with pytest.raises(ValueError):
        validate_schedule(plan, source)


@pytest.mark.parametrize('mutation', ['duplicate', 'missing', 'protected', 'nan', 'seed', 'category'])
def test_bad_source_rejected(source, mutation):
    source = deepcopy(source)
    row = source['rows'][0]
    if mutation == 'duplicate':
        source['rows'].append(deepcopy(row))
    elif mutation == 'missing':
        source['rows'].pop(0)
    elif mutation == 'protected':
        row['map_id'] = 'r3geo_base_r015'
    elif mutation == 'nan':
        row['capture_pose']['x'] = float('nan')
    elif mutation == 'seed':
        row['seed'] = True
    else:
        row['category'] = 'sphere'
    with pytest.raises(ValueError):
        make_schedule(source)


def test_no_label_or_old_world_hash_transfer(source):
    source['rows'][0]['human_label'] = 'incorrect'
    plan = make_schedule(source)
    assert all(r['human_label'] is None for r in plan['rows'])
    assert all('world_sha256' not in r and 'entity_id' not in r for r in plan['rows'])
    assert all(r['execution_manifest_sha256'] is None for r in plan['rows'])
