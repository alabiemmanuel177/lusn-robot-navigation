import ast
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import pytest


def configure():
    tree=ast.parse((Path(__file__).parents[1]/'ros_ws/src/language_nav_bringup/launch/physical_sim.launch.py').read_text())
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='configure_camera_fov')
    ns={'math':math,'ET':ET}
    exec(compile(ast.Module(body=[node],type_ignores=[]),'<camera>','exec'),ns)
    return ns['configure_camera_fov']


def test_fov_changes_both_cameras_only():
    raw='<sdf><model><sensor><camera><horizontal_fov>1</horizontal_fov></camera></sensor><sensor><camera><horizontal_fov>1</horizontal_fov></camera></sensor><pose>0 0 0 0 0 0</pose></model></sdf>'
    fn=configure()
    assert fn(raw,'')==raw
    root=ET.fromstring(fn(raw,'1.57'))
    assert [n.text for n in root.findall('.//horizontal_fov')]==['1.57','1.57']
    assert root.findtext('.//pose')=='0 0 0 0 0 0'


@pytest.mark.parametrize('value',['nan','0','3'])
def test_bad_fov_rejected(value):
    with pytest.raises(ValueError):
        configure()('<sdf/>',value)
