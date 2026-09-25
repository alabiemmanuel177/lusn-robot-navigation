"""Catalogue-blind contextual hypotheses, never verified identities or probabilities."""
import math
import re


def text_category(text):
    token = ' '.join(re.findall(r'[A-Z]+', text.upper()))
    return {'LAB': 'laboratory_entrance', 'LABORATORY': 'laboratory_entrance',
            'OFFICE': 'office_entrance'}.get(token)


def contextual_candidates(doorways, texts):
    """Retain every plausible pair, including competing category evidence.

    Sign centre must fall inside the doorway box expanded horizontally by half
    its width and vertically by half its height. This is a fixed engineering
    hypothesis, not a learned association rule or nearest-sign assignment.
    """
    results = []
    for i, door in enumerate(doorways):
        x0, y0, x1, y1 = map(float, door['xyxy'])
        if not all(map(math.isfinite, (x0, y0, x1, y1))) or x1 <= x0 or y1 <= y0:
            raise ValueError('finite nonempty doorway box required')
        w, h = x1-x0, y1-y0
        evidence = []
        for j, text in enumerate(texts):
            category = text_category(text['text'])
            quad = text['quad']
            if len(quad) != 4 or any(len(p) != 2 or not all(map(math.isfinite,p)) for p in quad):
                raise ValueError('finite quadrilateral required')
            cx = sum(p[0] for p in quad)/4
            cy = sum(p[1] for p in quad)/4
            if category and x0-w/2 <= cx <= x1+w/2 and y0-h/2 <= cy <= y1+h/2:
                evidence.append(dict(text_index=j, visual_category=category,
                                     text_score=text['score']))
        results.append(dict(doorway_index=i, xyxy=door['xyxy'],
            detector_score=door['raw_score'], context=evidence,
            status='no_context' if not evidence else 'ambiguous_context' if len(evidence)>1 else 'context_candidate',
            joint_probability=None, human_verdict=None, calibration_eligible=False))
    return results
