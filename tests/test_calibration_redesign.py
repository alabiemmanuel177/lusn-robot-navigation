import copy
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import pytest
import yaml
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_calibration_redesign import CONFIG,validate_config,lighting_variant,invariant_tree

RAW=b'''<sdf version="1.9"><world name="default"><light name="sun" type="directional"><diffuse>0.9 0.9 0.9 1</diffuse><direction>0 0 -1</direction></light><model name="chair"><pose>1 2 0 0 0 0</pose><link name="body"><collision name="c"><geometry><box><size>1 1 1</size></box></geometry></collision><visual name="v"><material><diffuse>1 0 0 1</diffuse></material></visual></link></model></world></sdf>'''


def test_candidate_config_is_non_executable_and_preserves_thresholds():
    validate_config(yaml.safe_load(CONFIG.read_bytes()))


@pytest.mark.parametrize('mutation',[
    lambda c:c.update(execution_authorized=True),
    lambda c:c['coverage'].update(minimum_per_class_outcome=1),
    lambda c:c['primary_candidate'].update(validation_maps=[15]),
    lambda c:c['conditions'].update(noise_added=True),
    lambda c:c['sampling'].update(nondetection_is_negative_label=True),
    lambda c:c['primary_candidate'].update(old_primary_pilot_diagnostic_and_feasibility_rows_pooled=True),
    lambda c:c['feasibility'].update(calibration_eligible=True),
    lambda c:c['primary_candidate'].update(total_attempts=20),
])
def test_scope_drift_rejected(mutation):
    value=yaml.safe_load(CONFIG.read_bytes());mutation(value)
    with pytest.raises(ValueError):validate_config(value)


def test_control_is_byte_identical():
    assert lighting_variant(RAW,1.)==RAW


@pytest.mark.parametrize('scale',[.9,.8])
def test_only_global_lighting_changes(scale):
    before=ET.fromstring(RAW);after=ET.fromstring(lighting_variant(RAW,scale))
    assert invariant_tree(before)==invariant_tree(after)
    assert [float(x) for x in after.findtext('world/scene/ambient').split()]==[.4*scale]*3+[1.]
    assert [float(x) for x in after.findtext('world/light/diffuse').split()]==[.9*scale]*3+[1.]
    assert after.findtext('world/model/link/visual/material/diffuse')=='1 0 0 1'


@pytest.mark.parametrize('path',['world/model/pose','world/model/link/collision/geometry/box/size',
    'world/model/link/visual/material/diffuse','world/light/direction'])
def test_invariant_comparison_detects_geometry_material_or_direction_drift(path):
    before=ET.fromstring(RAW);after=copy.deepcopy(before);after.find(path).text='9 9 9'
    assert invariant_tree(before)!=invariant_tree(after)


def test_unexpected_source_or_scale_rejected():
    with pytest.raises(ValueError):lighting_variant(RAW,.5)
    with pytest.raises(ValueError):lighting_variant(RAW.replace(b'0.9 0.9 0.9 1',b'1 1 1 1'),.9)


def test_panel_rejects_missing_schedule_before_any_evidence_read():
    from verify_calibration_redesign import check_panel
    with pytest.raises(ValueError,match='incomplete'):
        check_panel([],'design_feasibility',[1,6],[7],yaml.safe_load(CONFIG.read_bytes()))
