"""Accepted P2 numerical protocol; no runtime activation or model approval.

Callers must bind genuine reviewed primary rows and complete attempt accounting
before constructing a freeze. These pure functions never manufacture labels.
"""
import math
from collections import Counter, defaultdict

CLASSES = ('chair', 'doorway', 'laboratory_entrance', 'office_entrance')
EPS = 1e-12
GRID = tuple(sorted({1.0} | {math.exp(math.log(.2) + j / 1000 * math.log(25))
                            for j in range(1001)}))


def probability(p, temperature):
    if (type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1
            or type(temperature) not in (int, float)
            or not math.isfinite(temperature) or temperature <= 0):
        raise ValueError('finite raw probability and positive temperature required')
    clipped = min(1 - 1e-9, max(1e-9, p))
    z = (math.log(clipped) - math.log1p(-clipped)) / temperature
    return 1 / (1 + math.exp(-z)) if z >= 0 else math.exp(z) / (1 + math.exp(z))


def reviewed_rows(rows, partition, maps):
    """Strict partition admission; never silently filter forbidden inputs."""
    if partition not in ('development', 'validation') or not maps or len(set(maps)) != len(maps):
        raise ValueError('explicit nonprotected partition and unique required maps needed')
    rows = list(rows)
    ids = set()
    for row in rows:
        if (row.get('partition') != partition or row.get('panel') != 'primary_expansion'
                or row.get('reviewer_type') != 'human' or not row.get('reviewer_name')
                or row.get('map_id') not in maps or row.get('category') not in CLASSES
                or not isinstance(row.get('view_group'), str) or not row['view_group']
                or type(row.get('correct')) is not bool
                or not isinstance(row.get('observation_id'), str) or not row['observation_id']):
            raise ValueError('only bound human-reviewed binary primary rows in the exact partition are eligible')
        identity = (row.get('run_id'), row['observation_id']) if row.get('run_id') else row['observation_id']
        if identity in ids:
            raise ValueError('duplicate observation identity')
        ids.add(identity)
        probability(row.get('probability'), 1.)
    return rows


def coverage(rows, maps):
    deficits = []
    counts = {}
    for category in CLASSES:
        selected = [r for r in rows if r['category'] == category]
        by_map = Counter(r['map_id'] for r in selected)
        bins = [sum((0 if r['probability'] < .5 else 1 if r['probability'] < .8 else 2) == b
                    for r in selected) for b in range(3)]
        outcomes = {str(value).lower(): sum(r['correct'] is value for r in selected) for value in (True, False)}
        counts[category] = dict(maps={m: by_map[m] for m in maps}, bins=bins, outcomes=outcomes)
        deficits.extend(f'{category}/map/{m}' for m in maps if by_map[m] < 1)
        deficits.extend(f'{category}/bin/{b}' for b, n in enumerate(bins) if n < 5)
        deficits.extend(f'{category}/outcome/{v}' for v, n in outcomes.items() if n < 5)
    return dict(passed=not deficits, deficits=deficits, counts=counts)


def weights(rows):
    groups = defaultdict(Counter)
    for row in rows:
        groups[row['map_id']][row['view_group']] += 1
    return [1 / (len(groups) * len(groups[r['map_id']]) * groups[r['map_id']][r['view_group']])
            for r in rows]


def fit_class(rows):
    w = weights(rows)
    logits = []
    for r in rows:
        p = min(1 - 1e-9, max(1e-9, r['probability']))
        logits.append(math.log(p) - math.log1p(-p))
    losses = []
    for t in GRID:
        terms = []
        for r, weight, logit in zip(rows, w, logits):
            z = logit / t
            # Stable softplus(-z) for positives, softplus(z) for negatives.
            x = -z if r['correct'] else z
            terms.append(weight * (max(x, 0) + math.log1p(math.exp(-abs(x)))))
        losses.append(math.fsum(terms))
    minimum = min(losses)
    chosen = min((i for i, loss in enumerate(losses) if loss <= minimum + EPS),
                 key=lambda i: (abs(math.log(GRID[i])), GRID[i]))
    return dict(temperature=GRID[chosen], objective=losses[chosen],
                boundary=chosen in (0, len(GRID) - 1), grid=list(GRID), objectives=losses,
                samples=len(rows))


def fit_development(rows, maps):
    rows = reviewed_rows(rows, 'development', maps)
    audit = coverage(rows, maps)
    if not audit['passed']:
        return dict(status='coverage_blocked', coverage=audit, classes=None)
    return dict(status='numerical_candidate_not_frozen', coverage=audit,
                classes={c: fit_class([r for r in rows if r['category'] == c]) for c in CLASSES},
                actual_model_approved=False, validation_used_for_fitting=False)


def metrics(rows, probabilities, sample_weights):
    if not rows or len(rows) != len(probabilities) or len(rows) != len(sample_weights):
        raise ValueError('nonempty aligned metric inputs required')
    bins = []
    for b in range(10):
        indices = [i for i, p in enumerate(probabilities) if min(int(p * 10), 9) == b]
        mass = math.fsum(sample_weights[i] for i in indices)
        confidence = math.fsum(sample_weights[i] * probabilities[i] for i in indices) / mass if mass else None
        accuracy = math.fsum(sample_weights[i] * rows[i]['correct'] for i in indices) / mass if mass else None
        bins.append(dict(count=len(indices), weight=mass, confidence=confidence, accuracy=accuracy,
                         gap=abs(confidence - accuracy) if mass else None))
    return dict(brier=math.fsum(w * (p - r['correct']) ** 2 for w, p, r in zip(sample_weights, probabilities, rows)),
                ece=math.fsum(b['weight'] * b['gap'] for b in bins if b['weight']),
                mce=max(b['gap'] for b in bins if b['weight']), bins=bins)


def evaluate(rows, partition, maps, temperatures):
    rows = reviewed_rows(rows, partition, maps)
    if set(temperatures) != set(CLASSES):
        raise ValueError('exact four class temperatures required')
    result = {'coverage': coverage(rows, maps), 'classes': {}}
    for c in CLASSES:
        selected = [r for r in rows if r['category'] == c]
        if not selected:
            result['classes'][c] = None
            continue
        raw = [r['probability'] for r in selected]
        calibrated = [probability(p, temperatures[c]) for p in raw]
        result['classes'][c] = {
            label: {'weighted': metrics(selected, ps, weights(selected)),
                    'unweighted': metrics(selected, ps, [1 / len(selected)] * len(selected))}
            for label, ps in [('raw', raw), ('calibrated', calibrated)]}
    result['aggregate'] = None
    if all(result['classes'].values()):
        result['aggregate'] = {label: {
            'macro_brier': math.fsum(result['classes'][c][label]['weighted']['brier'] for c in CLASSES) / 4,
            'macro_ece': math.fsum(result['classes'][c][label]['weighted']['ece'] for c in CLASSES) / 4,
            'max_mce': max(result['classes'][c][label]['weighted']['mce'] for c in CLASSES)}
            for label in ('raw', 'calibrated')}
    return result


def leave_one_map_out(rows, maps):
    rows = reviewed_rows(rows, 'development', maps)
    if len(maps) < 2:
        raise ValueError('at least two development maps required')
    folds = []
    for held_map in maps:
        training = [r for r in rows if r['map_id'] != held_map]
        fit = fit_development(training, [m for m in maps if m != held_map])
        held = [r for r in rows if r['map_id'] == held_map]
        report = None if fit['classes'] is None else evaluate(
            held, 'development', [held_map], {c: fit['classes'][c]['temperature'] for c in CLASSES})
        folds.append(dict(held_development_map=held_map, fit=fit, diagnostic=report))
    return folds


def admission_screen(development_coverage, validation, *, full_attempt_accounting_verified):
    if type(full_attempt_accounting_verified) is not bool:
        raise ValueError('explicit attempt-accounting evidence required')
    gates = dict(development_coverage=development_coverage['passed'],
                 validation_coverage=validation['coverage']['passed'],
                 full_attempt_accounting=full_attempt_accounting_verified)
    aggregate = validation['aggregate']
    if aggregate is None:
        gates['metrics_available'] = False
    else:
        before, after = aggregate['raw'], aggregate['calibrated']
        gates.update(macro_brier_improved=before['macro_brier'] - after['macro_brier'] > EPS,
                     macro_ece_not_degraded=after['macro_ece'] <= before['macro_ece'] + EPS,
                     max_mce_not_degraded=after['max_mce'] <= before['max_mce'] + EPS,
                     every_class_brier_not_degraded=all(
                         row['calibrated']['weighted']['brier'] <= row['raw']['weighted']['brier'] + EPS
                         for row in validation['classes'].values()))
    return dict(point_estimate_screen_passed=all(gates.values()), gates=gates,
                human_model_approval=False, downstream_benefit_established=False)
