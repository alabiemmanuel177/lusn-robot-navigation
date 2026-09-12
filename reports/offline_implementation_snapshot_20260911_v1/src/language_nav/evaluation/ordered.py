"""Evaluator-only ordered gate scoring against independently annotated geometry.

Gate endpoints describe real passage cross-sections, never detector landmarks.
Positive direction is the left-to-right signed crossing relative to the gate.
"""
from __future__ import annotations

import math


def crossing_events(positions, gates):
    events = []
    for gate in gates:
        a, b = gate["a"], gate["b"]
        gx, gy = b[0] - a[0], b[1] - a[1]
        if math.hypot(gx, gy) < 1e-9:
            raise ValueError("gate endpoints must differ")
        direction = gate["direction"]
        if direction not in (-1, 1):
            raise ValueError("gate direction must be -1 or 1")
        for i, (p, q) in enumerate(zip(positions, positions[1:])):
            before = gx * (p[1] - a[1]) - gy * (p[0] - a[0])
            after = gx * (q[1] - a[1]) - gy * (q[0] - a[0])
            if not (direction * before < 0 <= direction * after):
                continue
            t = -before / (after - before)
            x, y = p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])
            along = ((x - a[0]) * gx + (y - a[1]) * gy) / (gx * gx + gy * gy)
            if 0 <= along <= 1:
                events.append({"gate_id": gate["gate_id"], "trajectory_index": i + t})
    return sorted(events, key=lambda item: (item["trajectory_index"], item["gate_id"]))


def score_ordered_instruction(positions, annotation, *, terminal_identity_correct,
                              collision=False, timeout=False):
    """Require explicit complete geometry annotation; unknown is not success.

    This scorer is downstream of execution only. A verified annotation maps each
    required motion clause to a directed physical gate, plus a terminal clause.
    """
    if annotation.get("schema_version") != "ordered-instruction-geometry/v1":
        raise ValueError("unsupported ordered geometry annotation")
    if (annotation.get("geometry_verified") is not True
            or not annotation.get("geometry_evidence")
            or not annotation.get("map_sha256")):
        return {"instruction_completion": None, "reason": "independent geometry annotation missing"}
    required = annotation.get("required_gate_ids", [])
    gates = annotation.get("gates", [])
    ids = [g["gate_id"] for g in gates]
    if (not required or len(required) != len(set(required))
            or len(ids) != len(set(ids)) or not set(required) <= set(ids)):
        raise ValueError("required gates must resolve to unique annotated identities")
    if not all(math.isfinite(v) for p in positions for v in p):
        raise ValueError("trajectory must be finite")
    for gate in gates:
        if not all(math.isfinite(v) for p in (gate["a"], gate["b"]) for v in p):
            raise ValueError("gate coordinates must be finite")
    events = crossing_events(positions, gates)
    forbidden = set(annotation.get("forbidden_gate_ids", []))
    if not forbidden <= set(ids) or forbidden & set(required):
        raise ValueError("forbidden gates must be distinct annotated alternatives")
    violations = [event for event in events if event["gate_id"] in forbidden]
    matched = []
    last_index = -1.0
    for event in events:
        if (len(matched) < len(required) and event["gate_id"] == required[len(matched)]
                and event["trajectory_index"] > last_index):
            matched.append(event["gate_id"])
            last_index = event["trajectory_index"]
    complete = (len(matched) == len(required) and terminal_identity_correct is True
                and not collision and not timeout and not violations)
    known_failure = collision or timeout or violations or terminal_identity_correct is False
    if not known_failure and (not positions or (
            len(matched) == len(required) and terminal_identity_correct is None)):
        complete = None
    return {"instruction_completion": complete, "matched_gate_ids": matched,
            "required_gate_ids": required, "crossing_events": events,
            "forbidden_crossings": violations,
            "reason": "ordered physical gates and independent terminal identity"}
