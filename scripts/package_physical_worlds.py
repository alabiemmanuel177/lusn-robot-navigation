#!/usr/bin/env python3
"""Archive the exact new world assets and geometry evidence with member hashes."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--worlds',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    checksum=args.output.with_suffix(args.output.suffix+'.sha256')
    if args.output.exists() or checksum.exists():
        raise SystemExit('refusing to overwrite bundle')
    files={f'worlds/{f.relative_to(args.worlds)}':f for f in sorted(args.worlds.rglob('*')) if f.is_file()}
    root=Path(__file__).resolve().parents[1]
    for path in (root/'reports/physical_navigation').glob('*/report.json'):
        files[str(path.relative_to(root))]=path
    for path in (root/'reports/physical_navigation').glob('*/interruption.json'):
        files[str(path.relative_to(root))]=path
    for relative in ('src/language_nav/world/physical.py','src/language_nav/evaluation/ordered.py',
                     'scripts/build_physical_worlds.py','scripts/verify_physical_world.py',
                     'scripts/validate_physical_navigation.py','scripts/render_physical_world.py',
                     'scripts/package_physical_worlds.py','docs/PHYSICAL_WORLDS.md',
                     'reports/physical_world_pilot_v1.png'):
        files[relative]=root/relative
    manifest={'schema_version':'research3-physical-world-bundle/v1',
              'scope':'world assets and reference validation; not comparative policy results',
              'files':{}}
    with tarfile.open(args.output,'x:gz') as tar:
        for name,path in sorted(files.items()):
            data=path.read_bytes()
            manifest['files'][name]=hashlib.sha256(data).hexdigest()
            info=tarfile.TarInfo(name)
            info.size=len(data)
            tar.addfile(info,io.BytesIO(data))
        data=json.dumps(manifest,indent=2,sort_keys=True).encode()
        info=tarfile.TarInfo('MANIFEST.json')
        info.size=len(data)
        tar.addfile(info,io.BytesIO(data))
    with tarfile.open(args.output) as tar:
        for name,digest in manifest['files'].items():
            assert hashlib.sha256(tar.extractfile(name).read()).hexdigest()==digest
    digest=hashlib.sha256(args.output.read_bytes()).hexdigest()
    with checksum.open('x') as stream:
        stream.write(f'{digest}  {args.output.name}\n')
    print(f'Verified {len(files)} files; {args.output.stat().st_size} bytes; SHA256 {digest}')


if __name__=='__main__':
    main()
