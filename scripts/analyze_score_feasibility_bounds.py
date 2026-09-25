"""Conditional analytic support bounds for the unchanged marker score.

Observed colour floors are descriptive, not guaranteed for future observations.
No transformed frames, invented detections, calibration labels or new collection.
"""
import json
from run_stage1_feasibility import ROOT,sha,write


def confidence_floor(color_floor,maximum_error,*,radius=.9):
    if not 0<=color_floor<=1 or not 0<=maximum_error<=radius:
        raise ValueError('colour/error outside score domain')
    # Emitted components have >=min_pixels; support is pixels/(4*min_pixels).
    return (.45*.25+.55*color_floor)*(1-.3*maximum_error/radius)


def error_needed_below_half(color_floor,*,radius=.9):
    raw_floor=.45*.25+.55*color_floor
    return radius/.3*(1-.5/raw_floor)


def analyze():
    source=ROOT/'reports/stage1_design_score_support_20260922_v1.json'
    evidence=json.loads(source.read_bytes())
    provider=ROOT.parent/'risk-calibrated-nav/extensions/research3_landmark_bridge/research3_landmark_bridge/core.py'
    if sha(provider)!=evidence['provider_core_sha256']:raise ValueError('provider source differs')
    classes={}
    for category in sorted({r['category'] for r in evidence['rows']}):
        rows=[r for r in evidence['rows'] if r['category']==category]
        color=min(r['color_score_inferred'] for r in rows)
        error=max(r['association_error_m'] for r in rows)
        classes[category]=dict(observed_emissions=len(rows),observed_minimum_color_score=color,
            observed_maximum_reference_error_m=error,
            conditional_confidence_floor_at_observed_error=confidence_floor(color,error),
            conditional_confidence_floor_at_pose_acceptance_radius=confidence_floor(color,.35),
            necessary_error_m_for_low_bin_at_minimum_support=error_needed_below_half(color),
            future_color_floor_guaranteed=False)
    return dict(schema_version='research3-conditional-score-support-bounds/v1',classes=classes,
        formula='p=(0.45*s+0.55*c)*(1-d/3), s>=0.25, 0<=d<=0.9, provider T=1',
        illustrative_color_floor=.89,illustrative_pose_consistent_floor=confidence_floor(.89,.35),
        illustrative_error_needed_m=error_needed_below_half(.89),
        assumptions=['emitted component meets min_pixels=18; support saturates at 72',
            'unchanged provider association radius .9 and temperature 1',
            'conditional on colour score staying above the stated floor; not guaranteed on unseen views'],
        source_sha256=sha(__file__),input_sha256=sha(source),provider_core_sha256=sha(provider),
        new_observations_generated=False,human_labels_generated=False,protected_data_read=False,
        calibration_eligible=False)


if __name__=='__main__':
    result=analyze();write(ROOT/'reports/conditional_score_bounds_20260922_v1.json',result)
    print(json.dumps(result['classes'],indent=2))
