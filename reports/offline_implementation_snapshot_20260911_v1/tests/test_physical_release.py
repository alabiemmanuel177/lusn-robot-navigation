import hashlib
import json
from pathlib import Path
import runpy

import pytest

MODULE = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/verify_physical_release.py"))


def fixture(tmp_path):
    (tmp_path / "evidence.json").write_bytes(b"retained evidence")
    return {"schema_version": "research3-local-file-manifest/v1", "files": [
        {"path": "evidence.json", "sha256": hashlib.sha256(b"retained evidence").hexdigest()}]}


def test_integrity_is_not_scientific_completion_and_manifest_can_be_inside(tmp_path):
    manifest = fixture(tmp_path)
    path = tmp_path / "MANIFEST.json"
    path.write_text(json.dumps(manifest))
    report = MODULE["verify"](tmp_path, manifest, path)
    assert report["integrity_passed"]
    assert not report["scientific_release_complete"]


def test_changed_missing_and_extra_files_reported(tmp_path):
    manifest = fixture(tmp_path)
    (tmp_path / "evidence.json").write_text("tampered")
    (tmp_path / "unexpected.txt").write_text("extra")
    report = MODULE["verify"](tmp_path, manifest)
    assert not report["integrity_passed"]
    assert report["errors"][0]["error"] == "checksum_mismatch"
    assert report["unexpected_files"] == ["unexpected.txt"]
    manifest["files"][0]["path"] = "missing.json"
    assert MODULE["verify"](tmp_path, manifest)["errors"][0]["error"] == "missing_or_not_regular_file"


@pytest.mark.parametrize("name", ["../outside", "/tmp/outside", "a/../b", "./evidence.json", "a//b", "a\\b", ""])
def test_unsafe_and_noncanonical_paths_rejected(tmp_path, name):
    manifest = fixture(tmp_path)
    manifest["files"][0]["path"] = name
    with pytest.raises(ValueError, match="path"):
        MODULE["verify"](tmp_path, manifest)


def test_duplicate_members_and_duplicate_json_keys_rejected(tmp_path):
    manifest = fixture(tmp_path)
    manifest["files"].append(dict(manifest["files"][0]))
    with pytest.raises(ValueError, match="duplicate"):
        MODULE["verify"](tmp_path, manifest)
    with pytest.raises(ValueError, match="duplicate"):
        json.loads('{"files": [], "files": []}', object_pairs_hook=MODULE["unique_object"])


def test_symlink_inside_or_outside_is_not_followed(tmp_path):
    manifest = fixture(tmp_path)
    (tmp_path / "alias").symlink_to(tmp_path / "evidence.json")
    manifest["files"][0]["path"] = "alias"
    report = MODULE["verify"](tmp_path, manifest)
    assert report["errors"][0]["error"] == "symlink_or_outside_root"
    (tmp_path / "linked_dir").symlink_to(tmp_path, target_is_directory=True)
    manifest["files"][0]["path"] = "linked_dir/evidence.json"
    assert MODULE["verify"](tmp_path, manifest)["errors"][0]["error"] == "symlink_or_outside_root"
