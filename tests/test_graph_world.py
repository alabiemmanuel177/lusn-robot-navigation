from language_nav.contracts import RouteRequest, SemanticObservationSource
from language_nav.world import GraphWorldAdapter, make_fixture_world


def test_graph_world_emits_research1_contract_deterministically() -> None:
    world_a = make_fixture_world()
    world_b = make_fixture_world()
    world_a.execute_path(("start", "hall", "junction"))
    world_b.execute_path(("start", "hall", "junction"))
    observations_a = world_a.observe()
    observations_b = world_b.observe()
    assert observations_a == observations_b
    assert {item.entity_id for item in observations_a} == {"chair-red", "chair-blue"}
    assert all(item.schema_version == "semantic-observation/v1" for item in observations_a)


def test_graph_adapter_satisfies_contract_and_guards_unknown_target() -> None:
    adapter = GraphWorldAdapter(make_fixture_world())
    assert isinstance(adapter, SemanticObservationSource)
    unknown = adapter.check(RouteRequest("r-1", "missing", "test", 0.35))
    assert not unknown.eligible
    known = adapter.check(RouteRequest("r-2", "goal", "test", 0.35))
    assert known.eligible
    assert adapter.execute(RouteRequest("r-2", "goal", "test", 0.35)).succeeded
