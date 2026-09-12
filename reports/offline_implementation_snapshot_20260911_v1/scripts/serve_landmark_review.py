#!/usr/bin/env python3
"""Local interactive UI for the Research 3 landmark human-review worksheet.

Serves a single-page review tool and records human verdicts directly into
data/landmark_bridge/human_review_queue_v1.reviewed.jsonl, touching only the
three fields the validator allows (review_status, reviewer_id, correct).

Usage:
    python3 scripts/serve_landmark_review.py [--port 8791]

Then open http://127.0.0.1:8791/ and review. Run
scripts/validate_landmark_human_review.py when done.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REVIEWED_PATH = ROOT / "data" / "landmark_bridge" / "human_review_queue_v1.reviewed.jsonl"
FRAME_ROOT = ROOT / "reports" / "landmark_capture"
SCENES_DIR = ROOT / "data" / "landmark_bridge" / "runtime_scenes"
EDITABLE = {"review_status", "reviewer_id", "correct"}


def load_entity_info() -> dict:
    """entity_id -> reference appearance (render color + declared attributes)."""
    info = {}
    for path in sorted(SCENES_DIR.glob("*.yaml")):
        scene = yaml.safe_load(path.read_text())
        for entity in scene.get("entities", []):
            info[entity["entity_id"]] = {
                "marker_rgb": entity.get("marker_rgb"),
                "attributes": entity.get("attributes") or {},
            }
    return info


ENTITY_INFO = load_entity_info()

_WRITE_LOCK = threading.Lock()


def load_rows() -> list[dict]:
    return [
        json.loads(line)
        for line in REVIEWED_PATH.read_text().splitlines()
        if line.strip()
    ]


def save_rows(rows: list[dict]) -> None:
    payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    fd, tmp = tempfile.mkstemp(dir=REVIEWED_PATH.parent, prefix=".review_tmp_")
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(payload)
        os.replace(tmp, REVIEWED_PATH)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # keep the terminal quiet
        pass

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, obj, status: int = 200) -> None:
        self._send(status, json.dumps(obj).encode(), "application/json")

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/":
            self._send(200, PAGE.encode(), "text/html; charset=utf-8")
        elif path == "/api/state":
            tasks = []
            for row in load_rows():
                ref = ENTITY_INFO.get(row["entity_id"], {})
                tasks.append({
                    **row,
                    "entity_marker_rgb": ref.get("marker_rgb"),
                    "entity_attributes": ref.get("attributes", {}),
                })
            self._send_json({"tasks": tasks, "path": str(REVIEWED_PATH.relative_to(ROOT))})
        elif path.startswith("/frames/"):
            relative = path[len("/frames/"):]
            target = (FRAME_ROOT / relative).resolve()
            if not target.is_relative_to(FRAME_ROOT.resolve()) or not target.is_file():
                self._send(404, b"not found", "text/plain")
                return
            self._send(200, target.read_bytes(), "image/png")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:
        if self.path.split("?", 1)[0] != "/api/review":
            self._send(404, b"not found", "text/plain")
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            body = json.loads(self.rfile.read(length))
            index = body["index"]
            observation_id = body["observation_id"]
            correct = body["correct"]  # 1, 0, or None to reset to pending
            reviewer_id = str(body.get("reviewer_id", "")).strip()
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            self._send_json({"error": f"bad request: {exc}"}, 400)
            return
        if correct not in (0, 1, None):
            self._send_json({"error": "correct must be 0, 1, or null"}, 400)
            return
        if correct is not None and not reviewer_id:
            self._send_json({"error": "reviewer_id is required"}, 400)
            return
        with _WRITE_LOCK:
            rows = load_rows()
            if not isinstance(index, int) or not 0 <= index < len(rows):
                self._send_json({"error": "index out of range"}, 400)
                return
            row = rows[index]
            if row.get("observation_id") != observation_id:
                self._send_json({"error": "observation_id mismatch; reload the page"}, 409)
                return
            if correct is None:
                row["review_status"] = "pending_human_review"
                row["reviewer_id"] = ""
                row["correct"] = None
            else:
                row["review_status"] = "human_verified"
                row["reviewer_id"] = reviewer_id
                row["correct"] = int(correct)
            save_rows(rows)
        ref = ENTITY_INFO.get(row["entity_id"], {})
        self._send_json({"ok": True, "task": {
            **row,
            "entity_marker_rgb": ref.get("marker_rgb"),
            "entity_attributes": ref.get("attributes", {}),
        }})


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Landmark Human Review</title>
<style>
  :root {
    --bg: #14171c; --panel: #1d2129; --panel2: #232834; --text: #e6e9ef;
    --muted: #8b93a3; --line: #2e3442; --green: #34c07c; --red: #e5605e;
    --amber: #d9a13c; --blue: #5b9dd9;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--text);
    font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif;
  }
  header {
    display: flex; align-items: center; gap: 16px; padding: 10px 18px;
    background: var(--panel); border-bottom: 1px solid var(--line);
    position: sticky; top: 0; z-index: 5;
  }
  header h1 { font-size: 15px; margin: 0; font-weight: 600; }
  .progress { flex: 1; display: flex; align-items: center; gap: 10px; }
  .bar { flex: 1; height: 8px; background: var(--panel2); border-radius: 4px; overflow: hidden; }
  .bar > div { height: 100%; background: var(--green); width: 0; transition: width .2s; }
  .count { color: var(--muted); white-space: nowrap; font-variant-numeric: tabular-nums; }
  header input {
    background: var(--panel2); border: 1px solid var(--line); color: var(--text);
    border-radius: 6px; padding: 5px 9px; width: 130px; font: inherit;
  }
  header input.missing { border-color: var(--amber); }
  main { display: flex; gap: 18px; padding: 18px; max-width: 1200px; margin: 0 auto; }
  .frame-col { flex: 0 0 auto; }
  .frame-wrap {
    position: relative; width: 640px; max-width: 100%;
    border: 1px solid var(--line); border-radius: 8px; overflow: hidden;
    background: #000;
  }
  .frame-wrap img { display: block; width: 100%; height: auto; }
  .marker {
    position: absolute; width: 34px; height: 34px; margin: -17px 0 0 -17px;
    border: 2px solid var(--amber); border-radius: 50%; pointer-events: none;
    box-shadow: 0 0 0 1px rgba(0,0,0,.6), inset 0 0 0 1px rgba(0,0,0,.6);
  }
  .marker::before, .marker::after {
    content: ""; position: absolute; background: var(--amber);
    box-shadow: 0 0 0 1px rgba(0,0,0,.5);
  }
  .marker::before { left: 50%; top: -10px; bottom: -10px; width: 2px; margin-left: -1px; }
  .marker::after { top: 50%; left: -10px; right: -10px; height: 2px; margin-top: -1px; }
  .hint { color: var(--muted); font-size: 12.5px; margin-top: 8px; }
  kbd {
    background: var(--panel2); border: 1px solid var(--line); border-bottom-width: 2px;
    border-radius: 4px; padding: 0 5px; font: 12px ui-monospace, monospace;
  }
  .side { flex: 1; min-width: 280px; display: flex; flex-direction: column; gap: 14px; }
  .card { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px 16px; }
  .question { font-size: 16px; font-weight: 600; }
  .question .cat { color: var(--blue); }
  dl { display: grid; grid-template-columns: auto 1fr; gap: 3px 14px; margin: 0; }
  dt { color: var(--muted); }
  dd { margin: 0; font-family: ui-monospace, monospace; font-size: 13px; overflow-wrap: anywhere; }
  .btns { display: flex; gap: 10px; }
  button {
    flex: 1; padding: 12px; border-radius: 8px; border: 1px solid var(--line);
    background: var(--panel2); color: var(--text); font: 600 14px/1 inherit; cursor: pointer;
  }
  button:hover { filter: brightness(1.15); }
  button.yes { background: #1d4634; border-color: #2c6a4e; }
  button.no { background: #4b2523; border-color: #7a3a37; }
  button.ghost { flex: 0 0 auto; font-weight: 400; color: var(--muted); }
  .lookfor {
    margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--line);
    display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  }
  .swatch {
    display: inline-block; width: 40px; height: 40px; border-radius: 6px;
    border: 1px solid rgba(255,255,255,.25); flex: 0 0 auto;
  }
  .lookfor code { font-size: 12px; color: var(--muted); }
  .zoomrow { display: flex; align-items: center; gap: 14px; }
  .zoom {
    width: 180px; height: 180px; border: 1px solid var(--line); border-radius: 8px;
    background-repeat: no-repeat; background-color: #000; position: relative;
    flex: 0 0 auto; image-rendering: pixelated;
  }
  .zoom::after {
    content: ""; position: absolute; left: 50%; top: 50%; width: 10px; height: 10px;
    margin: -5px 0 0 -5px; border: 2px solid var(--amber); border-radius: 50%;
    box-shadow: 0 0 0 1px rgba(0,0,0,.6);
  }
  .zoomlabel { color: var(--muted); font-size: 12.5px; }
  .verdict { font-weight: 600; }
  .verdict.v1 { color: var(--green); } .verdict.v0 { color: var(--red); }
  .verdict.pending { color: var(--amber); }
  .strip { display: flex; flex-wrap: wrap; gap: 5px; padding: 0 18px 24px; max-width: 1200px; margin: 0 auto; }
  .dot {
    width: 22px; height: 22px; border-radius: 5px; border: 1px solid var(--line);
    background: var(--panel2); cursor: pointer; font-size: 10px; color: var(--muted);
    display: flex; align-items: center; justify-content: center; padding: 0; flex: 0 0 auto;
  }
  .dot.v1 { background: #1d4634; border-color: #2c6a4e; color: #9fe0c0; }
  .dot.v0 { background: #4b2523; border-color: #7a3a37; color: #f0b3b1; }
  .dot.cur { outline: 2px solid var(--blue); outline-offset: 1px; }
  .toast {
    position: fixed; bottom: 18px; right: 18px; background: var(--panel);
    border: 1px solid var(--line); border-radius: 8px; padding: 10px 14px;
    opacity: 0; transition: opacity .2s; pointer-events: none;
  }
  .toast.show { opacity: 1; }
  .done-banner {
    margin: 0 18px 14px; max-width: 1164px; margin-inline: auto;
    background: #1d4634; border: 1px solid #2c6a4e; border-radius: 8px;
    padding: 12px 16px; display: none;
  }
</style>
</head>
<body>
<header>
  <h1>Landmark Review</h1>
  <div class="progress"><div class="bar"><div id="bar"></div></div>
    <span class="count" id="count">–</span></div>
  <label style="color:var(--muted)">reviewer_id
    <input id="reviewer" placeholder="e.g. eao" spellcheck="false"></label>
</header>
<div class="done-banner" id="doneBanner">
  All tasks reviewed. Run the validator for this worksheet version to confirm
  freeze-readiness.
</div>
<main>
  <div class="frame-col">
    <div class="frame-wrap">
      <img id="frame" alt="review frame">
      <div class="marker" id="marker"></div>
    </div>
    <div class="hint">
      <kbd>1</kbd>/<kbd>Y</kbd> correct &nbsp; <kbd>0</kbd>/<kbd>N</kbd> incorrect &nbsp;
      <kbd>U</kbd> clear &nbsp; <kbd>&larr;</kbd><kbd>&rarr;</kbd> navigate.
      The crosshair marks the detection under review.
    </div>
  </div>
  <div class="side">
    <div class="card">
      <div class="question">Is the marked detection really a
        <span class="cat" id="qCat"></span>?</div>
      <div style="margin-top:4px;color:var(--muted)">Status:
        <span class="verdict" id="verdict"></span></div>
      <div class="lookfor" id="lookfor"></div>
    </div>
    <div class="card zoomrow">
      <div class="zoom" id="zoom"></div>
      <div class="zoomlabel" id="zoomlabel">4&times; zoom under the crosshair.<br>
        Compare against the expected color above. Glass entities are translucent,
        so the hue may blend with whatever is behind them.</div>
    </div>
    <div class="btns">
      <button class="yes" id="btnYes">Correct (1)</button>
      <button class="no" id="btnNo">Incorrect (0)</button>
      <button class="ghost" id="btnClear" title="Reset to pending">Clear</button>
    </div>
    <div class="card"><dl id="meta"></dl></div>
  </div>
</main>
<div class="strip" id="strip"></div>
<div class="toast" id="toast"></div>
<script>
let tasks = [], cur = 0;
const $ = id => document.getElementById(id);
const reviewer = $("reviewer");
reviewer.value = localStorage.getItem("landmark_reviewer_id") || "";
reviewer.addEventListener("input", () => {
  localStorage.setItem("landmark_reviewer_id", reviewer.value);
  reviewer.classList.remove("missing");
});

function toast(msg) {
  const t = $("toast"); t.textContent = msg; t.classList.add("show");
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), 1800);
}

function statusOf(t) {
  return t.review_status === "human_verified" ? String(t.correct) : "pending";
}

function render() {
  const t = tasks[cur];
  const frameUrl = "/frames/" + t.review_frame.replace(/^reports\/landmark_capture\//, "");
  $("frame").src = frameUrl;
  $("marker").style.left = (t.pixel.u / 640 * 100) + "%";
  $("marker").style.top = (t.pixel.v / 480 * 100) + "%";
  $("qCat").textContent = t.category.replaceAll("_", " ") + " (" + t.entity_id + ")";
  const rgb = t.entity_marker_rgb;
  const sphereChallenge = (t.challenge_condition_kind || "").includes("sphere");
  const attrs = Object.entries(t.entity_attributes || {})
    .map(([k, v]) => k + ": " + v).join(", ");
  if (sphereChallenge) {
    $("lookfor").innerHTML =
      "<span><b>Judge object identity, not colour.</b><br>" +
      "A coloured sphere is not a chair, door, doorway, sign, or entrance. " +
      "Mark correct only if the crosshair is actually on an object of the claimed class.</span>";
    $("zoomlabel").innerHTML =
      "4&times; zoom under the crosshair.<br>Use the curved silhouette and wider scene " +
      "context. Matching colour alone is not semantic correctness.";
  } else {
    $("lookfor").innerHTML = rgb
      ? '<span class="swatch" style="background:rgb(' + rgb.join(",") + ')"></span>' +
        '<span>Expected appearance of this entity<br><code>rgb(' + rgb.join(", ") + ')' +
        (attrs ? " &middot; " + attrs : "") + "</code></span>"
      : "<span>No reference appearance found for this entity.</span>";
    $("zoomlabel").innerHTML =
      "4&times; zoom under the crosshair.<br>Compare against the expected colour above. " +
      "Glass entities are translucent, so the hue may blend with whatever is behind them.";
  }
  const Z = 4;
  const zoom = $("zoom");
  zoom.style.backgroundImage = "url('" + frameUrl + "')";
  zoom.style.backgroundSize = (640 * Z) + "px " + (480 * Z) + "px";
  zoom.style.backgroundPosition =
    (-(t.pixel.u * Z - 90)) + "px " + (-(t.pixel.v * Z - 90)) + "px";
  const s = statusOf(t), v = $("verdict");
  v.className = "verdict " + (s === "pending" ? "pending" : "v" + s);
  v.textContent = s === "pending" ? "pending review"
    : (s === "1" ? "verified correct" : "verified incorrect") + " by " + t.reviewer_id;
  const metadata = [
    ["task", (cur + 1) + " / " + tasks.length],
    ["partition", t.partition], ["map / route", t.map_id + " / " + t.route_id],
    ["capture", t.capture_id], ["probability", t.probability.toFixed(3)],
    ["depth", t.depth_m.toFixed(2) + " m"], ["pixels", t.pixels],
    ["pixel (u,v)", t.pixel.u + ", " + t.pixel.v],
  ];
  if (t.challenge_condition_id) {
    metadata.splice(4, 0, ["challenge condition", t.challenge_condition_id]);
  }
  $("meta").innerHTML = metadata
    .map(([k, val]) => "<dt>" + k + "</dt><dd>" + val + "</dd>").join("");
  document.querySelectorAll(".dot").forEach((d, i) => {
    d.className = "dot " + (statusOf(tasks[i]) === "pending" ? "" : "v" + statusOf(tasks[i]))
      + (i === cur ? " cur" : "");
  });
  const done = tasks.filter(t => t.review_status === "human_verified").length;
  $("count").textContent = done + " / " + tasks.length + " reviewed";
  $("bar").style.width = (done / tasks.length * 100) + "%";
  $("doneBanner").style.display = done === tasks.length ? "block" : "none";
}

function goto(i) { cur = (i + tasks.length) % tasks.length; render(); }

function nextPending() {
  for (let step = 1; step <= tasks.length; step++) {
    const i = (cur + step) % tasks.length;
    if (statusOf(tasks[i]) === "pending") return goto(i);
  }
  render(); // nothing pending left
}

async function submit(correct) {
  const t = tasks[cur];
  if (correct !== null && !reviewer.value.trim()) {
    reviewer.classList.add("missing"); reviewer.focus();
    toast("Set your reviewer_id first"); return;
  }
  const res = await fetch("/api/review", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      index: cur, observation_id: t.observation_id,
      correct: correct, reviewer_id: reviewer.value.trim(),
    }),
  });
  const out = await res.json();
  if (!res.ok) { toast(out.error || "save failed"); return; }
  tasks[cur] = out.task;
  if (correct === null) { render(); toast("cleared"); }
  else { toast("saved: " + (correct ? "correct" : "incorrect")); nextPending(); }
}

$("btnYes").onclick = () => submit(1);
$("btnNo").onclick = () => submit(0);
$("btnClear").onclick = () => submit(null);
document.addEventListener("keydown", e => {
  if (e.target === reviewer) return;
  if (e.key === "1" || e.key.toLowerCase() === "y") submit(1);
  else if (e.key === "0" || e.key.toLowerCase() === "n") submit(0);
  else if (e.key.toLowerCase() === "u") submit(null);
  else if (e.key === "ArrowRight") goto(cur + 1);
  else if (e.key === "ArrowLeft") goto(cur - 1);
});

fetch("/api/state").then(r => r.json()).then(state => {
  tasks = state.tasks;
  const strip = $("strip");
  tasks.forEach((t, i) => {
    const d = document.createElement("button");
    d.className = "dot"; d.textContent = i + 1; d.title = t.capture_id;
    d.onclick = () => goto(i);
    strip.appendChild(d);
  });
  const firstPending = tasks.findIndex(t => t.review_status !== "human_verified");
  cur = firstPending === -1 ? 0 : firstPending;
  render();
});
</script>
</body>
</html>
"""


def main() -> None:
    global REVIEWED_PATH
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8791)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument(
        "--worksheet", choices=("v1", "v2", "v3", "v4", "v5"), default="v1",
        help="which review worksheet to serve and edit",
    )
    args = parser.parse_args()
    REVIEWED_PATH = (
        ROOT / "data" / "landmark_bridge"
        / f"human_review_queue_{args.worksheet}.reviewed.jsonl"
    )
    load_rows()  # fail fast if the worksheet is missing or malformed
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Landmark review tool: http://{args.host}:{args.port}/")
    print(f"Writing verdicts to {REVIEWED_PATH}")
    server.serve_forever()


if __name__ == "__main__":
    main()
