"""Post-Wave-S raw-pass-through/doorway-logistic candidate, not runtime admission."""
import math
from joint_score_components import FEATURE_ORDER, predict

PASS_THROUGH = ('chair', 'laboratory_entrance', 'office_entrance')


def score(emission, doorway_model):
    category = emission['category']
    raw = emission['raw_score']
    if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not math.isfinite(raw) or not 0 <= raw <= 1:
        raise ValueError('finite original matching score in [0,1] required')
    if category in PASS_THROUGH:
        value, meaning = raw, 'uncalibrated_matching_score'
    elif category == 'doorway':
        if emission['feature_order'] != list(FEATURE_ORDER):
            raise ValueError('fixed doorway feature order required')
        x = emission['features']
        if len(x) != 5 or not all(math.isfinite(v) for v in x) or x[0] != 1 or not -1 <= x[1] <= 1 or any(not 0 <= v <= 1 for v in x[2:]):
            raise ValueError('fixed bounded doorway features required')
        value, meaning = float(predict(doorway_model, [x])[0]), 'unvalidated_joint_probability_estimate'
    else:
        raise ValueError('unknown class; no fallback')
    return dict(category=category, input_score=value, original_matching_score=raw,
                score_meaning=meaning, calibration_validated=False, runtime_admitted=False)
