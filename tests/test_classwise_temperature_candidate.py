"""Synthetic fixtures only; never Research 3 human observation returns."""
import copy
import math
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import classwise_temperature_candidate as cal


def rows(partition='development', maps=('synthetic-a', 'synthetic-b')):
    return [dict(observation_id=f'{m}-{c}-{i}', map_id=m, view_group=f'{m}-view-{i % 3}',
                 category=c, partition=partition, panel='primary_expansion',
                 reviewer_type='human', reviewer_name='synthetic-test-fixture-not-a-review',
                 correct=i % 2 == 0, probability=(.2, .6, .9)[i % 3])
            for m in maps for c in cal.CLASSES for i in range(18)]


def test_exact_grid_and_numeric_extremes():
    assert 1.0 in cal.GRID and len(cal.GRID) == len(set(cal.GRID))
    assert cal.GRID[0] == pytest.approx(.2) and cal.GRID[-1] == pytest.approx(5)
    for p in (0., .1, .5, .9, 1.):
        assert math.isfinite(cal.probability(p, .2))
        assert cal.probability(p, 1) == pytest.approx(min(1-1e-9, max(1e-9, p)))
    for bad in (None, True, float('nan'), -.1, 1.1):
        with pytest.raises(ValueError): cal.probability(bad, 1)


def test_equal_map_view_emission_weights():
    selected = [{'map_id': 'a', 'view_group': 'x'}] * 3 + [
        {'map_id': 'a', 'view_group': 'y'}, {'map_id': 'b', 'view_group': 'z'}]
    assert cal.weights(selected) == pytest.approx([1/12, 1/12, 1/12, 1/4, 1/2])


@pytest.mark.parametrize('field,value', [('partition', 'validation'), ('panel', 'pilot'),
    ('panel', 'engineered_diagnostic'), ('correct', None), ('correct', 1),
    ('reviewer_type', 'agent'), ('map_id', 'protected'), ('view_group', '')])
def test_forbidden_rows_rejected(field, value):
    sample = rows(); sample[0][field] = value
    with pytest.raises(ValueError): cal.fit_development(sample, ['synthetic-a', 'synthetic-b'])


def test_duplicate_identity_rejected():
    sample = rows(); sample.append(sample[0])
    with pytest.raises(ValueError, match='duplicate'): cal.fit_development(sample, ['synthetic-a', 'synthetic-b'])


def test_coverage_boundaries_are_half_open():
    sample = rows()
    for r in sample:
        r['probability'] = .5
    audit = cal.coverage(sample, ['synthetic-a', 'synthetic-b'])
    assert not audit['passed']
    assert audit['counts']['chair']['bins'] == [0, 36, 0]
    assert cal.fit_development(sample, ['synthetic-a', 'synthetic-b'])['classes'] is None


def test_grid_fit_retains_objectives_and_does_not_modify_inputs():
    sample = rows(); original = copy.deepcopy(sample)
    result = cal.fit_development(sample, ['synthetic-a', 'synthetic-b'])
    assert result['status'] == 'numerical_candidate_not_frozen'
    assert result['actual_model_approved'] is False
    for c in cal.CLASSES:
        fit = result['classes'][c]
        assert len(fit['objectives']) == len(cal.GRID)
        assert fit['objective'] <= min(fit['objectives']) + cal.EPS
    assert sample == original


def test_constant_half_probability_tie_chooses_identity():
    sample = rows()[:18]
    for r in sample: r['probability'] = .5
    fit = cal.fit_class(sample)
    assert fit['temperature'] == 1.0
    assert fit['objective'] == pytest.approx(math.log(2))


def test_metrics_hand_calculation_and_empty_bins():
    report = cal.metrics([{'correct': False}, {'correct': True}], [.1, .9], [.5, .5])
    assert report['brier'] == pytest.approx(.01)
    assert report['ece'] == pytest.approx(.1)
    assert report['mce'] == pytest.approx(.1)
    assert report['bins'][0]['gap'] is None
    assert report['bins'][1]['count'] == report['bins'][9]['count'] == 1


def test_identity_does_not_pass_strict_improvement_screen():
    sample = rows('validation')
    report = cal.evaluate(sample, 'validation', ['synthetic-a', 'synthetic-b'], {c: 1 for c in cal.CLASSES})
    admission = cal.admission_screen({'passed': True}, report, full_attempt_accounting_verified=True)
    assert not admission['point_estimate_screen_passed']
    assert not admission['gates']['macro_brier_improved']
    assert not admission['human_model_approval']


def test_all_leave_map_out_folds_retained_including_unfit():
    sample = rows()
    for r in sample:
        if r['map_id'] == 'synthetic-a': r['correct'] = True
    folds = cal.leave_one_map_out(sample, ['synthetic-a', 'synthetic-b'])
    assert len(folds) == 2
    assert folds[0]['diagnostic'] is not None
    assert folds[1]['fit']['status'] == 'coverage_blocked'
    assert folds[1]['diagnostic'] is None
