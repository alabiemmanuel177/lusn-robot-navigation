#!/usr/bin/env python3
"""Export exact RGB frames for the v2 validation-expansion review queue."""
from __future__ import annotations

from collections import defaultdict
from html import escape
import hashlib
import json
from pathlib import Path

from PIL import Image as PILImage
import rosbag2_py
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import Image


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_rgb(message: Image, destination: Path) -> None:
    decoders = {"rgb8": "RGB", "bgr8": "BGR"}
    if message.encoding not in decoders:
        raise ValueError(f"unsupported RGB encoding: {message.encoding}")
    image = PILImage.frombytes(
        "RGB", (message.width, message.height), bytes(message.data),
        "raw", decoders[message.encoding], message.step,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)


def export_version(tag: str = "v2") -> None:
    if tag not in {"v2", "v3", "v4", "v5"}:
        raise ValueError("review-frame export supports v2, v3, v4, or v5")
    queue_path = ROOT / "data" / "landmark_bridge" / f"human_review_queue_{tag}.jsonl"
    frame_root = ROOT / "reports" / "landmark_capture" / "review_frames"
    frame_manifest = ROOT / "reports" / "landmark_capture" / f"review_frame_manifest_{tag}.json"
    index_path = ROOT / "reports" / "landmark_capture" / f"review_index_{tag}.html"
    if index_path.exists():
        raise SystemExit(f"{tag} review frame index is create-once")
    rows = [json.loads(line) for line in queue_path.read_text().splitlines() if line.strip()]
    by_capture: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_capture[row["capture_id"]].append(row)

    files: dict[str, str] = {}
    for capture_id, capture_rows in sorted(by_capture.items()):
        wanted = {int(row["observed_at_ns"]) for row in capture_rows}
        found = set()
        bag_path = ROOT / capture_rows[0]["review_media"]
        reader = rosbag2_py.SequentialReader()
        reader.open(
            rosbag2_py.StorageOptions(uri=str(bag_path), storage_id="mcap"),
            rosbag2_py.ConverterOptions("", ""),
        )
        while reader.has_next() and found != wanted:
            topic, serialized, _ = reader.read_next()
            if topic != "/camera/image":
                continue
            message = deserialize_message(serialized, Image)
            stamp = int(message.header.stamp.sec) * 1_000_000_000 + int(
                message.header.stamp.nanosec
            )
            if stamp not in wanted or stamp in found:
                continue
            destination = frame_root / capture_id / f"{stamp}.png"
            if not destination.exists():
                save_rgb(message, destination)
            relative = str(destination.relative_to(ROOT))
            files[relative] = sha256(destination)
            found.add(stamp)
        missing = wanted - found
        if missing:
            raise ValueError(f"{capture_id}: missing exact RGB frames {sorted(missing)}")

    manifest = {
        "schema_version": f"landmark-review-frames/{tag}",
        "queue_sha256": sha256(queue_path),
        "frame_count": len(files),
        "files": dict(sorted(files.items())),
    }
    serialized_manifest = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if frame_manifest.exists():
        if frame_manifest.read_text() != serialized_manifest:
            raise ValueError(f"existing {tag} review frame manifest differs from verified frames")
    else:
        frame_manifest.write_text(serialized_manifest)

    cards = []
    for index, row in enumerate(rows, 1):
        frame = ROOT / row["review_frame"]
        relative_image = frame.relative_to(index_path.parent)
        cards.append(
            '<article class="card">'
            f'<img src="{escape(str(relative_image))}" alt="review frame">'
            f"<p><b>{index}. {escape(row['category'])}</b> — "
            f"p={float(row['probability']):.4f}</p>"
            f"<p>{escape(row['entity_id'])}<br>{escape(row['region_id'])}</p>"
            f"<p>{escape(row['partition'])} / {escape(row['route_id'])}<br>"
            f"pixel=({float(row['pixel']['u']):.1f}, {float(row['pixel']['v']):.1f}), "
            f"depth={float(row['depth_m']):.2f} m</p>"
            f"<code>{escape(row['observation_id'])}</code>"
            "</article>"
        )
    index_path.write_text(
        f"<!doctype html><meta charset='utf-8'><title>Research 3 landmark review {tag}</title>"
        "<style>body{font-family:system-ui;margin:24px;background:#eee}"
        ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px}"
        ".card{background:white;padding:12px;border-radius:8px}.card img{width:100%;height:auto}"
        "code{font-size:10px;word-break:break-all}</style>"
        f"<h1>Research 3 landmark human-review queue {tag}</h1>"
        "<p>Inspect the marked pixel coordinates and set only review_status, reviewer_id, "
        "and correct in the JSONL queue. No labels in this page were generated automatically.</p>"
        f"<div class='grid'>{''.join(cards)}</div>",
        encoding="utf-8",
    )
    print(json.dumps({k: manifest[k] for k in ("schema_version", "queue_sha256", "frame_count")},
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    export_version("v2")
