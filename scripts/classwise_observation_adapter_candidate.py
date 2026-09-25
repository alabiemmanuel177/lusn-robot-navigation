"""Offline P2 observation adapter candidate; deliberately not a ROS runtime hook.

Keep the frozen provider at raw T=1. A future approved R3 consumer may apply this
mapping after association, with raw observations retained on a separate channel.
This module does not load approvals, publish observations, or declare a model fit.
"""
from copy import deepcopy
from dataclasses import dataclass,replace
import math
import re

from language_nav.contracts import SemanticObservationContract
from classwise_temperature_candidate import CLASSES,GRID,probability


@dataclass(frozen=True)
class CandidateMapping:
    raw: SemanticObservationContract
    calibrated: SemanticObservationContract
    receipt: dict


def validate_parameters(temperatures,model_sha256):
    if (not isinstance(temperatures,dict) or set(temperatures)!=set(CLASSES)
            or any(type(t) not in (int,float) or not math.isfinite(t) or t not in GRID
                   for t in temperatures.values())):
        raise ValueError('exact four P2 grid temperatures required')
    if not isinstance(model_sha256,str) or not re.fullmatch('[a-f0-9]{64}',model_sha256):
        raise ValueError('explicit candidate model digest required; it is not approval')


def candidate_mapping(observation,temperatures,*,model_sha256):
    if type(observation) is not SemanticObservationContract:
        raise TypeError('one raw semantic observation required; mapped candidates cannot be reapplied')
    validate_parameters(temperatures,model_sha256)
    if observation.category not in CLASSES:raise ValueError('class has no approved calibration family')
    if not observation.observation_id or not observation.entity_id:
        raise ValueError('identified observation required')
    temperature=temperatures[observation.category]
    q=probability(observation.confidence,temperature)
    raw=deepcopy(observation)
    mapped=replace(deepcopy(observation),confidence=q)
    return CandidateMapping(raw,mapped,dict(schema_version='research3-candidate-calibration-mapping/v1',
        observation_id=observation.observation_id,category=observation.category,
        raw_confidence=observation.confidence,calibrated_confidence=q,temperature=temperature,
        model_sha256=model_sha256,provider_temperature_required=1.0,
        runtime_authorized=False,model_approved=False,calibration_fit_performed=False))


def candidate_batch(observations,temperatures,*,model_sha256):
    """Preserve emission order/count. Empty input remains a nondetection."""
    validate_parameters(temperatures,model_sha256)
    observations=list(observations)
    identities=[(o.source,o.observation_id) for o in observations]
    if len(identities)!=len(set(identities)):raise ValueError('duplicate raw observation identity')
    return [candidate_mapping(o,temperatures,model_sha256=model_sha256) for o in observations]
