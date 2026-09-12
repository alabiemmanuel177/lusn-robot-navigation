import copy
from collections import Counter, defaultdict
import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "prepare_physical_comparison", ROOT / "scripts/prepare_physical_comparison.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def config():
    return yaml.safe_load((ROOT / "configs/physical_campaign_draft_v1.yaml").read_text())


def test_nonprotected_matrix_count_unique_pairs_and_missing_intervention():
    plan = MODULE.prepare_plan(config(), ROOT / "data/physical_worlds_v1")
    assert plan["episode_count"] == 560
    assert plan["paired_block_count"] == 112
    episodes = plan["episodes"]
    assert len({row["episode_id"] for row in episodes}) == 560
    assert Counter(row["partition"] for row in episodes) == {
        "development": 400, "validation": 160}
    blocks = defaultdict(set)
    for row in episodes:
        blocks[row["variant_id"]].add(row["system_id"])
        assert not row["execution_authorized"]
        assert (row["environment_intervention"] != "none") == (
            row["condition"] == "missing_landmark")
    assert all(systems == set(MODULE.SYSTEMS) for systems in blocks.values())
    assert not plan["execution_authorized"]
    assert plan["heldout_reservation"]["episode_count_if_frozen"] == 240


def test_order_reproducible_and_each_position_balanced_within_one():
    settings = config()
    first = MODULE.prepare_plan(settings, ROOT / "data/physical_worlds_v1")
    assert first == MODULE.prepare_plan(settings, ROOT / "data/physical_worlds_v1")
    positions = defaultdict(Counter)
    for row in first["episodes"]:
        positions[row["within_block_position"]][row["system_id"]] += 1
    assert all(max(counts.values()) - min(counts.values()) <= 1
               for counts in positions.values())
    settings["execution_order_seed"] = 19
    assert first["episodes"] != MODULE.prepare_plan(
        settings, ROOT / "data/physical_worlds_v1")["episodes"]


def test_no_heldout_files_opened(monkeypatch):
    original = Path.read_bytes
    opened = []

    def guarded_read(path):
        opened.append(path)
        assert not any(f"base-r{i:03}" in path.parts for i in range(15, 21))
        return original(path)

    settings = config()
    monkeypatch.setattr(Path, "read_bytes", guarded_read)
    plan = MODULE.prepare_plan(settings, ROOT / "data/physical_worlds_v1")
    assert len(opened) == 14
    assert not plan["protected_content_read"]


@pytest.mark.parametrize("change", [
    lambda c: c.update(status="frozen"),
    lambda c: c.update(instruction_seed=1),
    lambda c: c.update(execution_order_seed=True),
    lambda c: c["world_ids"]["development"].append("base-r015"),
    lambda c: c["execution_gates"].pop("resource_isolation_research2"),
])
def test_invalid_or_unsafe_config_rejected(change):
    settings = copy.deepcopy(config())
    change(settings)
    with pytest.raises(ValueError):
        MODULE.prepare_plan(settings, ROOT / "data/physical_worlds_v1")


def test_setting_gates_cannot_authorize_execution():
    settings = config()
    settings["execution_gates"] = {key: "passed" for key in MODULE.GATES}
    plan = MODULE.prepare_plan(settings, ROOT / "data/physical_worlds_v1")
    assert not plan["execution_authorized"]
