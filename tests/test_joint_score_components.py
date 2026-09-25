from copy import deepcopy
import numpy as np
import pytest

from joint_score_components import (depth_features, vector, emissions, fingerprint,
                                    duplicate_accounting, weights, fit_numeric, predict,
                                    process_development_frame)
from chair_foreground_band_candidate import chair_surface_estimate


def test_chair_depth_matches_frozen_v3_and_ignores_background():
    d = np.full((100, 100), 6.)
    d[35:45, 35:65] = 2.
    stats = depth_features(d, 'chair', [0, 0, 100, 100])
    old = chair_surface_estimate(d, [0, 0, 100, 100], np.eye(3), np.eye(4))
    assert stats['median_depth_m'] == old['median_depth_m'] == 2.
    assert stats['depth_iqr_m'] == old['depth_iqr_m'] == 0.
    assert stats['valid_depth_fraction'] == old['valid_fraction'] == 1.


def test_portal_uses_both_jambs_not_empty_centre():
    d = np.full((100, 100), np.nan)
    d[15:85, :15] = 2.
    d[15:85, 85:] = 2.2
    s = depth_features(d, 'doorway', [0, 0, 100, 100])
    assert s['median_depth_m'] == pytest.approx(2.1)
    assert s['depth_iqr_m'] == pytest.approx(.2)
    assert s['valid_depth_fraction'] == 1.
    d[15:85, 85:] = 5.
    with pytest.raises(ValueError, match='disagree'):
        depth_features(d, 'doorway', [0, 0, 100, 100])


@pytest.mark.parametrize('c', ['laboratory_entrance', 'office_entrance'])
def test_text_central_roi(c):
    d = np.full((100, 100), 8.)
    d[30:70, 30:70] = 2.
    assert depth_features(d, c, [0, 0, 100, 100])['median_depth_m'] == 2.


@pytest.mark.parametrize('z', [.05, 12., np.inf, np.nan])
def test_depth_bounds_no_imputation(z):
    with pytest.raises(ValueError):
        depth_features(np.full((100, 100), z), 'chair', [0, 0, 100, 100])


def test_endpoint_score_clipping_does_not_change_raw():
    stats = {'valid_depth_fraction': 1., 'relative_depth_iqr': 0.}
    assert vector(0., stats, .9) == [1., -1., 1., 0., 1.]
    assert vector(1., stats, 0.) == [1., 1., 1., 0., 0.]
    with pytest.raises(ValueError):
        vector(float('nan'), stats, 0.)


def row(i=0, entity='chair1', category='chair', score=.8):
    return dict(source='test', source_index=i, visual_category=category,
                raw_score=score, box=[0, 0, 100, 100], map_pose=[0., 0.],
                association=dict(status='unique_geometric_candidate', entity_id=entity,
                                 candidates=[dict(entity_id=entity, reference_distance_m=.1)]))


def test_whole_duplicate_group_abstains_not_best_score():
    frame = dict(frame_id='test', observed_at_ns=1,
                 hypotheses=[row(), row(1, score=.99), row(2, entity='chair2')])
    out = emissions(frame, depth=np.full((100, 100), 2.), acquisition_class='chair')
    assert [e['entity_id'] for e in out['emissions']] == ['chair2']
    assert [r['primary_status'] for r in out['hypotheses']][:2] == ['duplicate_instance_abstention']*2
    assert 'primary_status' not in frame['hypotheses'][0]


def test_other_class_is_diagnostic_and_empty_is_nondetection():
    f = dict(frame_id='test', observed_at_ns=1, hypotheses=[row(category='office_entrance')])
    out = emissions(f, depth=np.full((100, 100), 2.), acquisition_class='chair')
    assert out['status'] == 'nondetection' and not out['emissions']
    assert out['hypotheses'][0]['primary_status'] == 'other_class_diagnostic'


def calibration():
    return dict(k=np.eye(3).ravel().tolist(), d=[], r=np.eye(3).ravel().tolist(),
                p=np.zeros(12).tolist(), distortion_model='plumb_bob')


def test_fingerprint_normalizes_nan_endian_and_refuses_headers():
    rgb = np.zeros((3, 4, 3), np.uint8)
    a = np.ones((3, 4), dtype='<f8'); a[0, 0] = np.nan
    b = a.astype('>f8')
    assert fingerprint(rgb, a, calibration()) == fingerprint(rgb, b, calibration())
    b[1, 1] = 2.
    assert fingerprint(rgb, a, calibration()) != fingerprint(rgb, b, calibration())
    with pytest.raises(ValueError):
        fingerprint(rgb, a, dict(calibration(), stamp=123))


def test_duplicates_within_and_across_wave_and_capture_reuse():
    rows = [dict(attempt_id=str(i), wave=w, status='completed', capture_uuid=str(i), content_sha256='same')
            for i, w in enumerate(['S', 'S', 'C'])]
    out = duplicate_accounting(rows)
    assert [r['fitting_eligible'] for r in out] == [True, False, False]
    assert out[1]['duplicate_scope'] == 'within_wave'
    assert out[2]['duplicate_scope'] == 'cross_wave'
    rows[2]['capture_uuid'] = rows[0]['capture_uuid']
    with pytest.raises(ValueError, match='reused'):
        duplicate_accounting(rows)


def test_balanced_weights_and_fixed_solver():
    rows = [dict(map_id='a', view_group='one')]*3 + [dict(map_id='a', view_group='two'), dict(map_id='b', view_group='one')]
    assert weights(rows) == pytest.approx([1/12]*3+[.25, .5])
    x = [[1., -.5, 1., 0., .7], [1., .5, 1., 0., .1]]
    m = fit_numeric(x, [0, 1], [.5, .5])
    assert m == fit_numeric(x, [0, 1], [.5, .5])
    assert m['gradient_infinity_norm'] <= 1e-8
    assert predict(m, x)[0] < predict(m, x)[1]
    with pytest.raises(ValueError):
        fit_numeric(x, [1, 1], [.5, .5])


def test_full_candidate_boundary_to_features_synthetic():
    d = np.full((100, 100), 2.)
    result = process_development_frame(acquisition_class='chair', frame_id='invented',
        rgb_stamp_ns=1, depth_stamp_ns=1, depth=d,
        k=np.array([[100., 0., 50.], [0., 100., 50.], [0., 0., 1.]]), optical_to_map=np.eye(4),
        detector_boxes=[dict(visual_category='chair', raw_score=.8, xyxy=[0, 0, 100, 100])],
        ocr_texts=[], catalogue=[dict(entity_id='invented', category='chair', x=0., y=0.)],
        camera_xy=[0., 0.], template='research3-readable-corridor-sign-v1', partition='development')
    assert len(result['emissions']) == 1
    assert result['emissions'][0]['features'][0] == 1.
    assert result['human_labels_generated'] is False
