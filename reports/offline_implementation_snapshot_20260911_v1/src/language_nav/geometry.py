from __future__ import annotations

import math

Point = tuple[float, float]


def relation_holds(
    relation: str,
    subject: Point,
    anchor: Point,
    *,
    reference_heading_rad: float = 0.0,
    near_tolerance: float = 1.0,
) -> bool:
    """Evaluate Protocol 1.0 relations in an explicit reference frame.

    ``before``/``after`` use projection along the reference heading; left/right
    use the signed lateral projection. This avoids map-axis-dependent labels.
    """
    dx, dy = subject[0] - anchor[0], subject[1] - anchor[1]
    forward = (math.cos(reference_heading_rad), math.sin(reference_heading_rad))
    left = (-forward[1], forward[0])
    longitudinal = dx * forward[0] + dy * forward[1]
    lateral = dx * left[0] + dy * left[1]

    if relation == "near":
        return math.hypot(dx, dy) <= near_tolerance
    if relation == "before":
        return longitudinal < 0
    if relation == "after":
        return longitudinal > 0
    if relation in {"left", "left_of"}:
        return lateral > 0
    if relation in {"right", "right_of"}:
        return lateral < 0
    raise ValueError(f"unsupported spatial relation: {relation}")

