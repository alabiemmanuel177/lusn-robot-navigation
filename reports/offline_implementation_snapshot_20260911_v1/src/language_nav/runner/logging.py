from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any


def _json_default(value: object) -> object:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(f"cannot encode {type(value).__name__}")


def canonical_json(value: object) -> str:
    return json.dumps(value, default=_json_default, sort_keys=True, separators=(",", ":"), allow_nan=False)


def configuration_digest(configuration: object) -> str:
    return hashlib.sha256(canonical_json(configuration).encode()).hexdigest()


class ImmutableJsonlWriter:
    """Create-once JSONL writer with per-record and whole-file checksums."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.checksum_path = path.with_suffix(path.suffix + ".sha256")
        self._handle = None
        self._file_hasher = hashlib.sha256()

    def __enter__(self) -> ImmutableJsonlWriter:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("x", encoding="utf-8")
        return self

    def write(self, record: object) -> str:
        if self._handle is None:
            raise RuntimeError("writer is not open")
        payload = asdict(record) if is_dataclass(record) else record
        material = canonical_json(payload)
        record_checksum = hashlib.sha256(material.encode()).hexdigest()
        envelope = canonical_json({"record": payload, "record_checksum": record_checksum}) + "\n"
        self._handle.write(envelope)
        self._handle.flush()
        self._file_hasher.update(envelope.encode())
        return record_checksum

    def __exit__(self, exc_type, exc, traceback) -> None:
        assert self._handle is not None
        self._handle.close()
        if exc_type is None:
            with self.checksum_path.open("x", encoding="utf-8", errors="strict") as checksum_file:
                checksum_file.write(self._file_hasher.hexdigest() + "\n")


def verify_jsonl(path: Path) -> list[dict[str, Any]]:
    checksum_path = path.with_suffix(path.suffix + ".sha256")
    expected_file_checksum = checksum_path.read_text().strip()
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_file_checksum:
        raise ValueError("whole-file checksum mismatch")
    records = []
    for line_number, line in enumerate(raw.decode().splitlines(), start=1):
        envelope = json.loads(line)
        actual = hashlib.sha256(canonical_json(envelope["record"]).encode()).hexdigest()
        if actual != envelope["record_checksum"]:
            raise ValueError(f"record checksum mismatch on line {line_number}")
        records.append(envelope["record"])
    return records
