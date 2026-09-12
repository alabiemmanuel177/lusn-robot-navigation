#!/usr/bin/env python3
"""Check a local staging directory's file inventory, not scientific completion."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def verify(root, manifest, manifest_path=None):
    root = Path(root).resolve(strict=True)
    if not root.is_dir() or manifest.get("schema_version") != "research3-local-file-manifest/v1":
        raise ValueError("directory and supported local-file manifest required")
    records = manifest.get("files")
    if not isinstance(records, list) or not records:
        raise ValueError("nonempty file records required")
    expected, errors = set(), []
    for record in records:
        name = record.get("path", "")
        if not isinstance(name, str) or not name or "\\" in name or name.startswith("/") or any(p in {"", ".", ".."} for p in name.split("/")):
            raise ValueError("unsafe/noncanonical member path")
        if name in expected:
            raise ValueError("duplicate member path")
        expected.add(name)
        if not isinstance(record.get("sha256"), str) or re.fullmatch(r"[0-9a-f]{64}", record["sha256"]) is None:
            raise ValueError("invalid SHA256")
        target = root.joinpath(*PurePosixPath(name).parts)
        chain = [target, *list(target.parents)[:len(PurePosixPath(name).parts)-1]]
        if any(p.is_symlink() for p in chain) or not target.resolve().is_relative_to(root):
            errors.append({"path": name, "error": "symlink_or_outside_root"})
            continue
        if not target.is_file():
            errors.append({"path": name, "error": "missing_or_not_regular_file"})
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != record["sha256"]:
            errors.append({"path": name, "error": "checksum_mismatch", "actual_sha256": actual})
    ignored = set()
    if manifest_path is not None:
        resolved = Path(manifest_path).resolve()
        if resolved.is_relative_to(root):
            ignored.add(str(resolved.relative_to(root)))
    actual = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() or p.is_symlink()}
    extras = sorted(actual - expected - ignored)
    return {"schema_version": "research3-local-file-verification/v1", "integrity_passed": not errors and not extras,
            "verified_manifest_members": len(expected), "errors": errors, "unexpected_files": extras,
            "scientific_release_complete": False,
            "scope": "local byte integrity and exact inventory only; no archive extraction or research gate certification"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.root, json.loads(args.manifest.read_text(), object_pairs_hook=unique_object), args.manifest)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["integrity_passed"] else 1)


if __name__ == "__main__":
    main()
