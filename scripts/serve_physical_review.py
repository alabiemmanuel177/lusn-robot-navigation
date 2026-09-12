#!/usr/bin/env python3
"""Loopback-only human review of hash-revalidated, individually QA-ready items."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
from io import BytesIO
import json
import os
from pathlib import Path
import secrets
import threading

from PIL import Image

_SPEC = importlib.util.spec_from_file_location('physical_inventory', Path(__file__).with_name(
    'prepare_consolidated_review.py'))
_INVENTORY = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_INVENTORY)
_JOINT_SPEC = importlib.util.spec_from_file_location('joint_evidence', Path(__file__).with_name('prepare_joint_review_evidence.py'))
_JOINT = importlib.util.module_from_spec(_JOINT_SPEC)
_JOINT_SPEC.loader.exec_module(_JOINT)
DIMENSIONS = ('category', 'entity_association', 'pose')


def joint_verdict(dimensions):
    if (not isinstance(dimensions, dict) or set(dimensions) != set(DIMENSIONS)
            or any(value not in ('correct', 'incorrect', 'unreviewable') for value in dimensions.values())):
        raise ValueError('three explicit dimension verdicts required')
    return ('incorrect' if 'incorrect' in dimensions.values() else
            'correct' if all(value == 'correct' for value in dimensions.values()) else 'unreviewable')


def load_json(path):
    return json.loads(Path(path).read_text())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ReviewStore:
    def __init__(self, inventory, qa, progress, *, resume=False, evidence=None, policy=None):
        self.inventory, self.qa, self.progress = map(Path, (inventory, qa, progress))
        self.lock = threading.Lock()
        self.token = secrets.token_urlsafe(32)
        self.inventory_hash, self.qa_hash = digest(self.inventory), digest(self.qa)
        if (evidence is None) != (policy is None):
            raise ValueError('joint evidence and policy must be supplied together')
        self.evidence = Path(evidence) if evidence else None
        self.policy = Path(policy) if policy else None
        self.evidence_hash = digest(self.evidence) if evidence else None
        self.policy_hash = digest(self.policy) if policy else None
        self.items, self.runs = self.validate()
        if not self.items:
            raise ValueError('no individually QA-ready items; do not start human review')
        header = {'schema_version': 'research3-physical-human-review-audit/v1',
                  'inventory_sha256': self.inventory_hash, 'qa_sha256': self.qa_hash}
        if self.evidence:
            self.validate_joint()
            header.update(schema_version='research3-physical-human-review-audit/v2',
                          evidence_sha256=self.evidence_hash, policy_sha256=self.policy_hash)
        if resume:
            if self.events()[0] != header:
                raise ValueError('progress belongs to different inventory or QA input')
        else:
            with self.progress.open('x') as stream:
                stream.write(json.dumps(header, sort_keys=True) + '\n')

    def validate_joint(self):
        if digest(self.evidence) != self.evidence_hash or digest(self.policy) != self.policy_hash:
            raise ValueError('joint evidence or policy changed')
        evidence = load_json(self.evidence)
        if evidence != _JOINT.build(self.inventory):
            raise ValueError('stale joint reference evidence')
        policy = load_json(self.policy)
        return evidence['items'], policy, _JOINT.validate_policy(policy)

    def validate(self):
        if digest(self.inventory) != self.inventory_hash or digest(self.qa) != self.qa_hash:
            raise ValueError('inventory or QA input changed')
        inventory = load_json(self.inventory)
        if (inventory.get('schema_version') != 'research3-consolidated-review-inventory/v1'
                or inventory.get('protected_data_used') is not False):
            raise ValueError('invalid or protected inventory')
        qa_rows = [json.loads(line) for line in self.qa.read_text().splitlines() if line.strip()]
        sampling = inventory.get('sampling_policy')
        if sampling is not None or inventory.get('sampling_policy_sha256') is not None:
            _INVENTORY.validate_sampling_policy(sampling)
            if sampling is None or _INVENTORY.task_digest(sampling) != inventory.get('sampling_policy_sha256'):
                raise ValueError('embedded sampling policy checksum mismatch')
        fresh = _INVENTORY.consolidate(
            [row['directory'] for row in inventory['runs']], qa_rows,
            required_maps=inventory['required_maps'], required_classes=inventory['required_classes'],
            sampling_policy=sampling)
        if inventory.get('qa_input_sha256', self.qa_hash) != self.qa_hash:
            raise ValueError('QA input checksum mismatch')
        if fresh['runs'] != inventory['runs'] or fresh['items'] != inventory['items']:
            raise ValueError('stale inventory: source, frame, task or individual QA changed')
        ready = [row for row in fresh['items'] if row['status'] == 'ready_for_human_review']
        return ready, {row['run_id']: Path(row['directory']) for row in fresh['runs']
                       if row.get('run_id')}

    def events(self):
        return [json.loads(line) for line in self.progress.read_text().splitlines() if line.strip()]

    def state(self):
        with self.lock:
            items, _ = self.validate()
            verdicts = {}
            for event in self.events()[1:]:
                verdicts[event['item_index']] = event
            tasks = []
            joint_rows, policy, approved = self.validate_joint() if self.evidence else ([], {}, False)
            for index, item in enumerate(items):
                run = self.runs[item['run_id']]
                raw_tasks = [json.loads(line) for line in
                             (run / 'landmark_review_tasks.jsonl').read_text().splitlines()
                             if line.strip()]
                task = next(row for row in raw_tasks
                            if row['observation_id'] == item['observation_id'])
                frame = load_json(run / item['frame'])
                tasks.append({**item, 'index': index, 'source': task['source'],
                              'width': frame['rgb']['width'], 'height': frame['rgb']['height'],
                              'review': verdicts.get(index), 'image_url': f'/frame/{index}.png'})
                if self.evidence:
                    evidence = joint_rows[index]
                    tasks[-1].update(joint_evidence=evidence,
                                     joint_policy_approved=approved,
                                     joint_review_allowed=approved and evidence['evidence_complete'])
            return {'items': tasks, 'token': self.token,
                    'reviewed': len(verdicts), 'inventory_sha256': self.inventory_hash,
                    'joint_review': bool(self.evidence), 'joint_policy': policy}

    def png(self, index):
        items, _ = self.validate()
        if type(index) is not int or not 0 <= index < len(items):
            raise ValueError('unknown item')
        item = items[index]
        frame_path = self.runs[item['run_id']] / item['frame']
        info = load_json(frame_path)['rgb']
        raw = _INVENTORY._JOIN.local_file(frame_path.parent, info['file']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != info['sha256']:
            raise ValueError('RGB source changed')
        mode = {'rgb8': 'RGB', 'bgr8': 'BGR'}.get(info['encoding'])
        if mode is None:
            raise ValueError('unsupported RGB encoding')
        source = Image.frombytes('RGB', (info['width'], info['height']), raw,
                                 'raw', mode, info['step'], 1)
        output = BytesIO()
        source.save(output, format='PNG')
        return output.getvalue()

    def review(self, index, fields):
        expected = {'reviewer_id', 'dimension_verdicts', 'notes'} if self.evidence else {'reviewer_id', 'verdict', 'notes'}
        if not isinstance(fields, dict) or set(fields) != expected:
            raise ValueError('only reviewer_id, verdict and notes are editable')
        reviewer, notes = fields['reviewer_id'], fields['notes']
        verdict = joint_verdict(fields['dimension_verdicts']) if self.evidence else fields['verdict']
        if (not isinstance(reviewer, str) or not reviewer.strip() or len(reviewer) > 100
                or verdict not in ('correct', 'incorrect', 'unreviewable')
                or not isinstance(notes, str) or len(notes) > 2000):
            raise ValueError('provide reviewer name, explicit verdict and valid notes')
        with self.lock:
            items, _ = self.validate()
            if type(index) is not int or not 0 <= index < len(items):
                raise ValueError('unknown item')
            item = items[index]
            extra = {}
            if self.evidence:
                joint_rows, _, approved = self.validate_joint()
                row = joint_rows[index]
                if not approved:
                    raise ValueError('policy approval pending: preview only; no judgments may be saved')
                if not row['evidence_complete'] and any(value != 'unreviewable' for value in fields['dimension_verdicts'].values()):
                    raise ValueError('missing reference evidence or approved policy: unreviewable only')
                extra = {'dimension_verdicts': fields['dimension_verdicts'],
                         'evidence_sha256': self.evidence_hash, 'policy_sha256': self.policy_hash,
                         'item_evidence_sha256': _JOINT.object_hash(row)}
            event = {'item_index': index, 'run_id': item['run_id'],
                     'observation_id': item['observation_id'], 'task_sha256': item['task_sha256'],
                     'frame_sha256': item['frame_sha256'], 'reviewer_id': reviewer.strip(),
                     'verdict': verdict, 'notes': notes,
                     'correct': True if verdict == 'correct' else False if verdict == 'incorrect' else None,
                     'review_status': 'human_unreviewable' if verdict == 'unreviewable' else 'human_verified',
                     'recorded_at': datetime.now(timezone.utc).isoformat(), **extra}
            # Never replace the inventory, provider rows, or an earlier human verdict.
            with self.progress.open('a') as stream:
                stream.write(json.dumps(event, sort_keys=True, allow_nan=False) + '\n')
                stream.flush()
                os.fsync(stream.fileno())
            return event


def handler_for(store):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, status, body, content_type='application/json'):
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)

        def local_request(self):
            host = self.headers.get('Host', '').split(':')[0]
            origin = self.headers.get('Origin')
            return host in ('127.0.0.1', 'localhost') and (
                origin is None or origin == 'http://' + self.headers.get('Host', ''))

        def do_GET(self):
            if not self.local_request():
                self.send(403, b'{"error":"local origin required"}')
                return
            try:
                if self.path == '/':
                    self.send(200, PAGE.encode(), 'text/html; charset=utf-8')
                elif self.path == '/api/state':
                    self.send(200, json.dumps(store.state()).encode())
                elif self.path.startswith('/frame/') and self.path.endswith('.png'):
                    self.send(200, store.png(int(self.path[7:-4])), 'image/png')
                else:
                    self.send(404, b'{"error":"not found"}')
            except (ValueError, OSError, KeyError, StopIteration) as exc:
                self.send(409, json.dumps({'error': str(exc)}).encode())

        def do_PATCH(self):
            if not self.local_request() or self.headers.get('X-Review-Token') != store.token:
                self.send(403, b'{"error":"local review token required"}')
                return
            try:
                if not self.path.startswith('/api/review/'):
                    self.send(404, b'{"error":"not found"}')
                    return
                length = int(self.headers.get('Content-Length', 0))
                if not 0 < length <= 8192:
                    raise ValueError('invalid request length')
                result = store.review(int(self.path[12:]), json.loads(self.rfile.read(length)))
                self.send(200, json.dumps(result).encode())
            except (ValueError, OSError, KeyError) as exc:
                self.send(400, json.dumps({'error': str(exc)}).encode())
    return Handler


PAGE = r'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Physical landmark review</title>
<style>
:root{color:#17324d;background:#fff;font:17px/1.5 "Trebuchet MS",sans-serif}*{box-sizing:border-box}
[hidden]{display:none!important}
#joint-reference{grid-column:1 / -1;min-width:0;border-top:2px solid #667c91;padding-top:20px}
#coordinate-map{width:100%;min-height:300px}#coordinate-legend{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:8px 24px;padding-left:25px;font-size:15px;overflow-wrap:anywhere}
body{margin:0}header{padding:20px 4vw;background:#edf3f8}h1{font-size:25px;margin:0}
main{max-width:1450px;margin:auto;padding:24px 4vw;display:grid;grid-template-columns:minmax(0,3fr) minmax(250px,1fr);gap:28px}
figure{margin:0}svg{width:100%;height:auto;display:block;background:#d8e2eb}figcaption{font-size:14px;padding-top:10px}
label{display:block;margin:16px 0 5px}input,textarea,select{font:inherit;width:100%;padding:9px;border:1px solid #667c91}
button{font:inherit;padding:10px 15px;background:#fff;color:#17324d;border:2px solid #476581;cursor:pointer;border-radius:4px}
button:hover{background:#edf3f8}button:focus-visible,input:focus-visible,textarea:focus-visible,select:focus-visible{outline:3px solid #926500;outline-offset:3px}
.choices{display:flex;flex-wrap:wrap;gap:10px;margin:20px 0}.nav{display:flex;justify-content:space-between;margin-top:18px}
dl{font-size:14px;overflow-wrap:anywhere}dt{font-weight:bold;margin-top:9px}dd{margin:0}#feedback{min-height:2em;color:#713d00}
#claim{font-size:24px;line-height:1.3}button:disabled{opacity:.5;cursor:wait}.hint{max-width:70ch}
@media(max-width:850px){main{grid-template-columns:1fr}header{padding:16px}main{padding:16px}}
</style><header><h1>Physical landmark review</h1><div id="progress">Loading verified items…</div></header>
<main><section><label for="item-selector">Jump to item</label><select id="item-selector" disabled aria-label="Jump to item"></select>
<button id="next-unreviewed" disabled>Next unreviewed</button>
<figure><svg id="frame" role="img" aria-label="Original camera frame with detector crosshair"></svg>
<p id="image-status" role="status" aria-live="polite">Loading image… Verdicts are unavailable.</p>
<figcaption>Full original camera frame. The crosshair marks the detector’s reported pixel, not a suggested answer.</figcaption></figure>
<div class="nav"><button id="previous">Previous item</button><button id="marker">Hide crosshair</button><button id="next">Next item</button></div>
<dl id="metadata"></dl></section><section><div id="claim"></div>
<p class="hint">Review all three claims: object category, stable entity association, and map-frame pose under the approved policy. Colour alone is not enough. The catalogue is reference evidence, never a human verdict. Reported yaw comes from the catalogue, not an independent orientation estimate.</p>
<div id="dimensions"></div><button id="save-joint" disabled>Save three judgments</button>
<label for="reviewer">Your name</label><input id="reviewer" autocomplete="name" maxlength="100">
<label for="notes">Notes (optional)</label><textarea id="notes" rows="3" maxlength="2000"></textarea>
<div class="choices"><button data-verdict="correct" disabled>Correct</button><button data-verdict="incorrect" disabled>Incorrect</button><button data-verdict="unreviewable" disabled>Unreviewable</button></div>
<p id="saved">No verdict selected.</p><p id="feedback" role="status" aria-live="polite"></p>
</section><section id="joint-reference"><h2>Coordinate reference</h2><p id="policy-status"></p><svg id="coordinate-map" role="img" aria-label="Map-frame catalogue references and reported observation"></svg><ol id="coordinate-legend"></ol><pre id="reference-details" style="white-space:pre-wrap;overflow-wrap:anywhere;font:16px/1.5 sans-serif"></pre></section></main><script>
let state=null,position=0,showMarker=true,busy=false;const $=id=>document.getElementById(id);
const ns='http://www.w3.org/2000/svg';
function firstUnreviewed(items){return items.findIndex(item=>!item.review)}
function nextUnreviewed(items,current){for(let step=1;step<=items.length;step++){const index=(current+step)%items.length;if(!items[index].review)return index}return -1}
function createImageGate(){let generation=0,ready=false;return {begin(){ready=false;return ++generation},settle(token,success){if(token!==generation)return false;ready=success;return true},canReview(){return ready}}}
const imageGate=createImageGate();
function updateVerdicts(){document.querySelectorAll('[data-verdict]').forEach(button=>button.disabled=busy||!imageGate.canReview()||state?.joint_review);$('save-joint').disabled=busy||!imageGate.canReview()||(state?.joint_review&&!state.items[position].joint_policy_approved)}
function imageStatus(success,joint,approved){return !success?'Image could not load. Verdicts are unavailable. Select another item and return to retry.':joint&&!approved?'Image loaded for preview only. Policy approval pending; saving is disabled.':'Image loaded. You may review this item.'}
function element(tag,attrs){const e=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);return e}
function render(){const t=state.items[position];$('progress').textContent=`Item ${position+1} of ${state.items.length} • ${state.reviewed} reviewed`;
const selector=$('item-selector');selector.replaceChildren();state.items.forEach((item,index)=>{const option=document.createElement('option');option.value=String(index);option.textContent=`${index+1}. ${item.category.replaceAll('_',' ')} (${item.map_id})`;selector.append(option)});selector.value=String(position);selector.disabled=busy;
const pendingIndex=nextUnreviewed(state.items,position);$('next-unreviewed').disabled=busy||pendingIndex<0||pendingIndex===position;
$('claim').textContent=`Review observation claimed as “${t.category.replaceAll('_',' ')}”`;
document.querySelector('.choices').hidden=state.joint_review;$('joint-reference').hidden=!state.joint_review;$('dimensions').hidden=!state.joint_review;$('save-joint').hidden=!state.joint_review;
if(state.joint_review){const evidence=t.joint_evidence;$('policy-status').textContent=!t.joint_policy_approved?'Policy approval pending. Preview only: do not spend time judging these items yet. Saving is disabled.':t.joint_review_allowed?'Apply this approved policy: '+JSON.stringify(state.joint_policy):'Missing reference evidence. Only Unreviewable can be saved.';
$('reference-details').textContent=evidence.evidence_complete?`Claimed entity: ${evidence.observation.entity_id}\nClaimed region: ${evidence.observation.region_id}\nReported x/y (m): ${evidence.observation.x.toFixed(3)}, ${evidence.observation.y.toFixed(3)}\nCatalogue x/y (m): ${evidence.selected_reference.pose.x.toFixed(3)}, ${evidence.selected_reference.pose.y.toFixed(3)}\nCatalogue entity: ${evidence.selected_reference.entity_id}\nCatalogue region: ${evidence.selected_reference.region_id}\nReported yaw (rad): ${evidence.observation.yaw.toFixed(3)} — catalogue supplied, not independently estimated\nCovariance: ${JSON.stringify(evidence.observation.covariance)}\nCapture pose: ${JSON.stringify(evidence.capture_pose)}\nScene SHA256: ${evidence.runtime_scene_sha256}\nReference only: a human must judge association and pose under the approved policy.`:evidence.gaps.join('\n');const map=$('coordinate-map');map.replaceChildren();map.setAttribute('viewBox','0 0 650 300');
if(evidence.evidence_complete){const refs=evidence.references,obs=evidence.observation;const xs=refs.map(r=>r.pose.x).concat(obs.x),ys=refs.map(r=>r.pose.y).concat(obs.y);const minX=Math.min(...xs)-1,maxX=Math.max(...xs)+1,minY=Math.min(...ys)-1,maxY=Math.max(...ys)+1;const px=x=>30+(x-minX)/(maxX-minX)*590,py=y=>270-(y-minY)/(maxY-minY)*240;
$('coordinate-legend').replaceChildren();for(const [index,ref] of refs.entries()){map.append(element('circle',{cx:px(ref.pose.x),cy:py(ref.pose.y),r:4,fill:'#17324d'}));const text=element('text',{x:px(ref.pose.x)+6,y:py(ref.pose.y)+(index%2?-10:19),'font-size':16});text.textContent=String(index+1);map.append(text);const entry=document.createElement('li');entry.textContent=`${ref.entity_id} — ${ref.category.replaceAll('_',' ')}; x ${ref.pose.x.toFixed(2)} m, y ${ref.pose.y.toFixed(2)} m`;if(ref.entity_id===obs.entity_id){entry.style.fontWeight='bold';entry.textContent+=' (claimed association)'}$('coordinate-legend').append(entry)}
map.append(element('path',{d:`M ${px(obs.x)-8} ${py(obs.y)} h 16 M ${px(obs.x)} ${py(obs.y)-8} v 16`,stroke:'#a34d00','stroke-width':3}));const legend=element('text',{x:10,y:295,'font-size':12});legend.textContent='Map metres: x increases right; y increases up. Dots: catalogue. Cross: reported x/y. Not to scale with camera.';map.append(legend)}
$('dimensions').replaceChildren();for(const key of ['category','entity_association','pose']){const label=document.createElement('label');label.textContent=key.replaceAll('_',' ');const select=document.createElement('select');select.id='dimension-'+key;for(const value of ['', 'correct','incorrect','unreviewable']){const option=document.createElement('option');option.value=value;option.textContent=value||'Choose a judgment';option.disabled=!t.joint_review_allowed&&value!==''&&value!=='unreviewable';select.append(option)}select.value=t.review?.dimension_verdicts?.[key]||'';label.append(select);$('dimensions').append(label)}}
$('notes').value=t.review?.notes||'';$('saved').textContent=t.review?`Saved: ${t.review.verdict} by ${t.review.reviewer_id}`:'No verdict selected.';
const svg=$('frame');svg.replaceChildren();svg.setAttribute('viewBox',`0 0 ${t.width} ${t.height}`);
const imageToken=imageGate.begin();updateVerdicts();svg.setAttribute('aria-busy','true');$('image-status').textContent='Loading image… Verdicts are unavailable.';
const frameImage=element('image',{x:0,y:0,width:t.width,height:t.height});
const finishImage=success=>{if(!imageGate.settle(imageToken,success))return;svg.setAttribute('aria-busy','false');$('image-status').textContent=imageStatus(success,state.joint_review,t.joint_policy_approved);updateVerdicts()};
frameImage.addEventListener('load',()=>finishImage(true),{once:true});frameImage.addEventListener('error',()=>finishImage(false),{once:true});svg.append(frameImage);frameImage.setAttribute('href',t.image_url);
if(showMarker){const u=t.pixel.u+.5,v=t.pixel.v+.5;for(const stroke of ['#17324d','#ffdf40']){const g=element('g',{stroke,'stroke-width':stroke==='#17324d'?4:2,fill:'none'});g.append(element('circle',{cx:u,cy:v,r:10}),element('path',{d:`M ${u-18} ${v} h 12 M ${u+6} ${v} h 12 M ${u} ${v-18} v 12 M ${u} ${v+6} v 12`}));svg.append(g)}}
$('metadata').replaceChildren();for(const[label,value]of [['Claimed class',t.category],['Source',t.source],['Run',t.run_id],['Map',t.map_id],['Observation',t.observation_id]]){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=value;$('metadata').append(dt,dd)}
$('previous').disabled=position===0||busy;$('next').disabled=position===state.items.length-1||busy;
}
async function load(){const initial=state===null;const response=await fetch('/api/state');state=await response.json();if(!response.ok)throw Error(state.error);if(initial)position=Math.max(0,firstUnreviewed(state.items));render()}
$('save-joint').onclick=async()=>{if(busy||!imageGate.canReview())return;const dimensions=Object.fromEntries(['category','entity_association','pose'].map(key=>[key,$('dimension-'+key).value]));if(Object.values(dimensions).some(value=>!value)||!$('reviewer').value.trim()){$('feedback').textContent='Enter your name and explicitly choose all three judgments.';return}busy=true;updateVerdicts();try{const response=await fetch('/api/review/'+state.items[position].index,{method:'PATCH',headers:{'Content-Type':'application/json','X-Review-Token':state.token},body:JSON.stringify({reviewer_id:$('reviewer').value,notes:$('notes').value,dimension_verdicts:dimensions})});const result=await response.json();if(!response.ok)throw Error(result.error);await load();$('feedback').textContent='Three judgments saved.'}catch(error){$('feedback').textContent=error.message}finally{busy=false;render()}};
for(const button of document.querySelectorAll('[data-verdict]'))button.onclick=async()=>{if(busy||!imageGate.canReview())return;if(!$('reviewer').value.trim()){$('feedback').textContent='Enter your name before saving a verdict.';$('reviewer').focus();return}busy=true;document.querySelectorAll('button').forEach(b=>b.disabled=true);try{const response=await fetch('/api/review/'+state.items[position].index,{method:'PATCH',headers:{'Content-Type':'application/json','X-Review-Token':state.token},body:JSON.stringify({reviewer_id:$('reviewer').value,verdict:button.dataset.verdict,notes:$('notes').value})});const result=await response.json();if(!response.ok)throw Error(result.error);await load();$('feedback').textContent='Verdict saved. Use Next item when ready.'}catch(e){$('feedback').textContent=e.message}finally{busy=false;document.querySelectorAll('button:not([data-verdict])').forEach(b=>b.disabled=false);if(state)render()}};
$('item-selector').onchange=()=>{if(busy){$('item-selector').value=String(position);return}position=Number($('item-selector').value);render()};
$('next-unreviewed').onclick=()=>{if(busy)return;const index=nextUnreviewed(state.items,position);if(index>=0){position=index;render()}};
$('previous').onclick=()=>{if(busy)return;position--;render()};$('next').onclick=()=>{if(busy)return;position++;render()};$('marker').onclick=()=>{if(busy)return;const draft=$('notes').value;showMarker=!showMarker;$('marker').textContent=showMarker?'Hide crosshair':'Show crosshair';render();$('notes').value=draft};
load().catch(e=>{$('feedback').textContent='Review unavailable: '+e.message;document.querySelectorAll('button').forEach(b=>b.disabled=true)});
</script></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', required=True, type=Path)
    parser.add_argument('--qa', required=True, type=Path)
    parser.add_argument('--progress', required=True, type=Path)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--evidence', required=True, type=Path)
    parser.add_argument('--policy', required=True, type=Path)
    parser.add_argument('--port', type=int, default=8793)
    args = parser.parse_args()
    store = ReviewStore(args.inventory, args.qa, args.progress, resume=args.resume,
                        evidence=args.evidence, policy=args.policy)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), handler_for(store))
    print(f'Human review: http://127.0.0.1:{server.server_port}/', flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
