#!/usr/bin/env python3
"""Reviewer-side authenticated encryption and gated release of validation returns.

Keep the generated key on the reviewer's device, outside the shared packet.
This is confidentiality plus byte binding, not an authenticated human identity,
trusted timestamp service or proof that a reviewer has not disclosed plaintext.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import zipfile

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

RETURN_NAMES={'approval.json','policy.json','requirements.json','progress.jsonl','return_manifest.json'}


def encoded(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def b64(raw):return base64.b64encode(raw).decode('ascii')
def unb64(value):return base64.b64decode(value,validate=True)


def check_binding(raw, kit_raw):
    kit=json.loads(kit_raw)
    if (kit.get('schema_version')!='research3-portable-review-kit/v1'
            or kit.get('expansion_partition')!='validation'
            or kit.get('diagnostic_or_pilot_included') is not False):
        raise ValueError('explicit validation-only primary expansion kit required')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if set(archive.namelist())!=RETURN_NAMES or len(archive.namelist())!=5:
            raise ValueError('unexpected or duplicate return members')
        if any(info.file_size>2_000_000 for info in archive.infolist()):raise ValueError('oversized return member')
        contents={name:archive.read(name) for name in RETURN_NAMES}
    manifest=json.loads(contents.pop('return_manifest.json'))
    if (manifest.get('schema_version')!='research3-portable-review-return/v1'
            or manifest.get('kit_sha256')!=sha(kit_raw)
            or manifest.get('files')!={name:sha(value) for name,value in contents.items()}):
        raise ValueError('return/kit byte binding mismatch')
    return sha(kit_raw)


def seal(raw, kit_raw):
    kit_hash=check_binding(raw,kit_raw)
    key=AESGCM.generate_key(bit_length=256)
    nonce=os.urandom(12)
    metadata={'schema_version':'research3-sealed-validation/v1','partition':'validation',
              'algorithm':'AES-256-GCM','kit_manifest_sha256':kit_hash,
              'plaintext_return_sha256':sha(raw),
              'sealed_at':datetime.now(timezone.utc).isoformat(),
              'reviewer_keeps_key':True,'scientific_review_validated':False}
    ciphertext=AESGCM(key).encrypt(nonce,raw,encoded(metadata))
    return encoded({'metadata':metadata,'nonce':b64(nonce),'ciphertext':b64(ciphertext)}),key


def open_sealed(envelope_raw,key,gate,model_raw,protocol_raw):
    # Validate scope and model binding BEFORE attempting decryption.
    if (gate.get('schema_version')!='research3-validation-release-gate/v1'
            or gate.get('status')!='approved_development_model_frozen'
            or gate.get('reviewer_type')!='human'
            or not isinstance(gate.get('approved_by'),str) or not gate['approved_by'].strip()
            or gate.get('validation_used_for_fitting_or_selection') is not False
            or gate.get('sealed_validation_sha256')!=sha(envelope_raw)
            or gate.get('development_model_sha256')!=sha(model_raw)
            or gate.get('calibration_protocol_sha256')!=sha(protocol_raw)):
        raise ValueError('human development freeze and exact release bindings required')
    date=datetime.fromisoformat(gate.get('approved_at','').replace('Z','+00:00'))
    if date.tzinfo is None:raise ValueError('timezone-aware release decision required')
    envelope=json.loads(envelope_raw);meta=envelope['metadata']
    if (meta.get('schema_version')!='research3-sealed-validation/v1'
            or meta.get('partition')!='validation' or meta.get('algorithm')!='AES-256-GCM'):
        raise ValueError('unsupported encrypted validation envelope')
    nonce=unb64(envelope['nonce'])
    if len(key)!=32 or len(nonce)!=12:raise ValueError('invalid key or nonce length')
    raw=AESGCM(key).decrypt(nonce,unb64(envelope['ciphertext']),encoded(meta))
    if sha(raw)!=meta['plaintext_return_sha256']:raise ValueError('decrypted return hash mismatch')
    return raw


def write_private_once(path,raw):
    descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(descriptor,'wb') as stream:stream.write(raw)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    seal_parser=sub.add_parser('seal')
    seal_parser.add_argument('--return-zip',type=Path,required=True)
    seal_parser.add_argument('--kit-manifest',type=Path,required=True)
    seal_parser.add_argument('--key-file',type=Path,required=True)
    seal_parser.add_argument('--output',type=Path,required=True)
    opening=sub.add_parser('open')
    for name in ('sealed','key-file','release-gate','development-model','calibration-protocol','output'):
        opening.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    if args.command=='seal':
        if args.key_file.exists():raise FileExistsError(args.key_file)
        if args.key_file.resolve().is_relative_to(args.kit_manifest.resolve().parent):
            raise ValueError('keep the key outside the shared review kit directory')
        if args.key_file.resolve()==args.output.resolve():raise ValueError('key and ciphertext paths must differ')
        envelope,key=seal(args.return_zip.read_bytes(),args.kit_manifest.read_bytes())
        # Key first: if writing ciphertext fails, retain it; never delete user keys.
        write_private_once(args.key_file,key)
        write_private_once(args.output,envelope)
        print('SEALED. Send only the encrypted output. Keep the key and plaintext private until approved release.')
    else:
        raw=open_sealed(args.sealed.read_bytes(),args.key_file.read_bytes(),
            json.loads(args.release_gate.read_bytes()),args.development_model.read_bytes(),args.calibration_protocol.read_bytes())
        write_private_once(args.output,raw)
        print('DECRYPTED after bound release gate. Run the original kit return validator before analysis.')


if __name__=='__main__':main()
