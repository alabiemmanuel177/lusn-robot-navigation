import json
import runpy
from pathlib import Path

from language_nav.world.physical import build_world


def test_real_doorway_routes_and_wrong_choices(tmp_path):
    root=Path(__file__).parents[1]
    rows=json.loads((root/'data/manifests/instruction_benchmark_v0.1.json').read_text())['instructions']
    verify=runpy.run_path(str(root/'scripts/verify_physical_world.py'))['verify']
    # Exercise both mirror directions against SDF collision geometry and grid routes.
    for row in rows[:2]:
        folder=tmp_path/row['base_instruction_id']
        build_world(folder,row)
        result=verify(folder)
        assert sum(p['ordered_score']['instruction_completion'] for p in result['paths'])==1
        assert result['candidate_count']==4
