"""R3-only visual evidence contract. Regions are not localized landmark objects."""
import math

PROMPTS = {
    'chair': 'a chair with a seat, backrest and legs in an indoor corridor',
    'doorway': 'an open doorway with a door frame leading into a room',
    'laboratory_entrance': 'a laboratory entrance with a LAB sign above the opening',
    'office_entrance': 'an office entrance with an OFFICE sign above the opening',
    'sign': 'a sign or coloured panel on a wall without a visible entrance',
    'background': 'a wall or floor without a visible chair, doorway or entrance',
}


def regions(width, height):
    if type(width) is not int or type(height) is not int or width < 4 or height < 4:
        raise ValueError('integer image dimensions >=4 required')
    w, h = width // 2, height // 2
    result = [('full', (0, 0, width, height))]
    for j, y in enumerate((0, (height-h)//2, height-h)):
        for i, x in enumerate((0, (width-w)//2, width-w)):
            result.append((f'grid-{j}-{i}', (x, y, x+w, y+h)))
    return result


def evidence(region_id, box, cosine, logit_scale):
    if set(cosine) != set(PROMPTS) or not all(math.isfinite(v) and -1.00001 <= v <= 1.00001 for v in cosine.values()):
        raise ValueError('exact finite cosine vector required')
    if not math.isfinite(logit_scale) or logit_scale <= 0:
        raise ValueError('positive fixed checkpoint scale required')
    logits = {k: v * logit_scale for k, v in cosine.items()}
    peak = max(logits.values())
    values = {k: math.exp(v-peak) for k, v in logits.items()}
    total = sum(values.values())
    return dict(schema_version='research3-visual-region-evidence-candidate/v1',
        region_id=region_id, box=list(box), cosine_similarity=cosine,
        relative_prompt_scores={k: v/total for k, v in values.items()},
        top_prompt=max(logits, key=logits.get), raw_score_meaning='relative_fixed_prompt_softmax_not_joint_correctness_probability',
        object_localized=False, entity_id=None, map_pose=None, human_verdict=None,
        calibration_eligible=False, runtime_admitted=False)
