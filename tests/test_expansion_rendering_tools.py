"""Offline tests for the rendering camera model, rendered checks and diagnostic packet gates."""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import expansion_camera_model as cam  # noqa: E402
import expansion_rendered_checks as checks  # noqa: E402
import render_expansion_diagnostics as render  # noqa: E402
import prepare_expansion_diagnostics_v2 as v2  # noqa: E402


def test_rendering_camera_is_forward_right_and_above_base():
    centre, rotation = cam.rendering_camera(dict(x=0., y=0., yaw=0.))
    assert centre.tolist() == pytest.approx([0.133, -0.094, 0.224])
    # optical axes: right = -y, down = -z, forward = +x
    assert rotation[:, 0].tolist() == pytest.approx([0., -1., 0.])
    assert rotation[:, 1].tolist() == pytest.approx([0., 0., -1.])
    assert rotation[:, 2].tolist() == pytest.approx([1., 0., 0.])
    roll, pitch, yaw = cam.sdf_rpy(rotation)
    assert np.allclose(cam.rotation_from_rpy(roll, pitch, yaw), rotation, atol=1e-12)


def test_camera_model_recovers_height_and_offset_from_synthetic_depth():
    pose = dict(x=1., y=-.5, yaw=.3)
    centre, rotation = cam.rendering_camera(pose)
    info = v2.intrinsics()
    height, width = info['height'], info['width']
    v, u = np.mgrid[0:height, 0:width]
    k = info['k']
    rays = np.stack([(u - k[2]) / k[0], (v - k[5]) / k[4], np.ones_like(u, dtype=float)], -1) @ rotation.T
    depth = np.full((height, width), np.inf, dtype=np.float32)
    rgb = np.full((height, width, 3), 60, dtype=np.uint8)
    # floor plane z=0 and one wall face at y=1.125 (a box at y=1.2 with sy=.15)
    for plane_axis, value, colour in ((2, 0., (204, 204, 204)), (1, 1.125, (82, 84, 86))):
        direction = rays[..., plane_axis]
        t = (value - centre[plane_axis]) / np.where(np.abs(direction) < 1e-9, np.nan, direction)
        hit = np.isfinite(t) & (t > 0)
        forward = rays @ rotation[:, 2]
        z = t * forward
        better = hit & (z < depth)
        depth[better] = z[better].astype(np.float32)
        rgb[better] = colour
    walls = [dict(name='hall_1_1', x=5., y=1.2, sx=10., sy=.15)]
    result = cam.verify_against_depth(pose, depth, info, rgb, walls, floor_rgb=(204, 204, 204))
    assert result['verified'] is True
    assert abs(result['height_residual']) < 1e-3 and abs(result['y_residual']) < 1e-3


def test_occluder_and_sphere_checks_measure_coverage():
    control = np.full((48, 64, 3), 200, dtype=np.uint8)
    control[10:30, 10:40] = (107, 45, 45)          # target strip
    info = dict(k=[1., 0., 0., 0., 1., 0., 0., 0., 1.])
    polygon = [(10, 10), (40, 10), (40, 30), (10, 30)]
    candidate = control.copy()
    candidate[10:30, 10:16] = (115, 115, 115)      # grey screen over the left 20% of the box
    result, masks = checks.occluder_checks(control, candidate, polygon_normalized=polygon, camera_info=info,
                                           target_rgb=(107, 45, 45))
    assert result['screen_visible'] and result['box_coverage_within_tolerance'] and result['passed']
    assert result['rendered_box_coverage'] == pytest.approx(.2, abs=.02)
    sphere = control.copy()
    sphere[35:45, 45:60] = (107, 45, 45)           # disjoint same-colour blob
    result, _ = checks.sphere_checks(control, sphere, target_rgb=(107, 45, 45))
    assert result['sphere_visible'] and result['sphere_and_target_disjoint'] and result['passed']
    overlapping = control.copy()
    overlapping[20:40, 30:50] = (107, 45, 45)      # blob touching the target
    result, _ = checks.sphere_checks(control, overlapping, target_rgb=(107, 45, 45))
    assert result['passed'] is False and result['sphere_and_target_disjoint'] is False


def test_sphere_candidates_are_fixed_ordered_geometry():
    candidates = v2.sphere_candidates(dict(x=2., y=1.), dict(x=0., y=1., yaw=0.))
    assert candidates[0]['along'] == .45 and candidates[0]['across'] == 0.
    assert candidates[0]['x'] == pytest.approx(1.55) and candidates[0]['y'] == pytest.approx(1.)
    assert len(candidates) == 4 + 6 * 6 and len({(c['along'], c['across']) for c in candidates}) == len(candidates)


def test_asset_decision_gate_requires_packet_binding_and_acceptance(tmp_path, monkeypatch):
    packet = ROOT / 'reports' / 'test_packet_tmp'
    monkeypatch.setattr(render, 'ROOT', ROOT)
    packet_rel = 'reports/test_packet_tmp'
    packet.mkdir(exist_ok=False)
    try:
        audit = dict(rows=[dict(candidate_key='occluder/expansion-v1-r001-chair-s1-view0', candidate_id='expansion-v1-r001-chair-s1-view0',
                                treatment='occluder', rendered=True)])
        (packet / 'rendered_audit.json').write_text(json.dumps(audit))
        manifest = dict(files={'rendered_audit.json': render.sha_file(packet / 'rendered_audit.json')})
        (packet / 'manifest.json').write_text(json.dumps(manifest))
        decision = dict(schema_version=render.DECISION_SCHEMA, packet_directory=packet_rel,
                        packet_sha256=render.sha_file(packet / 'manifest.json'), reviewer_name='A Reviewer',
                        reviewer_role='Researcher', reviewed_at='2026-09-12T10:00:00+01:00',
                        occluder_definition_accepted=True, human_labels_generated=False,
                        decisions={'occluder/expansion-v1-r001-chair-s1-view0': dict(decision='accept', note='')})
        path = tmp_path / 'DECISIONS.json'
        path.write_text(json.dumps(decision))
        assert render.validate_asset_decision(path, candidate_id='expansion-v1-r001-chair-s1-view0', treatment='occluder')
        decision['decisions']['occluder/expansion-v1-r001-chair-s1-view0']['decision'] = 'revise'
        path.write_text(json.dumps(decision))
        with pytest.raises(PermissionError):
            render.validate_asset_decision(path, candidate_id='expansion-v1-r001-chair-s1-view0', treatment='occluder')
        decision['decisions']['occluder/expansion-v1-r001-chair-s1-view0']['decision'] = 'accept'
        decision['occluder_definition_accepted'] = False
        path.write_text(json.dumps(decision))
        with pytest.raises(PermissionError):
            render.validate_asset_decision(path, candidate_id='expansion-v1-r001-chair-s1-view0', treatment='occluder')
        decision['occluder_definition_accepted'] = True
        decision['packet_sha256'] = '0' * 64
        path.write_text(json.dumps(decision))
        with pytest.raises(ValueError):
            render.validate_asset_decision(path)
    finally:
        for child in packet.iterdir():
            child.unlink()
        packet.rmdir()


def test_render_jobs_share_one_control_per_view_and_use_diag_namespace():
    rows = render.candidates()
    jobs = render.render_jobs(rows)
    controls = [job for job in jobs if job['kind'] == 'control']
    assert len(rows) == 80 and len(controls) == 40 and len(jobs) == 120
    assert all(job['run_id'].startswith('expansion-diag-') for job in jobs)
    argv = render.command(jobs[-1], 89, 20)
    assert '--diagnostic-derivative' in argv and '--capture-only' in argv and '--expansion-instrumentation-snapshot' not in argv
