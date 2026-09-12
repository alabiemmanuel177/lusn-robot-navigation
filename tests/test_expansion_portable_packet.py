import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import portable_physical_review as KIT


def test_explicit_partition_required_before_reads(tmp_path):
    with pytest.raises(ValueError,match='explicit nonprotected'):
        KIT.build_kit(tmp_path,tmp_path/'out.zip',packet_directory=tmp_path/'reports/absent')


def test_no_empty_evidence_kit(tmp_path):
    packet=tmp_path/'reports/packet';packet.mkdir(parents=True)
    (packet/'inventory.json').write_text(json.dumps({'runs':[]}))
    (packet/'combined_visual_qa.jsonl').write_text('')
    with pytest.raises(ValueError,match='no actual'):
        KIT.build_kit(tmp_path,tmp_path/'out.zip',packet_directory=packet,partition='development')


def test_protected_run_refused_before_request_read(tmp_path):
    packet=tmp_path/'reports/packet';packet.mkdir(parents=True)
    name='expansion-v1-r015-chair-s1-view0'
    (packet/'inventory.json').write_text(json.dumps({'runs':[{
        'run_id':name,'directory':str(tmp_path/'reports/physical_live_episodes'/name)}]}))
    (packet/'combined_visual_qa.jsonl').write_text('')
    with pytest.raises(ValueError,match='prespecified primary'):
        KIT.build_kit(tmp_path,tmp_path/'out.zip',packet_directory=packet,partition='development')


def test_mixed_partition_refused_before_consolidation(tmp_path):
    packet=tmp_path/'reports/packet';packet.mkdir(parents=True)
    name='expansion-v1-r011-chair-s1-view0'
    run=tmp_path/'reports/physical_live_episodes'/name;run.mkdir(parents=True)
    (run/'request.json').write_text(json.dumps({'run_id':name,'partition':'validation',
        'map_id':'r3geo_base_r011','protected_test_routes_used':False}))
    (packet/'inventory.json').write_text(json.dumps({'runs':[{'run_id':name,'directory':str(run)}]}))
    (packet/'combined_visual_qa.jsonl').write_text('')
    with pytest.raises(ValueError,match='mixed'):
        KIT.build_kit(tmp_path,tmp_path/'out.zip',packet_directory=packet,partition='development')
