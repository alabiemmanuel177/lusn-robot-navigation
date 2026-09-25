import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import recompute_development_navigation as m
from run_feasibility_navigation import plan_rows


def request():
    row=plan_rows()[0]
    return row,dict(partition='development',protected_test_routes_used=False,
        map_id='r3geo_'+row['base'].replace('-','_'),run_id=row['run_id'],
        system_id=row['system_id'],variant_id=row['variant_id'],
        world_directory=str(m.ROOT/row['world_directory']),asset_sha256={'map.yaml':'a'*64},
        source_sha256={name:'b'*64 for name in m.EVALUATORS})


def test_only_exact_development_request_accepted(monkeypatch):
    row,value=request();monkeypatch.setattr(m,'sha',lambda p:'b'*64)
    m.require_development_request(value,row)


@pytest.mark.parametrize('field,value', [('partition','held_out'),('protected_test_routes_used',True),
    ('world_directory','/tmp/not-the-world'),('map_id','r3geo_base_r015'),
    ('asset_sha256',{'../outside':'a'*64})])
def test_invalid_scope_rejected_before_evaluator_source_reads(field,value,monkeypatch):
    row,data=request();data[field]=value
    monkeypatch.setattr(m,'sha',lambda p:pytest.fail('must reject scope before source reads'))
    with pytest.raises(ValueError):m.require_development_request(data,row)


def test_source_drift_rejected(monkeypatch):
    row,value=request();monkeypatch.setattr(m,'sha',lambda p:'c'*64)
    with pytest.raises(ValueError,match='source differs'):m.require_development_request(value,row)
