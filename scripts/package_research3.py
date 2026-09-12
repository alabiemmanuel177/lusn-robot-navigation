#!/usr/bin/env python3
"""Create a verified local source/evidence snapshot without changing Git trees."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPOS = {"research3": ROOT, "research1": Path("/home/eao/risk-calibrated-nav"),
         "research2": Path("/home/eao/failure-prediction")}
SUFFIXES = {".py", ".yaml", ".yml", ".json", ".xml", ".msg", ".md", ".cfg", ".zsh", ".sh", ".txt"}


def collect():
    files = {}
    for label, root in REPOS.items():
        folders = ["src", "scripts", "configs", "ros_ws/src"]
        if label == "research1":
            folders += ["extensions/research3_landmark_bridge"]
        if label == "research3":
            folders += ["docs", "tests", "data/manifests"]
        for folder in folders:
            for path in sorted((root / folder).rglob("*")):
                if (path.is_file() and not path.is_symlink() and path.suffix in SUFFIXES
                        and not (label != "research3" and path.suffix != ".py"
                                 and any(p.startswith("test_") for p in path.parts))
                        and not any(p in {"__pycache__", ".venv", ".git"} for p in path.parts)):
                    files[f"{label}/{path.relative_to(root)}"] = path
        for name in ("README.md", "pyproject.toml", "requirements.txt", "package.xml", "setup.py", "setup.cfg"):
            if (root / name).is_file():
                files[f"{label}/{name}"] = root / name
    freeze = yaml.safe_load((REPOS["research2"] / "configs/model_freeze.yaml").read_text())
    for section, path_key, digest_key in (("predictor", "checkpoint", "checkpoint_sha256"),
                                        ("calibration", "artifact", "artifact_sha256")):
        item = freeze[section]
        path = REPOS["research2"] / item[path_key]
        if hashlib.sha256(path.read_bytes()).hexdigest() != item[digest_key]:
            raise ValueError(f"frozen model asset mismatch: {path}")
        files[f"research2/{item[path_key]}"] = path
    model_dir = REPOS["research2"] / Path(freeze["predictor"]["checkpoint"]).parent
    for path in model_dir.iterdir():
        if path.is_file() and path.suffix in {".yaml", ".json"}:
            files[f"research2/{path.relative_to(REPOS['research2'])}"] = path
    for name in ("graph_heldout_v1.0.jsonl", "graph_heldout_v1.0.jsonl.sha256",
                 "research3_graph_heldout_analysis_v1.0.json", "live_comparison_plan_v1.json",
                 "live_campaign_v2.analysis.json", "live_campaign_v2.provenance.json"):
        files[f"research3/reports/{name}"] = ROOT / "reports" / name
    # Small structured live evidence only; omit multi-gigabyte capture media.
    for path in sorted((ROOT / "reports/live_episodes").rglob("*.json")):
        files[f"research3/{path.relative_to(ROOT)}"] = path
    for path in sorted((ROOT / "reports").glob("measured_live_*.json")):
        files[f"research3/{path.relative_to(ROOT)}"] = path
    for path in sorted((ROOT / "reports/collision_validation").rglob("report.json")):
        files[f"research3/{path.relative_to(ROOT)}"] = path
    for path in sorted((ROOT / "reports").glob("doorway_geometry_audit_*.json")):
        files[f"research3/{path.relative_to(ROOT)}"] = path
    return files


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    digest_path = args.output.with_suffix(args.output.suffix + ".sha256")
    if args.output.exists() or digest_path.exists():
        raise SystemExit("refusing to overwrite snapshot or checksum")
    files = collect()
    repositories = {}
    for name, root in REPOS.items():
        def git(*args):
            return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()
        repositories[name] = {"revision": git("rev-parse", "HEAD"),
                              "dirty": bool(git("status", "--porcelain"))}
    manifest = {"schema_version": "research3-source-evidence-package/v1",
                "scope": "current engineering snapshot; not the historical graph execution source",
                "protected_graph_results_included": True,
                "repositories": repositories,
                "not_bundled": ["ROS/Gazebo installations", "full map assets", "capture media",
                                "complete Python environments", "complete Research 2 training data"],
                "files": {}}
    with tarfile.open(args.output, "x:gz") as archive:
        for name, path in sorted(files.items()):
            data = path.read_bytes()
            manifest["files"][name] = hashlib.sha256(data).hexdigest()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(data))
        data = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
        info = tarfile.TarInfo("MANIFEST.json")
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
    with tarfile.open(args.output, "r:gz") as archive:
        for name, expected in manifest["files"].items():
            if hashlib.sha256(archive.extractfile(name).read()).hexdigest() != expected:
                raise ValueError(f"archive verification failed: {name}")
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    with digest_path.open("x") as stream:
        stream.write(f"{digest}  {args.output.name}\n")
    print(f"Verified {len(files)} files; {args.output.stat().st_size} bytes; SHA256 {digest}")


if __name__ == "__main__":
    main()
