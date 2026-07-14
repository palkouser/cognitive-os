"""Provider-output decoding for Problem Representation."""

from cognitive_os.domain.problems import ProblemRepresentation
from cognitive_os.problem.normalization import NormalizedProblemSeed
from cognitive_os.problem.validation import merge_machine_constraints


def decode_representation(
    value: object, seed: NormalizedProblemSeed, *, confidence_threshold: float
) -> ProblemRepresentation:
    representation = ProblemRepresentation.model_validate(value)
    if representation.source_request_hash != seed.request_hash:
        raise ValueError("provider representation has the wrong source request hash")
    merged = merge_machine_constraints(representation, seed.machine_constraints)
    if merged.confidence < confidence_threshold and not merged.requires_clarification():
        raise ValueError("low-confidence representation requires explicit clarification")
    return merged
