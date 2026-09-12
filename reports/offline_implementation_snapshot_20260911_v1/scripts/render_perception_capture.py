#!/usr/bin/env python3
"""Decode a retained RGB camera sample to a create-once PNG for inspection."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('frame', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    info = json.loads(args.frame.read_text())['rgb']
    raw = (args.frame.parent / info['file']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != info['sha256']:
        raise ValueError('camera sample checksum mismatch')
    mode = {'rgb8': 'RGB', 'bgr8': 'BGR'}.get(info['encoding'])
    if mode is None:
        raise ValueError('unsupported camera encoding')
    image = Image.frombytes('RGB', (info['width'], info['height']), raw,
                            'raw', mode, info['step'], 1)
    with args.output.open('xb') as stream:
        image.save(stream, format='PNG')


if __name__ == '__main__':
    main()
