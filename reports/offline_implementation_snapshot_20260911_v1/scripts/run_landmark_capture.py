#!/usr/bin/env python3
"""Run one create-once, non-protected Research 3 landmark capture."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import time
from typing import IO

import yaml

from language_nav.adapters.landmark_challenge import load_challenge_condition


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESEARCH1 = Path("/home/eao/risk-calibrated-nav")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_hashes(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return {
        str(item.relative_to(path)): sha256(item)
        for item in sorted(path.rglob("*"))
        if item.is_file()
    }


def load_route(research1: Path, route_id: str) -> tuple[dict, dict]:
    map_id = route_id.rsplit("_r", 1)[0]
    route_file = research1 / "configs" / "routes" / f"{map_id}.yaml"
    route_doc = yaml.safe_load(route_file.read_text())
    route = next((item for item in route_doc["routes"] if item["route_id"] == route_id), None)
    if route is None:
        raise ValueError(f"unknown Research 1 route: {route_id}")
    return route_doc, route


def launch(command: list[str], log: IO[str]) -> subprocess.Popen:
    return subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=log,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )


def stop(process: subprocess.Popen | None, timeout: float = 20.0) -> None:
    if process is None or process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGINT)
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=10.0)


def wait_for_rows(path: Path, processes: list[subprocess.Popen], timeout: float) -> int:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        failed = [process.returncode for process in processes if process.poll() is not None]
        if failed:
            raise RuntimeError(f"capture process exited early: {failed}")
        if path.exists():
            rows = sum(1 for line in path.open() if line.strip())
            if rows:
                return rows
        time.sleep(0.25)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--route-id", required=True)
    parser.add_argument("--research1-root", type=Path, default=DEFAULT_RESEARCH1)
    parser.add_argument("--motion-seconds", type=float, default=8.0)
    parser.add_argument("--speed", type=float, default=0.10)
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--view-entity")
    parser.add_argument("--view-side", type=int, choices=(-1, 1), default=-1)
    parser.add_argument("--view-distance", type=float, default=1.0)
    parser.add_argument("--record-review-media", action="store_true")
    parser.add_argument("--challenge-spec", type=Path)
    parser.add_argument("--challenge-condition")
    args = parser.parse_args()
    if bool(args.challenge_spec) != bool(args.challenge_condition):
        raise SystemExit("--challenge-spec and --challenge-condition must be supplied together")
    if (
        args.attempt < 1 or args.motion_seconds < 0 or not 0 <= args.speed <= 0.20
        or not 0.4 <= args.view_distance <= 3.0
    ):
        raise SystemExit("motion duration and speed must be bounded and non-negative")

    profile_path = ROOT / "configs" / "landmark_capture_profile.yaml"
    profile = yaml.safe_load(profile_path.read_text())
    actual_revision = subprocess.run(
        ["git", "-C", str(args.research1_root), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if actual_revision != profile["provider_revision"]:
        raise SystemExit(
            f"Research 1 revision mismatch: {actual_revision} != {profile['provider_revision']}"
        )

    route_doc, route = load_route(args.research1_root, args.route_id)
    map_id = route_doc["map_id"]
    plan = yaml.safe_load(
        (args.research1_root / "configs" / "landmark_bridge" / "research3_route_plan.yaml").read_text()
    )
    allowed = {item["platform_route_id"]: item for item in plan["routes"]}
    selected = allowed.get(args.route_id)
    if selected is None or selected["partition"] not in {"development", "validation"}:
        raise SystemExit("refusing route outside the non-protected Research 3 route plan")
    if plan.get("protected_test_routes_used"):
        raise SystemExit("route plan declares protected test use")

    source_scene = (
        args.research1_root / "configs" / "landmark_bridge" / "scenes" / f"{map_id}.yaml"
    )
    challenge_spec = challenge_condition = None
    if args.challenge_spec:
        challenge_spec, _, challenge_condition = load_challenge_condition(
            args.challenge_spec,
            source_scene,
            route_id=args.route_id,
            condition_id=args.challenge_condition,
        )
        args.view_entity = challenge_condition["entity_id"]
        args.view_side = int(challenge_condition["view_side"])
        args.view_distance = float(challenge_condition["view_distance_m"])
    runtime_scene = ROOT / "data" / "landmark_bridge" / "runtime_scenes" / f"{map_id}.yaml"
    if not runtime_scene.is_file():
        raise SystemExit(f"missing runtime scene: {runtime_scene}")
    runtime_doc = yaml.safe_load(runtime_scene.read_text())
    view = None
    spawn = dict(route["start"])
    if args.view_entity:
        view = next(
            (item for item in runtime_doc["entities"] if item["entity_id"] == args.view_entity),
            None,
        )
        if view is None or args.route_id not in view.get("route_ids", []):
            raise SystemExit("view entity must belong to the selected non-protected route")
        entity_pose = view["pose"]
        normal_yaw = float(entity_pose["yaw"])
        spawn = {
            "x": float(entity_pose["x"]) + args.view_side * args.view_distance * math.cos(normal_yaw),
            "y": float(entity_pose["y"]) + args.view_side * args.view_distance * math.sin(normal_yaw),
            "yaw": normal_yaw + (math.pi if args.view_side == 1 else 0.0),
        }
    if challenge_condition:
        view_suffix = f"-challenge-{challenge_condition['condition_id']}"
    else:
        view_suffix = f"-{args.view_entity}" if args.view_entity else ""
    attempt_suffix = "" if args.attempt == 1 else f"-attempt{args.attempt}"
    capture_id = f"{args.route_id}{view_suffix}{attempt_suffix}"
    report_dir = ROOT / "reports" / "landmark_capture" / capture_id
    review_log = (
        ROOT / "data" / "landmark_bridge" / f"{capture_id}-review.jsonl"
    )
    summary_path = report_dir / "summary.json"
    bag_path = report_dir / "review_media"
    if report_dir.exists() or review_log.exists():
        raise SystemExit(f"capture is create-once and already exists for {args.route_id}")
    report_dir.mkdir(parents=True)

    world_path = Path("/tmp") / f"research3-{capture_id}-landmarks.sdf"
    if challenge_condition:
        subprocess.run([
            "python3", str(ROOT / "scripts" / "make_landmark_challenge_world.py"),
            "--research1-root", str(args.research1_root),
            "--scene", str(source_scene),
            "--runtime-scene", str(runtime_scene),
            "--spec", str(args.challenge_spec),
            "--route-id", args.route_id,
            "--condition-id", args.challenge_condition,
            "--output", str(world_path),
        ], check=True)
    else:
        subprocess.run([
            "python3", str(args.research1_root / "scripts" / "make_landmark_world.py"),
            "--scene", str(source_scene), "--output", str(world_path),
        ], check=True)

    start = spawn
    sim = static_tf = bridge = bag = None
    handles: list[IO[str]] = []
    status = "failed"
    failure = None
    try:
        sim_log = (report_dir / "sim.log").open("x")
        tf_log = (report_dir / "static_tf.log").open("x")
        bridge_log = (report_dir / "bridge.log").open("x")
        handles.extend([sim_log, tf_log, bridge_log])
        sim = launch([
            "ros2", "launch", "simulation_worlds", "sim.launch.py",
            f"world:={map_id}", f"world_path:={world_path}",
            f"x_pose:={start['x']}", f"y_pose:={start['y']}",
            f"yaw:={start.get('yaw', 0.0)}",
        ], sim_log)
        time.sleep(1.5)
        yaw = float(start.get("yaw", 0.0))
        static_tf = launch([
            "ros2", "run", "tf2_ros", "static_transform_publisher",
            "--x", str(start["x"]), "--y", str(start["y"]), "--z", "0.0",
            "--yaw", str(yaw), "--pitch", "0.0", "--roll", "0.0",
            "--frame-id", "map", "--child-frame-id", "odom",
        ], tf_log)
        if args.record_review_media:
            bag_log = (report_dir / "bag.log").open("x")
            handles.append(bag_log)
            bag = launch([
                "ros2", "bag", "record", "-s", "mcap", "-o", str(bag_path),
                "/camera/image", "/camera/depth_image", "/camera/camera_info",
                "/semantic_observations", "/tf", "/tf_static", "/clock",
            ], bag_log)
            time.sleep(1.0)
        bridge = launch([
            "ros2", "launch", "language_nav_bringup", "research1_landmarks.launch.py",
            f"scene:={runtime_scene}", f"review_log:={review_log}",
            f"color_tolerance:={profile['color_tolerance']}",
        ], bridge_log)
        active = [sim, static_tf, bridge] + ([bag] if bag is not None else [])
        initial_rows = wait_for_rows(review_log, active, 20.0)
        if args.motion_seconds:
            motion = subprocess.Popen([
                "ros2", "topic", "pub", "/cmd_vel", "geometry_msgs/msg/Twist",
                f"{{linear: {{x: {args.speed}}}, angular: {{z: 0.0}}}}",
                "--rate", "10",
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            try:
                motion.wait(timeout=args.motion_seconds)
            except subprocess.TimeoutExpired:
                stop(motion, timeout=5.0)
            subprocess.run([
                "ros2", "topic", "pub", "/cmd_vel", "geometry_msgs/msg/Twist",
                "{linear: {x: 0.0}, angular: {z: 0.0}}", "--once",
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8.0)
            time.sleep(2.0)
        else:
            time.sleep(1.0)
        rows = [json.loads(line) for line in review_log.open() if line.strip()]
        if not rows:
            raise RuntimeError("no landmark observations were captured")
        status = "pending_human_review"
    except Exception as exc:  # preserve diagnostic logs and a machine-readable failure
        failure = str(exc)
        raise
    finally:
        for process in (bridge, bag, static_tf, sim):
            stop(process)
        for handle in handles:
            handle.close()
        rows = []
        if review_log.exists():
            rows = [json.loads(line) for line in review_log.open() if line.strip()]
        summary = {
            "schema_version": "landmark-capture-summary/v1",
            "status": status,
            "failure": failure,
            "partition": selected["partition"],
            "protected_test_data": False,
            "route_id": args.route_id,
            "attempt": args.attempt,
            "view_entity_id": args.view_entity,
            "view_side": args.view_side if args.view_entity else None,
            "view_distance_m": args.view_distance if args.view_entity else None,
            "map_id": map_id,
            "provider_revision": actual_revision,
            "capture_profile": profile["profile_id"],
            "capture_profile_sha256": sha256(profile_path),
            "source_scene_sha256": sha256(source_scene),
            "runtime_scene_sha256": sha256(runtime_scene),
            "world_sha256": sha256(world_path),
            "challenge_capture": bool(challenge_condition),
            "challenge_id": challenge_spec.get("challenge_id") if challenge_spec else None,
            "challenge_condition_id": (
                challenge_condition.get("condition_id") if challenge_condition else None
            ),
            "challenge_condition_kind": (
                challenge_condition.get("kind") if challenge_condition else None
            ),
            "challenge_spec_sha256": (
                sha256(args.challenge_spec) if args.challenge_spec else None
            ),
            "detector_configuration_changed": False,
            "review_log_sha256": sha256(review_log) if review_log.exists() else None,
            "review_media_available": bool(tree_hashes(bag_path)),
            "review_media_files": tree_hashes(bag_path),
            "observation_rows": len(rows),
            "entities": dict(sorted(Counter(row["entity_id"] for row in rows).items())),
            "categories": dict(sorted(Counter(row["category"] for row in rows).items())),
            "review_statuses": dict(sorted(Counter(row["review_status"] for row in rows).items())),
            "motion": {"seconds": args.motion_seconds, "linear_speed_mps": args.speed},
            "online_ground_truth_used": False,
            "segmentation_labels_used": False,
        }
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
