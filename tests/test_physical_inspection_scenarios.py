"""Non-protected inspection diagnostics; replay is not a new live experiment."""
from dataclasses import replace
import json
import math
from pathlib import Path

import pytest

from language_nav.live import inspection_waypoint
from language_nav.models import ActionKind
from language_nav.systems.variants import B6ContradictionAware, SemanticRouteCandidate, SystemInput

TEXT = "Go through the corridor, then continue past the green chair, then take the second doorway on the right, then stop near the office entrance."


def candidates(observed=True):
    return tuple(SemanticRouteCandidate(
        route_id=f"r3geo_base_r010_{side}_{ordinal}", region_id="r3geo_base_r010_chair_region",
        anchor_entity_id="live-chair" if observed else "unobserved:chair",
        anchor_category="chair" if observed else "unknown",
        anchor_attributes={"color": "blue"} if observed else {},
        terminal_category=None, semantic_confidence=.95 if observed else 0,
        observation_coverage=0, distance=5.0 + ordinal, risk=0,
        traversability_observed=True, nav2_eligible=True, branch_index=ordinal, side=side,
        anchor_observation_id="rgbd-frame-17-chair" if observed else "",
        anchor_observed_at_ns=17_000_000_000 if observed else 0,
        anchor_observation_source="rgbd" if observed else "",
        anchor_observation_sequence=17 if observed else -1,
    ) for side in ("left", "right") for ordinal in (1, 2))


def test_direct_observed_attribute_conflict_can_trigger_inspection_without_absence_coverage():
    decision = B6ContradictionAware().decide(SystemInput("attribute-conflict", TEXT, candidates()))
    assert decision.action is ActionKind.INSPECT
    assert decision.route_id == "r3geo_base_r010_right_2"
    assert decision.contradiction > .25


def test_unknown_anchor_does_not_manufacture_contradiction_or_inspection():
    decision = B6ContradictionAware().decide(SystemInput("not-observed", TEXT, candidates(False)))
    assert decision.action is not ActionKind.INSPECT
    assert decision.contradiction == 0


def test_observed_matching_anchor_does_not_trigger_inspection():
    decision = B6ContradictionAware().decide(SystemInput("matching", TEXT.replace("green", "blue"), candidates()))
    assert decision.action is ActionKind.COMMIT
    assert decision.contradiction == 0


def test_retained_dev10_observation_replay_supports_attribute_inspection_scenario():
    path = Path(__file__).resolve().parents[1] / "reports/physical_live_episodes/r3-stage1-physical-dev10-v3/capture.json"
    capture = json.loads(path.read_text())
    snapshots = [json.loads(d.get("candidates_json", "[]")) for d in capture["decisions"]]
    snapshot = next(rows for rows in snapshots if len(rows) == 4
                    and all(r.get("anchor_observation_id") and r.get("nav2_eligible") for r in rows))
    selected = tuple(SemanticRouteCandidate(**row) for row in snapshot)
    assert all(c.observation_coverage == 0 for c in selected)
    decision = B6ContradictionAware().decide(SystemInput("offline-dev10-attribute-replay", TEXT, selected))
    assert decision.action is ActionKind.INSPECT


def test_shared_anchor_conflict_is_not_counted_four_times():
    shared = candidates()
    decision = B6ContradictionAware().decide(SystemInput("shared", TEXT, shared))
    assert decision.contradiction == pytest.approx(.45)
    assert decision.clause_reliability > .35
    assert all(c.observation_coverage == 0 for c in shared)


def test_observed_matching_alternative_prevents_global_clause_contradiction():
    shared = list(candidates())
    shared[0] = replace(shared[0], anchor_entity_id="green-chair", anchor_attributes={"color": "green"},
                        anchor_observation_id="rgbd-green")
    decision = B6ContradictionAware().decide(SystemInput("alternate", TEXT, tuple(shared)))
    assert decision.contradiction == 0
    assert decision.action is not ActionKind.INSPECT


def test_terminal_observation_can_supply_direct_conflict_with_zero_regional_coverage():
    shared = tuple(replace(c, terminal_category="laboratory_entrance", terminal_observation_id="terminal-17-" + c.route_id,
                           terminal_observation_source="rgbd", terminal_observation_sequence=17,
                           terminal_observed_at_ns=17_000_000_000) for c in candidates())
    decision = B6ContradictionAware().decide(SystemInput("terminal", TEXT.replace("green", "blue"), shared))
    assert decision.contradiction > .25
    assert decision.action is ActionKind.INSPECT


def test_midpoint_waypoint_alone_does_not_guarantee_anchor_visibility():
    # A plausible approved corridor path puts the midpoint past the chair.
    # This fixture documents the limitation, not a measured Gazebo path.
    path = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0), (8, 0), (8, -1), (8, -2)]
    x, y, yaw = inspection_waypoint(path)
    observed_anchor = (2.2, .75)
    forward_dot = (observed_anchor[0] - x) * math.cos(yaw) + (observed_anchor[1] - y) * math.sin(yaw)
    assert forward_dot < 0  # facing away; fresh-anchor post-inspection gate may time out
