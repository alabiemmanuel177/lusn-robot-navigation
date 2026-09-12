from pathlib import Path
import runpy

import pytest

MODULE = runpy.run_path(str(Path(__file__).parents[1] / 'scripts/check_physical_design_readiness.py'))


def config():
    return {'schema_version': 'research3-physical-experiment-design-draft/v2',
            'analysis_proposals': {'candidate_contrasts': ['B6_minus_B1'], 'primary_contrast': 'B6_minus_B1',
                                  'multiplicity_policy': 'synthetic_choice', 'confirmatory_inference_method': 'synthetic_choice'},
            'simulator_seed': {'confirmatory_seed_list': [1, 2]},
            'replication': {'confirmatory_replications': 2},
            'power_inputs_requiring_freeze': {'repetitions_per_world': 2, 'target_effect': .1,
                'target_power': .8, 'alpha': .05, 'baseline_completion': .5,
                'paired_discordance': .3, 'world_intracluster_correlation': .2}}


def test_complete_fields_cannot_approve_scientific_design_or_execution():
    report = MODULE['check'](config())
    assert report['supplied_design_fields_valid_and_complete']
    assert not report['campaign_authorized'] and not report['scientific_design_approved']
    assert not report['human_review_is_only_remaining_gate']


def test_missing_choices_and_nuisance_estimates_are_distinct():
    settings = config()
    settings['analysis_proposals']['primary_contrast'] = None
    settings['power_inputs_requiring_freeze']['paired_discordance'] = None
    report = MODULE['check'](settings)
    assert report['missing_scientific_choices'] == ['analysis_proposals.primary_contrast']
    assert report['missing_nonprotected_nuisance_estimates'] == ['power_inputs_requiring_freeze.paired_discordance']


@pytest.mark.parametrize('seeds', [[0], [True], [1, 1], [2**32], [], ['1']])
def test_invalid_seed_specs_are_not_ready(seeds):
    settings = config()
    settings['simulator_seed']['confirmatory_seed_list'] = seeds
    assert 'simulator_seed.confirmatory_seed_list' in MODULE['check'](settings)['invalid_or_inconsistent_values']


def test_replication_count_must_match_seed_list():
    settings = config()
    settings['replication']['confirmatory_replications'] = 3
    assert 'replication.confirmatory_replications:seed_count_mismatch' in MODULE['check'](settings)['invalid_or_inconsistent_values']


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -1, 1, True])
def test_invalid_alpha_rejected(value):
    settings = config()
    settings['power_inputs_requiring_freeze']['alpha'] = value
    assert 'power_inputs_requiring_freeze.alpha' in MODULE['check'](settings)['invalid_or_inconsistent_values']
