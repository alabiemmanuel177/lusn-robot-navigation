#!/usr/bin/env python3
"""Create an exclusive, checksummed engineering evidence archive, not a release."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import runpy
import tarfile

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = runpy.run_path(str(ROOT / "scripts/analyze_physical_pilots.py"))


def collect(episodes, root=ROOT):
    root = Path(root).resolve()
    episodes = [Path(p) for p in episodes]
    if any(not p.resolve(strict=True).is_relative_to(root) for p in episodes):
        raise ValueError("episode outside workspace")
    analysis = ANALYSIS["analyze"](episodes)
    files = {}
    comparisons = {}

    def add(path):
        path = Path(path)
        resolved = path.resolve(strict=True)
        if path.is_symlink() or not resolved.is_relative_to(root) or not resolved.is_file():
            raise ValueError(f"archive member must be a regular workspace file: {path}")
        name = str(resolved.relative_to(root))
        # Snapshot bytes once: hashes and archived payload refer to exactly the same bytes.
        if name not in files:
            files[name] = resolved.read_bytes()
        return name

    for directory in episodes:
        directory = directory.resolve(strict=True)
        if not directory.is_relative_to(root):
            raise ValueError("episode outside workspace")
        request = json.loads((directory / "request.json").read_text())
        for path in sorted(directory.rglob("*")):
            if path.is_file() or path.is_symlink():
                add(path)
        world = Path(request["world_directory"])
        world = world if world.is_absolute() else root / world
        # Only exact request-pinned assets are read; never enumerate held-out catalogues.
        for name, expected in request.get("asset_sha256", {}).items():
            path = world / name
            if Path(name).is_absolute() or ".." in Path(name).parts:
                raise ValueError("unsafe asset path")
            member = add(path)
            if hashlib.sha256(files[member]).hexdigest() != expected:
                raise ValueError(f"historical world asset changed: {path}")
        comparisons[request["run_id"]] = {}
        for name, expected in request.get("source_sha256", {}).items():
            if Path(name).is_absolute() or ".." in Path(name).parts:
                raise ValueError("unsafe source path")
            member = add(root / name)
            actual = hashlib.sha256(files[member]).hexdigest()
            comparisons[request["run_id"]][name] = {
                "request_sha256": expected, "snapshot_sha256": actual, "matches_request": actual == expected}
    for name in ("scripts/analyze_physical_pilots.py", "scripts/package_physical_pilots.py",
                 "scripts/analyze_measured_live.py", "scripts/physical_perception_capture.py",
                 "src/language_nav/planning/policy.py", "configs/research_dependencies.yaml"):
        add(root / name)
    for episode in analysis["episodes"]:
        for item in episode["inputs"].values():
            member = str(Path(item["path"]).resolve().relative_to(root))
            if hashlib.sha256(files[member]).hexdigest() != item["sha256"]:
                raise ValueError("pilot evidence changed during packaging")
    manifest = {"schema_version": "research3-physical-pilot-bundle/v1",
                "scope": "retained pilot evidence plus current selected source snapshot; not final research release",
                "historical_execution_reproducibility_complete": False,
                "external_provider_sources_included": False,
                "source_comparisons": comparisons, "analysis": analysis,
                "limitations": ["Current source snapshot is not the exact historical source tree, even when selected pins match.",
                                "ROS environment, external providers and frozen model binaries are not bundled.",
                                "Archive includes every file in supplied pilot directories, including failed runs and logs.",
                                "This bundle does not constitute detector validation or a comparative campaign."],
                "files": {name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                          for name, data in sorted(files.items())}}
    return files, manifest


def write_bundle(output, files, manifest):
    output = Path(output)
    checksum = Path(str(output) + ".sha256")
    if output.exists() or checksum.exists():
        raise FileExistsError("refusing to overwrite bundle or checksum")
    with tarfile.open(output, "x:gz") as archive:
        for name, data in sorted({**files, "MANIFEST.json": json.dumps(manifest, indent=2, sort_keys=True).encode()}.items()):
            member = tarfile.TarInfo(name)
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
    with tarfile.open(output) as archive:
        for name, metadata in manifest["files"].items():
            if hashlib.sha256(archive.extractfile(name).read()).hexdigest() != metadata["sha256"]:
                raise ValueError(f"archive verification failed: {name}")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    with checksum.open("x") as stream:
        stream.write(f"{digest}  {output.name}\n")
    return digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episode", type=Path, action="append")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.dry_run and args.output is None:
        parser.error("--output is required unless --dry-run")
    files, manifest = collect(args.episode or ANALYSIS["DEFAULT_EPISODES"])
    result = {"members": len(files), "uncompressed_bytes": sum(map(len, files.values())),
              "historical_execution_reproducibility_complete": False}
    if not args.dry_run:
        result["sha256"] = write_bundle(args.output, files, manifest)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
