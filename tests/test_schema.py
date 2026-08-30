import json
from pathlib import Path


def test_instruction_schema_is_valid_json_with_closed_objects() -> None:
    schema = json.loads(Path("configs/instruction_schema.json").read_text())
    assert schema["additionalProperties"] is False
    clause_schema = schema["properties"]["clauses"]["items"]
    assert clause_schema["additionalProperties"] is False
    assert set(clause_schema["properties"]["clause_type"]["enum"]) == {
        "motion", "landmark", "turn", "topology", "terminal"
    }
