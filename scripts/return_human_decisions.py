#!/usr/bin/env python3
"""Package a human-authored response; never approve its scientific content."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def package(root, output):
    root = Path(root).resolve()
    manifest_raw = (root/'manifest.json').read_bytes()
    manifest = json.loads(manifest_raw)
    if manifest.get('schema_version') != 'research3-human-action-packet/v1':
        raise ValueError('unsupported packet')
    for name, expected in manifest['files'].items():
        path = root/name
        if (Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink()
                or not path.resolve().is_relative_to(root)):
            raise ValueError('unsafe fixed file')
        if sha(path.read_bytes()) != expected:
            raise ValueError('fixed packet file changed: '+name)
    response = (root/'YOUR_RESPONSE.md').read_bytes()
    if not response.strip() or len(response) > 1_000_000:
        raise ValueError('response must be nonempty and at most 1 MB')
    original = (root/'response.template.md').read_bytes()
    if response == original:
        raise ValueError('response is unchanged; enter your decisions first')
    record = {
        'schema_version':'research3-human-action-return/v1',
        'packet_manifest_sha256':sha(manifest_raw), 'response_sha256':sha(response),
        'scientific_content_validated':False, 'identity_authenticated':False,
        'execution_authorized':False, 'calibration_approved':False,
        'partial_responses_allowed':True,
    }
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('YOUR_RESPONSE.md',response)
        archive.writestr('packet_manifest.json',manifest_raw)
        archive.writestr('return_record.json',json.dumps(record,sort_keys=True,indent=2)+'\n')
    return record


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('research3-human-decisions-return.zip'))
    args=parser.parse_args()
    package(Path(__file__).resolve().parent,args.output)
    print('RETURN PACKAGED; NOT AN EXECUTION OR CALIBRATION APPROVAL')


if __name__=='__main__': main()
