"""R3-JSC-20260924-01 features, emission selection and deterministic numerics.

No launch, label generation, catalogue-selected depth, or runtime admission.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json

import numpy as np

from four_class_candidate_runtime_v3 import process_frame
from joint_score_method_candidate import objective_gradient, sigmoid

CLASSES = ('chair', 'doorway', 'laboratory_entrance', 'office_entrance')
FEATURE_ORDER = ('intercept', 'raw_logit_scaled', 'valid_depth_fraction',
                 'relative_depth_iqr', 'reference_distance_scaled')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def support(depth, bounds):
    low = np.maximum(np.ceil(bounds[:2]).astype(int), [0, 0])
    high = np.minimum(np.ceil(bounds[2:]).astype(int), [depth.shape[1], depth.shape[0]])
    if np.any(high <= low):
        raise ValueError('no in-frame support')
    z = depth[low[1]:high[1], low[0]:high[0]]
    valid = np.isfinite(z) & (z > .05) & (z < 12.)
    if valid.sum() < 16 or valid.mean() < .5:
        raise ValueError('insufficient support; no imputation')
    return z[valid], z.size


def depth_features(depth, category, box):
    """Recompute exact approved supports from raw metric depth, not summaries."""
    d = np.asarray(depth, dtype=float)
    b = np.asarray(box, dtype=float)
    if category not in CLASSES or d.ndim != 2 or min(d.shape) < 1:
        raise ValueError('class and depth dimensions')
    if b.shape != (4,) or not np.isfinite(b).all() or np.any(b[2:] <= b[:2]):
        raise ValueError('positive finite box')
    if category == 'doorway':
        x0, y0, x1, y1 = b
        w, h = x1-x0, y1-y0
        left, nl = support(d, [x0, y0+.15*h, x0+.15*w, y1-.15*h])
        right, nr = support(d, [x1-.15*w, y0+.15*h, x1, y1-.15*h])
        medians = [np.median(left), np.median(right)]
        if abs(medians[0]-medians[1])/np.median(medians) > .15:
            raise ValueError('portal sides disagree')
        selected = np.concatenate([left, right])
        fraction = len(selected)/(nl+nr)
    else:
        centre = (b[:2]+b[2:])/2
        half = (b[2:]-b[:2])*.2
        z, n = support(d, np.concatenate([centre-half, centre+half]))
        fraction = len(z)/n
        selected = z
        if category == 'chair':
            ordered = np.sort(z, kind='stable')
            ends = np.searchsorted(ordered, ordered+.10, side='right')
            starts = np.flatnonzero(ends-np.arange(len(z)) >= max(16, int(np.ceil(.1*len(z)))))
            if not len(starts):
                raise ValueError('no supported chair band')
            start = int(starts[0])
            selected = ordered[start:ends[start]]
    q25, q75 = np.quantile(selected, [.25, .75], method='linear')
    median = float(np.median(selected))
    iqr = float(q75-q25)
    if category != 'doorway' and iqr > .1*median:
        raise ValueError('mixed surface')
    return dict(valid_depth_fraction=float(fraction), median_depth_m=median,
                depth_iqr_m=iqr, relative_depth_iqr=min(iqr/median, 1.),
                selected_pixels=len(selected))


def vector(raw_score, stats, distance):
    values = [raw_score, stats['valid_depth_fraction'], stats['relative_depth_iqr'], distance]
    if not np.isfinite(values).all() or not 0 <= raw_score <= 1 or not 0 <= distance <= .9:
        raise ValueError('finite score and association residual required')
    if not 0 <= values[1] <= 1 or not 0 <= values[2] <= 1:
        raise ValueError('depth feature bounds')
    p = np.clip(raw_score, 1e-9, 1-1e-9)
    return [1., float(np.clip(np.log(p/(1-p))/12., -1., 1.)),
            float(values[1]), float(values[2]), float(distance/.9)]


def emissions(frame, *, depth, acquisition_class):
    """Keep all hypotheses; whole duplicate-ID groups abstain before features."""
    if acquisition_class not in CLASSES:
        raise ValueError('acquisition class required, not a target identity')
    rows = deepcopy(frame['hypotheses'])
    groups = Counter()
    for row in rows:
        a = row.get('association')
        if a and a['status'] == 'unique_geometric_candidate':
            if len(a['candidates']) != 1 or a['entity_id'] != a['candidates'][0]['entity_id']:
                raise ValueError('inconsistent unique association')
            groups[(row['visual_category'], a['entity_id'])] += 1
    selected = []
    seen = set()
    for row in rows:
        key = (row['source'], row['source_index'])
        if key in seen:
            raise ValueError('duplicate proposal provenance')
        seen.add(key)
        row['primary_status'] = 'other_class_diagnostic'
        if row['visual_category'] != acquisition_class:
            continue
        a = row.get('association')
        if row['map_pose'] is None:
            row['primary_status'] = 'depth_template_abstention'
        elif not a:
            raise ValueError('localized hypothesis missing association accounting')
        elif a['status'] in ('unassociated', 'ambiguous'):
            row['primary_status'] = a['status']
        elif groups[(row['visual_category'], a['entity_id'])] > 1:
            row['primary_status'] = 'duplicate_instance_abstention'
        else:
            try:
                stats = depth_features(depth, row['visual_category'], row['box'])
                x = vector(row['raw_score'], stats, a['candidates'][0]['reference_distance_m'])
            except ValueError as exc:
                row.update(primary_status='feature_abstention', feature_error=str(exc))
                continue
            row['primary_status'] = 'scoreable_emission'
            item = dict(frame_id=frame['frame_id'], observed_at_ns=frame['observed_at_ns'],
                        category=row['visual_category'], entity_id=a['entity_id'],
                        source=row['source'], source_index=row['source_index'], box=row['box'],
                        map_pose=row['map_pose'], raw_score=row['raw_score'],
                        feature_order=list(FEATURE_ORDER), features=x, support=stats,
                        reference_distance_m=a['candidates'][0]['reference_distance_m'])
            item['emission_id'] = digest(item)
            selected.append(item)
    relevant = [r for r in rows if r['visual_category'] == acquisition_class]
    return dict(status='scoreable_emissions' if selected else 'nondetection' if not relevant else 'abstentions',
                emissions=selected, hypotheses=rows, human_labels_generated=False,
                runtime_admitted=False)


def process_development_frame(*, acquisition_class, **sensor_inputs):
    """Calls the pinned no-target inference/localization boundary before selection."""
    frame = process_frame(**sensor_inputs)
    return emissions(frame, depth=sensor_inputs['depth'], acquisition_class=acquisition_class)


def fingerprint(rgb, depth, calibration):
    """Canonical decoded content, not ROS headers, timestamps, paths or padding.

    RGB must already be decoded as HxWx3 uint8 RGB; depth is metric float64.
    Calibration is the numerical camera model, excluding header/frame names.
    """
    rgb = np.asarray(rgb)
    depth = np.asarray(depth, dtype='<f8').copy()
    if rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[2] != 3 or depth.shape != rgb.shape[:2]:
        raise ValueError('aligned canonical RGB/depth required')
    if set(calibration) != {'k', 'd', 'r', 'p', 'distortion_model'}:
        raise ValueError('explicit canonical calibration keys required')
    for key, size in [('k', 9), ('r', 9), ('p', 12)]:
        v = np.asarray(calibration[key], float)
        if v.shape != (size,) or not np.isfinite(v).all():
            raise ValueError('finite calibration shape')
    if not np.isfinite(calibration['d']).all() or not isinstance(calibration['distortion_model'], str):
        raise ValueError('distortion calibration')
    depth[np.isnan(depth)] = np.nan  # normalize NaN payloads
    depth[depth == 0] = 0.          # normalize negative zero
    h = hashlib.sha256()
    h.update(digest(dict(shape=list(rgb.shape), calibration=calibration)).encode())
    h.update(np.ascontiguousarray(rgb).tobytes())
    h.update(np.ascontiguousarray(depth).tobytes())
    return h.hexdigest()


def duplicate_accounting(attempts):
    """Input is complete schedule order (S then C then V), never completion order."""
    seen_content, seen_capture = {}, set()
    result = []
    for row in attempts:
        out = dict(row, duplicate_of=None, fitting_eligible=False)
        if row['status'] != 'completed':
            result.append(out)
            continue
        if not row.get('capture_uuid') or not row.get('content_sha256'):
            raise ValueError('capture identity/content required')
        if row['capture_uuid'] in seen_capture:
            raise ValueError('physical capture reused')
        seen_capture.add(row['capture_uuid'])
        previous = seen_content.get(row['content_sha256'])
        if previous:
            out.update(duplicate_of=previous['attempt_id'],
                       duplicate_scope='within_wave' if previous['wave'] == row['wave'] else 'cross_wave')
        else:
            seen_content[row['content_sha256']] = row
            out['fitting_eligible'] = True
        result.append(out)
    return result


def weights(rows):
    maps = {r['map_id'] for r in rows}
    if not maps:
        raise ValueError('no accepted rows')
    groups = {m: {r['view_group'] for r in rows if r['map_id'] == m} for m in maps}
    counts = Counter((r['map_id'], r['view_group']) for r in rows)
    return np.array([1/(len(maps)*len(groups[r['map_id']])*counts[(r['map_id'], r['view_group'])])
                     for r in rows])


def fit_numeric(x, y, w):
    """Fixed numeric kernel. Real-data authority belongs to fit_joint_score_wave_s."""
    x, y, w = np.asarray(x, float), np.asarray(y, float), np.asarray(w, float)
    if x.ndim != 2 or x.shape[1] != 5 or not len(x) or y.shape != (len(x),) or w.shape != y.shape:
        raise ValueError('aligned five-feature arrays required')
    if not all(np.isfinite(a).all() for a in (x, y, w)):
        raise ValueError('finite fitting arrays')
    if not np.all(x[:, 0] == 1) or np.any(abs(x[:, 1]) > 1) or np.any(x[:, 2:] < 0) or np.any(x[:, 2:] > 1):
        raise ValueError('feature domains')
    if set(y) != {0., 1.} or np.any(w <= 0) or abs(w.sum()-1) > 1e-12:
        raise ValueError('both outcomes and normalized positive weights required')
    bound = .25*float(np.sum(w*np.sum(x*x, axis=1)))+.01
    beta = np.zeros(5)
    updates = 0
    while True:
        loss, gradient = objective_gradient(beta, x, y, w)
        if np.max(abs(gradient)) <= 1e-8:
            break
        if updates == 20000:
            raise ValueError('fixed solver did not converge; no fallback')
        beta -= gradient/bound
        updates += 1
    return dict(coefficients=beta.tolist(), objective=loss, updates=updates,
                gradient_infinity_norm=float(np.max(abs(gradient))), step_size=1/bound,
                feature_order=list(FEATURE_ORDER), penalty=.01, runtime_admitted=False)


def predict(model, x):
    x = np.asarray(x, float)
    beta = np.asarray(model['coefficients'], float)
    if tuple(model['feature_order']) != FEATURE_ORDER or beta.shape != (5,) or not np.isfinite(beta).all():
        raise ValueError('model contract')
    if x.ndim != 2 or x.shape[1] != 5 or not np.isfinite(x).all() or not np.all(x[:, 0] == 1):
        raise ValueError('feature contract')
    if np.any(abs(x[:, 1]) > 1) or np.any(x[:, 2:] < 0) or np.any(x[:, 2:] > 1):
        raise ValueError('feature domain')
    return sigmoid(x@beta)
