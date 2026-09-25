"""Pinned-engine driver and audited completion exporter for captured S frames.

Use detector/ocr subcommands in their already-pinned isolated CPU environments.
No language prompt, model thresholds, label or inference features are changed.
"""
import argparse
import json
from pathlib import Path

from prepare_joint_score_protocol import ROOT, sha
from joint_score_collection import write_once
from joint_score_wave_s_driver import verify_inputs


def prepare(capture_root, output, config_path, preflight):
    config = json.loads(config_path.read_text()); verify_inputs(config)
    schedule = json.loads((ROOT/'reports/joint_score_protocol_20260924_v1/schedule.json').read_text())
    slots = [r for r in schedule['rows'] if r['wave'] == 'S']
    if preflight:
        slots = [r for r in slots if r['map_id']=='r3geo_base_r001' and r['seed']==101 and r['view']==0]
    records = []; pins = dict(config['input_sha256'])
    pins[str(config_path.resolve())] = sha(config_path)
    for i, slot in enumerate(slots):
        path = capture_root/(f'view-{i:02}' if preflight else slot['attempt_id'])
        summary = json.loads((path/'summary.json').read_text())
        expected = 'preflight-'+slot['acquisition_class'] if preflight else slot['attempt_id']
        if summary['attempt_id'] != expected: raise ValueError('wrong capture identity')
        record = dict(source_index=i, status='retained_source_failure', attempt_id=expected,
                      acquisition_class=slot['acquisition_class'], capture_directory=str(path.resolve()), slot=slot)
        if summary['status'] == 'captured':
            frame = path/'frame-000.json'; meta = json.loads(frame.read_text())
            record.update(status='ready', frame=str(frame.resolve()))
            for f in (frame, path/meta['rgb']['file'], path/meta['depth']['file'], path/'plan.json'):
                pins[str(f.resolve())] = sha(f)
        for f in (path/'summary.json', path/'execution.json'):
            pins[str(f.resolve())] = sha(f)
        records.append(record)
    output.mkdir(exist_ok=False)
    detector = output/'detector'; detector.mkdir()
    write_once(output/'batch.json', dict(slots=records, primary_eligible=not preflight,
        preflight_only=preflight, driver_config=str(config_path.resolve()), driver_config_sha256=sha(config_path)))
    write_once(detector/'plan.json', dict(slots=records, input_sha256=pins,
        model_path=config['detector_model_path'], text='chair. doorway. laboratory entrance. office entrance. sign. wall.',
        queries_ordered=['chair','doorway','laboratory entrance','office entrance','sign','wall'],
        box_threshold=.1, text_threshold=.25, threads=4, device='cpu',
        primary_eligible=not preflight, preflight_only=preflight))


def detector_run(output):
    import four_class_broad_detector_engine as engine
    engine.OUT=output/'detector'
    engine.run(); engine.audit()


def ocr_run(output):
    import run_entrance_context_candidate as runner
    runner.SOURCE=output/'detector'; runner.OUT=output/'ocr'
    runner.main()


def export(output):
    import yaml
    from joint_score_pipeline import process_capture, ordered_ledger
    from joint_score_components import digest
    batch=json.loads((output/'batch.json').read_text())
    config=json.loads(Path(batch['driver_config']).read_text()); verify_inputs(config)
    if sha(batch['driver_config']) != batch['driver_config_sha256']: raise ValueError('driver changed')
    dp=output/'detector'; op=output/'ocr'
    audit=json.loads((dp/'audit.json').read_text())
    if audit['reconstruction_passed'] is not True or audit['report_sha256']!=sha(dp/'report.json'):
        raise ValueError('detector reconstruction audit required')
    streams=[]; pins=[]
    for folder in (dp,op):
        plan=json.loads((folder/'plan.json').read_text()); report=json.loads((folder/'report.json').read_text())
        if report['plan_sha256']!=sha(folder/'plan.json') or report['journal_sha256']!=sha(folder/'results.jsonl'):
            raise ValueError('engine report binding')
        for path,h in plan['input_sha256'].items():
            if sha(path)!=h:raise ValueError('engine source changed')
        streams.append([json.loads(s) for s in (folder/'results.jsonl').read_text().splitlines()])
        pins.append({**plan['input_sha256'], **{str((folder/n).resolve()):sha(folder/n) for n in ('plan.json','report.json','results.jsonl')}})
    rows=[]; integration=output/'integration'; integration.mkdir()
    for slot,det,ocr in zip(batch['slots'], *streams, strict=True):
        if slot['source_index']!=det['source_index'] or slot['source_index']!=ocr['source_index']:
            raise ValueError('frame order changed')
        captured=Path(slot['capture_directory']); original=slot['slot']
        scoped=dict(original, attempt_id=slot['attempt_id'])
        detector=reader=None
        if slot['status']=='ready':
            if det['status']!='completed' or ocr['status']!='completed':raise ValueError('missing completed inference')
            raw=dp/det['raw_arrays']
            if sha(raw)!=det['raw_sha256']:raise ValueError('raw model arrays changed')
            detector=dict(status='completed', frame_sha256=sha(slot['frame']), audit_passed=True,
                input_sha256={**pins[0],str(raw.resolve()):sha(raw),str((dp/'audit.json').resolve()):sha(dp/'audit.json')}, boxes=det['boxes'])
            reader=dict(status='completed', frame_sha256=sha(slot['frame']), audit_passed=True,
                        input_sha256=pins[1], texts=ocr['texts'])
        scene=yaml.safe_load((ROOT/original['world_directory']/'landmark_scene.yaml').read_text())
        catalogue=[dict(entity_id=e['entity_id'],category=e['category'],x=e['pose']['x'],y=e['pose']['y']) for e in scene['entities']]
        result=process_capture(captured,scoped,detector,reader,nominal_mount=config['nominal_mount'],
                               rendered_mount=config['rendered_mount'],catalogue=catalogue)
        write_once(integration/f'completion-{slot["source_index"]:03}.json', dict(detector=detector,ocr=reader))
        rows.append(result)
    if batch['preflight_only']:
        value=dict(schema_version='research3-jsc-preflight-integration/v1', rows=rows,
            primary_eligible=False, human_labels_generated=False,
            integration_completed=all(r['status']=='completed' for r in rows),
            no_perception_success_quota=True)
    else:
        # Execution source chain is supplied by the primary driver, never invented.
        bindings=[]
        for item in batch['slots']:
            events=[json.loads(p.read_text()) for p in Path(item['capture_directory']).glob('event-*.json')]
            admitted=[e for e in events if e['kind']=='admission']
            if len(admitted)!=1:raise ValueError('each primary attempt requires its actual admission record')
            bindings.append(admitted[0]['execution_manifest_sha256'])
        if len(set(bindings))!=1:raise ValueError('mixed execution manifests')
        schedule_path=ROOT/'reports/joint_score_protocol_20260924_v1/schedule.json'
        value=ordered_ledger(json.loads(schedule_path.read_text()),rows, schedule_sha256=sha(schedule_path),
            protocol_sha256=sha(ROOT/'docs/SCORE_LEARNING_COLLECTION_PROTOCOL_20260924.md'),
            execution_manifest_sha256=bindings[0])
    write_once(output/'evidence.json',value)
    print(json.dumps(dict(attempts=len(rows), completed=sum(r['status']=='completed' for r in rows),
        emissions=sum(len(r['emissions']) for r in rows), primary_eligible=not batch['preflight_only']),indent=2))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('prepare','detector','ocr','export'))
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--capture-root',type=Path);p.add_argument('--config',type=Path)
    p.add_argument('--preflight',action='store_true')
    a=p.parse_args()
    if a.action=='prepare':
        if not a.capture_root or not a.config:p.error('capture-root and config required')
        prepare(a.capture_root,a.output,a.config,a.preflight)
    elif a.action=='detector':detector_run(a.output)
    elif a.action=='ocr':ocr_run(a.output)
    else:export(a.output)


if __name__=='__main__': main()
