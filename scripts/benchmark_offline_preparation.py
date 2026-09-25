"""Bounded development-image concurrency measurement; no simulator or labels."""
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import statistics
import threading
import time

ROOT=Path(__file__).resolve().parents[1]


def image_work(path):
    import numpy as np
    from expansion_rendered_checks import decode_frame, colour_mask
    image,_=decode_frame(path)
    # Fixed synthetic palette probes exercise the existing pixel-QA operation.
    # This returns workload checksums, never a scientific visual attestation.
    masks=[int(colour_mask(image,c).sum()) for c in ([107,45,45],[78,44,87],[92,42,76],[39,90,79])]
    return hashlib.sha256(json.dumps([float(np.std(image)),masks]).encode()).hexdigest()


def cpu_ticks():
    values=list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
    return sum(values),values[3]+values[4]


def sample():
    memory=dict((p[0].rstrip(':'),int(p[1])) for line in Path('/proc/meminfo').read_text().splitlines()
                if len(p:=line.split())>=2 and p[1].isdigit())
    device=Path('/sys/class/drm/card0/device')
    gpu={}
    for name in ('gpu_busy_percent','mem_info_vram_total','mem_info_vram_used','mem_info_gtt_used'):
        try:gpu[name]=int((device/name).read_text())
        except (OSError,ValueError):gpu[name]=None
    pressure={kind:float(dict(v.split('=') for v in Path('/proc/pressure'/Path(kind)).read_text().splitlines()[0].split()[1:])['avg10'])
              for kind in ('cpu','memory','io')}
    return dict(time=time.time(),cpu_ticks=cpu_ticks(),memory_available_kib=memory['MemAvailable'],
                load1=os.getloadavg()[0],pressure=pressure,gpu=gpu)


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--workers',type=int,nargs='+',default=[1,2,4])
    parser.add_argument('--frame-repeats',type=int,default=4)
    args=parser.parse_args()
    if (not args.workers or len(set(args.workers))!=len(args.workers)
            or any(n<1 or n>8 for n in args.workers) or not 1<=args.frame_repeats<=40):
        parser.error('unique worker counts 1..8 and frame repeats 1..40 required')
    if args.output.exists():raise FileExistsError(args.output)
    os.nice(19)
    from language_nav.live_resources import coexistence_headroom
    coexistence_headroom()
    report=json.loads((ROOT/'reports/expansion_collection_development_20260912_v1/report.json').read_bytes())
    frames=[];skipped=[]
    for row in report['attempts']:
        run=ROOT/'reports/physical_live_episodes'/row['run_id']
        path=run/'perception_capture/frame-000.json'
        if row['status']=='emitted' and path.exists():
            try:
                req=json.loads((run/'request.json').read_bytes())
                meta=json.loads(path.read_bytes())
                if not (path.parent/meta['rgb']['file']).is_file():raise ValueError('missing RGB bytes')
            except (OSError,ValueError,KeyError) as exc:
                skipped.append(dict(run_id=row['run_id'],reason=str(exc)))
                continue
            if req['partition']!='development' or req['protected_test_routes_used'] is not False:raise ValueError('scope')
            frames.append(str(path))
        if len(frames)==24:break
    if len(frames)!=24:raise ValueError('24 retained development frames required')
    samples=[];stop=threading.Event();monitor_errors=[]
    def monitor():
        while not stop.is_set():
            try:samples.append(sample())
            except Exception as exc:monitor_errors.append(str(exc));break
            stop.wait(.5)
    thread=threading.Thread(target=monitor);thread.start()
    timings=[];expected=None
    try:
        time.sleep(5)
        baseline_end=time.time()
        # Warm files once, then rotate worker counts to reduce order/cache bias.
        for frame in frames:image_work(frame)
        order=[n for offset in range(3) for n in (args.workers[offset%len(args.workers):]+args.workers[:offset%len(args.workers)])]
        for workers in order:
            coexistence_headroom()
            start=time.perf_counter()
            with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
                outputs=list(pool.map(image_work,frames*args.frame_repeats,chunksize=1))
            elapsed=time.perf_counter()-start
            digest=hashlib.sha256(''.join(outputs).encode()).hexdigest()
            if expected is not None and digest!=expected:raise ValueError('parallel result mismatch')
            expected=digest
            timings.append(dict(workers=workers,seconds=elapsed,tasks=len(frames)*args.frame_repeats,result_sha256=digest))
            print(json.dumps(timings[-1]),flush=True)
        time.sleep(5)
    finally:
        stop.set();thread.join()
    durations=[];failed=[]
    ledger=ROOT/'reports/expansion_collection_development_20260912_v1/attempts.jsonl'
    for line in ledger.read_text().splitlines():
        row=json.loads(line)
        if row.get('partition')!='development':raise ValueError('development ledger only')
        seconds=(dt.datetime.fromisoformat(row['finished_at_utc'])-dt.datetime.fromisoformat(row['started_at_utc'])).total_seconds()
        (durations if row.get('status')=='emitted' else failed).append(seconds)
    median={str(n):statistics.median(r['seconds'] for r in timings if r['workers']==n) for n in args.workers}
    baseline=str(min(args.workers))
    result=dict(schema_version='research3-offline-concurrency-benchmark/v1',
        scope='warm-cache checksum/decode/std/four-colour-mask proxy including process-pool startup; not full QA or simulator throughput',
        simulator_launched=False,validation_labels_read=False,priority_nice=os.nice(0),
        timings=timings,skipped_input_candidates=skipped,median_seconds=median,
        baseline_workers=int(baseline),speedup={n:median[baseline]/v for n,v in median.items()},
        samples=samples,baseline_end=baseline_end,monitor_errors=monitor_errors,
        historical_capture_seconds=dict(success_count=len(durations),median=statistics.median(durations),
            p90=sorted(durations)[int(.9*(len(durations)-1))],mean=statistics.mean(durations),
            failed_count=len(failed),failed_total_seconds=sum(failed),
            successful_total_seconds=sum(durations)),
        input_frame_metadata_sha256={str(Path(p).relative_to(ROOT)):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in frames})
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,sort_keys=True)
    print(json.dumps({k:result[k] for k in ('median_seconds','speedup','historical_capture_seconds')}),flush=True)


if __name__=='__main__':main()
