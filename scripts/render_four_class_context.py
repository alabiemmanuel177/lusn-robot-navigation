"""Lossless full-scene RGB previews for engineering inspection, not human labels."""
import argparse
import json
from pathlib import Path
from PIL import Image
from integrate_object_depth_candidate import ROOT,sha,write
from run_entrance_context_candidate import decode_frame


def main(paths,output):
    output.mkdir(exist_ok=False);items=[]
    for i,path in enumerate(paths):
        path=path.resolve();request=path.parent.parent/'request.json';req=json.loads(request.read_bytes())
        if req['partition']!='development' or req['protected_test_routes_used']:raise ValueError('development only')
        rgb,meta=decode_frame(path);destination=output/f'context-{i:03}.png'
        Image.fromarray(rgb).save(destination)
        items.append(dict(frame=str(path),frame_sha256=sha(path),rgb_sha256=meta['rgb']['sha256'],
            image=destination.name,image_sha256=sha(destination),human_verdict=None))
    write(output/'manifest.json',dict(items=items,source_sha256=sha(__file__),calibration_eligible=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('frames',type=Path,nargs='+')
    a=p.parse_args();main(a.frames,a.output)
