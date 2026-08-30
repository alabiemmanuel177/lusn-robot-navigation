from pathlib import Path


def test_graph_campaign_protects_held_out_partition() -> None:
    source = Path("scripts/run_graph_campaign.py").read_text()
    assert 'args.partition == "held_out" and not args.allow_protected' in source
    assert "held_out is protected" in source
