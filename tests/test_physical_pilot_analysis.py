import hashlib
import json
from pathlib import Path
import runpy
import tarfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = runpy.run_path(str(ROOT / "scripts/analyze_physical_pilots.py"))
PACKAGE = runpy.run_path(str(ROOT / "scripts/package_physical_pilots.py"))


def test_retained_pilots_audit_separate_endpoints_and_preserve_failures():
    report = ANALYSIS["analyze"](ANALYSIS["DEFAULT_EPISODES"])
    assert len(report["episodes"]) == 3
    assert report["counts"]["navigation_success"] == {"true": 1, "false": 2, "unknown": 0}
    assert report["counts"]["instruction_completion"] == {"true": 2, "false": 1, "unknown": 0}
    assert report["counts"]["collision"]["false"] == 3
    assert report["comparative_effect_estimates"] is None
    assert not report["final_research_release"]
    with pytest.raises(ValueError, match="duplicate"):
        ANALYSIS["analyze"]([ANALYSIS["DEFAULT_EPISODES"][0]] * 2)
    with pytest.raises(ValueError, match="at least one"):
        ANALYSIS["analyze"]([])


def test_protected_request_rejected_before_summary_read(tmp_path):
    (tmp_path / "request.json").write_text(json.dumps({"partition": "test", "protected_test_routes_used": True}))
    with pytest.raises(ValueError, match="non-protected"):
        ANALYSIS["analyze"]([tmp_path])


def test_bundle_exclusive_creation_and_member_checksums(tmp_path):
    data = b"retained failure evidence"
    files = {"episode/measurements.json": data}
    manifest = {"files": {"episode/measurements.json": {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}}}
    target = tmp_path / "pilots.tar.gz"
    digest = PACKAGE["write_bundle"](target, files, manifest)
    assert digest == hashlib.sha256(target.read_bytes()).hexdigest()
    with tarfile.open(target) as archive:
        assert archive.extractfile("episode/measurements.json").read() == data
        assert json.load(archive.extractfile("MANIFEST.json")) == manifest
    with pytest.raises(FileExistsError):
        PACKAGE["write_bundle"](target, files, manifest)


def test_collect_rejects_external_episode_without_reading_provider(tmp_path):
    collect = PACKAGE["collect"]
    original = collect.__globals__["ANALYSIS"]["analyze"]
    collect.__globals__["ANALYSIS"]["analyze"] = lambda episodes: {}
    try:
        root = tmp_path / "workspace"
        root.mkdir()
        external = tmp_path / "outside"
        external.mkdir()
        with pytest.raises(ValueError, match="outside workspace"):
            collect([external], root=root)
    finally:
        collect.__globals__["ANALYSIS"]["analyze"] = original
