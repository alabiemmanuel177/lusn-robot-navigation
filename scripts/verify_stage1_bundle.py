"""Read-only verification of an engineering evidence ZIP, without extracting it."""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import stat
import zipfile
from verify_physical_release import unique_object


def safe_name(name):
    return (isinstance(name,str) and bool(name) and not name.startswith('/') and '\\' not in name
            and all(part not in ('','.','..') for part in name.split('/')))


def verify(path,expected_sha256=None):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    checksum=digest.hexdigest()
    if expected_sha256 is not None and checksum!=expected_sha256:raise ValueError('archive SHA-256 mismatch')
    with zipfile.ZipFile(path) as archive:
        infos=archive.infolist();names=[item.filename for item in infos]
        if len(names)!=len(set(names)) or not all(safe_name(name) for name in names):
            raise ValueError('duplicate or unsafe archive member')
        if any(stat.S_ISLNK(item.external_attr>>16) for item in infos):raise ValueError('symlink member')
        if sum(item.file_size for item in infos)>2*1024**3:raise ValueError('archive exceeds bounded engineering evidence size')
        info=archive.getinfo('bundle_manifest.json')
        if info.file_size>8*1024**2:raise ValueError('manifest too large')
        manifest=json.loads(archive.read(info),object_pairs_hook=unique_object)
        if (manifest.get('schema_version')!='research3-engineering-evidence-bundle/v1'
                or manifest.get('scientific_release_complete') is not False
                or manifest.get('calibration_eligible') is not False):
            raise ValueError('engineering-only manifest required')
        records=manifest['files']
        expected=[row['path'] for row in records]
        if len(expected)!=len(set(expected)) or set(names)!=set(expected)|{'bundle_manifest.json'}:
            raise ValueError('manifest inventory mismatch')
        for row in records:
            member=archive.getinfo(row['path'])
            if member.file_size!=row['bytes']:raise ValueError('member size mismatch')
            member_digest=hashlib.sha256()
            with archive.open(member) as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):member_digest.update(block)
            if member_digest.hexdigest()!=row['sha256']:raise ValueError('member checksum mismatch')
    return dict(integrity_passed=True,archive_sha256=checksum,verified_members=len(records),
        expected_archive_digest_checked=expected_sha256 is not None,scientific_release_complete=False,
        approvals_generated=False,files_extracted=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path);parser.add_argument('--expected-sha256')
    args=parser.parse_args()
    print(json.dumps(verify(args.archive,args.expected_sha256),indent=2))
