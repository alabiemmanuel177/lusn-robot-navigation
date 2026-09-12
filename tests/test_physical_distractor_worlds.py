import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from language_nav.benchmark.physical_catalog import validate_physical_launch_inputs

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('shape_stress',
    ROOT/'scripts/build_physical_distractor_worlds.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize('base', ['base-r010', 'base-r011'])
@pytest.mark.parametrize('category', MODULE.CATEGORIES)
def test_single_shape_preserves_readable_geometry_and_scene(tmp_path, base, category):
    source = ROOT/'data/physical_worlds_readable_v1'/base
    output = tmp_path/category/base
    before = {name: (source/name).read_bytes() for name in MODULE.READABLE.FILES}
    audit = MODULE.build(source, output, category)
    assert before == {name: (source/name).read_bytes() for name in before}
    original = ET.fromstring(before['world.sdf'])
    derivative = ET.parse(output/'world.sdf').getroot()
    world = derivative.find('world')
    added = world.find(f"model[@name='{audit['shape_model']}']")
    assert added is not None
    assert not added.findall('.//collision') and not added.findall('.//plugin')
    assert added.find('.//geometry/'+audit['shape']) is not None
    material = original.find(f"world/model[@name='{audit['source_marker_model']}']/.//visual/material")
    assert MODULE.READABLE.canonical(material) == MODULE.READABLE.canonical(added.find('.//material'))
    world.remove(added)
    assert MODULE.READABLE.canonical(original) == MODULE.READABLE.canonical(derivative)
    assert audit['center_association_distance_m'] < .9
    for filename in before:
        if filename not in ('world.sdf', 'manifest.json', 'execution_catalog.json'):
            assert (output/filename).read_bytes() == before[filename]
    for filename in ('manifest.json', 'execution_catalog.json'):
        old, new = json.loads(before[filename]), json.loads((output/filename).read_text())
        assert old.pop('world_sha256') != new.pop('world_sha256')
        assert old == new
    assert len(validate_physical_launch_inputs(output/'execution_catalog.json',
               output/'landmark_scene.yaml', output/'map.yaml').execution) == 4
    assert audit['false_positive_observed'] is False
    assert audit['labels_generated'] is False


def test_create_once_and_reject_scope_before_source_access(tmp_path, monkeypatch):
    source = ROOT/'data/physical_worlds_readable_v1/base-r010'
    destination = tmp_path/'base-r010'
    MODULE.build(source, destination, 'chair')
    with pytest.raises(FileExistsError):
        MODULE.build(source, destination, 'chair')
    def forbidden(_):
        pytest.fail('protected/out-of-scope source opened')
    monkeypatch.setattr(Path, 'read_bytes', forbidden)
    for base in ('base-r015', 'base-r001', 'unknown'):
        with pytest.raises(PermissionError):
            MODULE.build(tmp_path/base, tmp_path/'never', 'chair')


def test_controlled_chair_occlusion_changes_only_added_shape(tmp_path):
    source = ROOT/'data/physical_worlds_readable_v1/base-r010'
    v1, v2 = tmp_path/'v1'/'base-r010', tmp_path/'v2'/'base-r010'
    first = MODULE.build(source, v1, 'chair')
    before = {name: (v1/name).read_bytes() for name in MODULE.READABLE.FILES}
    second = MODULE.build(source, v2, 'chair', controlled_occlusion=True)
    assert before == {name: (v1/name).read_bytes() for name in before}
    assert second['shape_pose'] == [2.0, .6, .45]
    assert second['radius_m'] == .30
    assert second['center_association_distance_m'] < .9
    assert not second['false_positive_observed']
    one = ET.parse(v1/'world.sdf').getroot()
    two = ET.parse(v2/'world.sdf').getroot()
    model1 = one.find(f"world/model[@name='{first['shape_model']}']")
    model2 = two.find(f"world/model[@name='{second['shape_model']}']")
    model2.find('pose').text = model1.find('pose').text
    model2.find('.//sphere/radius').text = model1.find('.//sphere/radius').text
    assert MODULE.READABLE.canonical(one) == MODULE.READABLE.canonical(two)
    for name in MODULE.READABLE.FILES:
        if name not in ('world.sdf', 'manifest.json', 'execution_catalog.json'):
            assert (v2/name).read_bytes() == before[name]


@pytest.mark.parametrize('base,category', [('base-r011', 'chair'), ('base-r010', 'doorway')])
def test_controlled_occlusion_rejects_other_splits_or_categories(tmp_path, base, category):
    with pytest.raises(ValueError, match='restricted'):
        MODULE.build(ROOT/'data/physical_worlds_readable_v1'/base,
                     tmp_path/'never', category, controlled_occlusion=True)


@pytest.mark.parametrize('category', MODULE.CATEGORIES[1:])
def test_material_occlusion_adds_shell_without_changing_original_subtree(tmp_path, category):
    source = ROOT/'data/physical_worlds_readable_v1/base-r010'
    before = {name: (source/name).read_bytes() for name in MODULE.READABLE.FILES}
    output = tmp_path/category/'base-r010'
    audit = MODULE.build(source, output, category, controlled_material_occlusion=True)
    original = ET.fromstring(before['world.sdf'])
    derivative = ET.parse(output/'world.sdf').getroot()
    world = derivative.find('world')
    shell = world.find(f"model[@name='{audit['neutral_shell']['model_name']}']")
    sphere_or_cylinder = world.find(f"model[@name='{audit['shape_model']}']")
    for model in (shell, sphere_or_cylinder):
        assert model is not None
        assert not model.findall('.//collision')
        assert not model.findall('.//plugin')
        world.remove(model)
    assert MODULE.READABLE.canonical(original) == MODULE.READABLE.canonical(derivative)
    assert before == {name: (source/name).read_bytes() for name in before}
    assert all(b-a == pytest.approx(.01) for a, b in zip(
        audit['neutral_shell']['source_box_size'], audit['neutral_shell']['shell_box_size']))
    assert audit['shape_footprint_wall_clearance_m'] >= audit['radius_m']
    if category.endswith('entrance'):
        assert abs(audit['shape_pose'][1]) == 1.0
    else:
        assert abs(audit['shape_pose'][1]) == pytest.approx(.62)
    assert audit['center_association_distance_m'] < .9
    assert audit['false_positive_observed'] is False
    assert audit['neutral_shell']['readable_lettering_models_modified'] is False
    for filename in ('map.pgm', 'map.yaml', 'landmark_scene.yaml', 'verified_ordered_geometry.json'):
        assert (output/filename).read_bytes() == before[filename]


@pytest.mark.parametrize('base,category', [('base-r011', 'doorway'), ('base-r010', 'chair')])
def test_material_occlusion_restricted_to_declared_development_categories(tmp_path, base, category):
    with pytest.raises(ValueError, match='restricted'):
        MODULE.build(ROOT/'data/physical_worlds_readable_v1'/base,
                     tmp_path/'never', category, controlled_material_occlusion=True)


def test_chair_v3_masks_both_coloured_boxes_without_altering_originals(tmp_path):
    source = ROOT/'data/physical_worlds_readable_v1/base-r010'
    output = tmp_path/'chair'/'base-r010'
    original = ET.parse(source/'world.sdf').getroot()
    audit = MODULE.build(source, output, 'chair', controlled_chair_material_occlusion=True)
    result = ET.parse(output/'world.sdf').getroot()
    world = result.find('world')
    assert audit['shape_pose'] == [2.0, .6, .45]
    assert audit['radius_m'] == .30
    assert {row['source_marker_model'] for row in audit['chair_neutral_shells']} == {'chair_seat', 'chair_back'}
    world.remove(world.find(f"model[@name='{audit['shape_model']}']"))
    for record in audit['chair_neutral_shells']:
        shell = world.find(f"model[@name='{record['model_name']}']")
        assert not shell.findall('.//collision') and not shell.findall('.//plugin')
        source_model = original.find(f"world/model[@name='{record['source_marker_model']}']")
        assert record['source_material']['diffuse'] == source_model.findtext('.//material/diffuse')
        assert shell.findtext('.//material/diffuse') == '.45 .45 .45 1'
        assert shell.findtext('pose') == source_model.findtext('pose')
        assert all(b-a == pytest.approx(.01) for a,b in zip(record['source_box_size'], record['shell_box_size']))
        world.remove(shell)
    assert MODULE.READABLE.canonical(result) == MODULE.READABLE.canonical(original)
    assert MODULE.READABLE.canonical(ET.parse(source/'world.sdf').getroot()) == MODULE.READABLE.canonical(original)
    for filename in MODULE.READABLE.FILES:
        if filename not in ('world.sdf', 'manifest.json', 'execution_catalog.json'):
            assert (output/filename).read_bytes() == (source/filename).read_bytes()
    assert audit['false_positive_observed'] is False


@pytest.mark.parametrize('base,category', [('base-r011','chair'), ('base-r010','doorway')])
def test_chair_v3_cannot_change_validation_or_other_categories(tmp_path, base, category):
    with pytest.raises(ValueError, match='restricted'):
        MODULE.build(ROOT/'data/physical_worlds_readable_v1'/base, tmp_path/'never', category,
                     controlled_chair_material_occlusion=True)
