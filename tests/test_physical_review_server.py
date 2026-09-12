import importlib.util
from io import BytesIO
import json
from pathlib import Path
import threading
import re
import shutil
import subprocess
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from PIL import Image
import pytest


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


ROOT = Path(__file__).resolve().parents[1]
UI = module('physical_review_ui', ROOT / 'scripts/serve_physical_review.py')
FIXTURES = module('synthetic_review_fixture', ROOT / 'tests/test_consolidated_review.py')
capture = FIXTURES.capture


@pytest.fixture
def store(capture):
    qa = FIXTURES.synthetic_qa(capture)
    qa_path = capture / 'qa.jsonl'
    qa_path.write_text(json.dumps(qa))
    inventory = UI._INVENTORY.consolidate([capture], [qa])
    inventory_path = capture / 'inventory.json'
    inventory_path.write_text(json.dumps(inventory))
    return UI.ReviewStore(inventory_path, qa_path, capture / 'new-human-progress.jsonl')


def test_get_state_and_image_never_write_labels(store):
    before = store.progress.read_bytes()
    state = store.state()
    assert state['items'][0]['correct'] is None
    assert state['items'][0]['review'] is None
    assert state['items'][0]['source'] == 'rgbd'
    image = Image.open(BytesIO(store.png(0)))
    assert image.size == (2, 2)
    assert image.tobytes() == bytes(12)
    assert store.progress.read_bytes() == before


@pytest.mark.parametrize('verdict,correct', [('correct', True), ('incorrect', False),
                                           ('unreviewable', None)])
def test_only_explicit_synthetic_choices_append_audit(store, verdict, correct):
    prefix = store.progress.read_bytes()
    event = store.review(0, {'reviewer_id': 'Synthetic test reviewer', 'verdict': verdict,
                             'notes': 'Unit-test fixture, not real review'})
    assert event['correct'] is correct
    assert store.progress.read_bytes().startswith(prefix)
    assert store.state()['reviewed'] == 1


@pytest.mark.parametrize('patch', [
    {'reviewer_id': '', 'verdict': 'correct', 'notes': ''},
    {'reviewer_id': 'Test', 'verdict': None, 'notes': ''},
    {'reviewer_id': 'Test', 'verdict': 'correct', 'notes': '', 'category': 'chair'},
    {'reviewer_id': 'Test', 'correct': True},
])
def test_invalid_or_extra_fields_never_write(store, patch):
    before = store.progress.read_bytes()
    with pytest.raises(ValueError):
        store.review(0, patch)
    assert store.progress.read_bytes() == before


def test_stale_raw_frame_blocks_reads_and_writes(store):
    raw = next(iter(store.runs.values())) / 'perception_capture/rgb.bin'
    raw.write_bytes(b'changed')
    before = store.progress.read_bytes()
    with pytest.raises(ValueError, match='stale'):
        store.state()
    with pytest.raises(ValueError):
        store.review(0, {'reviewer_id': 'Test', 'verdict': 'correct', 'notes': ''})
    assert store.progress.read_bytes() == before


def test_create_once_and_explicit_resume(store):
    with pytest.raises(FileExistsError):
        UI.ReviewStore(store.inventory, store.qa, store.progress)
    resumed = UI.ReviewStore(store.inventory, store.qa, store.progress, resume=True)
    assert resumed.state()['items'][0]['review'] is None


def test_inventory_mutation_and_unready_items_rejected(store):
    original = store.inventory.read_text()
    inventory = json.loads(original)
    inventory['items'][0]['category'] = 'fabricated'
    store.inventory.write_text(json.dumps(inventory))
    with pytest.raises(ValueError):
        store.validate()
    with pytest.raises(ValueError, match='stale'):
        UI.ReviewStore(store.inventory, store.qa, store.progress.parent / 'other.jsonl')


def test_equal_weight_choices_no_answer_key_or_default():
    assert 'data-verdict="correct"' in UI.PAGE
    assert 'data-verdict="incorrect"' in UI.PAGE
    assert 'data-verdict="unreviewable"' in UI.PAGE
    assert 'entity_marker_rgb' not in UI.PAGE
    assert 'expected_route' not in UI.PAGE
    assert 'ground_truth' not in UI.PAGE
    assert 'No verdict selected.' in UI.PAGE


def test_http_get_does_not_write_and_patch_requires_local_token(store):
    try:
        server = UI.ThreadingHTTPServer(('127.0.0.1', 0), UI.handler_for(store))
    except PermissionError:
        pytest.skip('loopback sockets unavailable in sandbox; run this test with socket permission')
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    address = f'http://127.0.0.1:{server.server_port}'
    before = store.progress.read_bytes()
    try:
        with urlopen(address + '/api/state') as response:
            state = json.load(response)
        with urlopen(address + '/') as response:
            assert b'Physical landmark review' in response.read()
        assert store.progress.read_bytes() == before
        body = json.dumps({'reviewer_id': 'Synthetic API test', 'verdict': 'unreviewable',
                           'notes': 'Synthetic test only'}).encode()
        with pytest.raises(HTTPError) as error:
            urlopen(Request(address + '/api/review/0', data=body, method='PATCH'))
        assert error.value.code == 403
        with pytest.raises(HTTPError) as error:
            urlopen(Request(address + '/api/review/0', data=body, method='PATCH', headers={
                'X-Review-Token': state['token'], 'Origin': 'https://untrusted.example'}))
        assert error.value.code == 403
        with urlopen(Request(address + '/api/review/0', data=body, method='PATCH', headers={
                'X-Review-Token': state['token']})) as response:
            assert json.load(response)['correct'] is None
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_item_selector_has_category_labels_without_answer_hints():
    assert 'label for="item-selector">Jump to item' in UI.PAGE
    assert 'Next unreviewed' in UI.PAGE
    assert 'option.textContent=`${index+1}. ${item.category.replaceAll' in UI.PAGE
    assert 'option.textContent=`${item.review' not in UI.PAGE
    assert 'if(initial)position=Math.max(0,firstUnreviewed(state.items))' in UI.PAGE
    assert "if(busy){$('item-selector').value=String(position);return}" in UI.PAGE


def test_navigation_helpers_find_first_pending_wrap_and_handle_complete():
    node = shutil.which('node')
    if node is None:
        pytest.skip('Node unavailable for pure JavaScript navigation unit test')
    helpers = '\n'.join(re.findall(r'^function (?:firstUnreviewed|nextUnreviewed).*$', UI.PAGE, re.M))
    # Pure functions, no browser/server/real review input or output.
    script = helpers + '''
const items=Array.from({length:60},(_,i)=>({review:i<56?{verdict:'unreviewable'}:null}));
console.log(JSON.stringify({first:firstUnreviewed(items),next:nextUnreviewed(items,56),
wrap:nextUnreviewed(items,59),complete:firstUnreviewed([{review:{}}]),
completeNext:nextUnreviewed([{review:{}}],0),empty:nextUnreviewed([],0),
onlyCurrent:nextUnreviewed([{review:null}],0)}));
'''
    result = subprocess.run([node, '-e', script], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == {'first': 56, 'next': 57, 'wrap': 56,
        'complete': -1, 'completeNext': -1, 'empty': -1, 'onlyCurrent': 0}


def test_image_gate_blocks_loading_errors_and_stale_load_events():
    node = shutil.which('node')
    if node is None:
        pytest.skip('Node unavailable for pure JavaScript image state test')
    helper = re.search(r'^function createImageGate.*$', UI.PAGE, re.M).group()
    script = helper + '''
const gate=createImageGate(), results=[gate.canReview()];
const first=gate.begin();results.push(gate.canReview());
const second=gate.begin();results.push(gate.settle(first,true),gate.canReview());
results.push(gate.settle(second,false),gate.canReview());
const third=gate.begin();results.push(gate.settle(third,true),gate.canReview());
results.push(gate.settle(second,false),gate.canReview());
gate.begin();results.push(gate.canReview());
console.log(JSON.stringify(results));
'''
    result = subprocess.run([node, '-e', script], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == [False, False, False, False, True, False,
                                        True, True, False, True, False]
    assert 'if(busy||!imageGate.canReview())return' in UI.PAGE
    assert 'button.disabled=busy||!imageGate.canReview()' in UI.PAGE
    assert "addEventListener('load',()=>finishImage(true)" in UI.PAGE
    assert "addEventListener('error',()=>finishImage(false)" in UI.PAGE
    assert 'Image could not load. Verdicts are unavailable.' in UI.PAGE
    for verdict in ('correct', 'incorrect', 'unreviewable'):
        assert f'data-verdict="{verdict}" disabled' in UI.PAGE
