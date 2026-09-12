#!/usr/bin/env python3
"""Validate explicit test extension without weakening the dev/validation schema."""
import argparse
import json
from pathlib import Path

import jsonschema
import yaml


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--catalogues', type=Path, required=True)
    args = parser.parse_args()
    schema = json.loads(Path('/home/eao/risk-calibrated-nav/configs/landmark_bridge/landmark_scene.schema.json').read_text())
    schema['properties']['partition']['enum'] = ['test']
    schema['properties']['map_id']['pattern'] = '^test_[0-9]{2}$'
    schema['title'] = 'Explicitly authorized held-out landmark scene extension'
    schema_path = args.catalogues / 'heldout_scene.schema.json'
    if schema_path.exists():
        if json.loads(schema_path.read_text()) != schema:
            raise ValueError('existing held-out schema differs')
    else:
        with schema_path.open('x') as stream:
            json.dump(schema, stream, indent=2, sort_keys=True)
            stream.write('\n')
    paths = sorted((args.catalogues / 'scenes').glob('test_*.yaml'))
    assert len(paths) == 3
    for path in paths:
        jsonschema.validate(yaml.safe_load(path.read_text()), schema)
    print('All three scenes pass the explicit test-partition JSON Schema extension')


if __name__ == '__main__':
    main()
