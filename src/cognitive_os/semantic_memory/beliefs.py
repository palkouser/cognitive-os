"""Legal append-only belief transitions and confidence aggregation."""

from cognitive_os.domain.semantic_memory import BeliefStatus, ConfidenceDimensions

_LEGAL_TRANSITIONS = {
    BeliefStatus.UNKNOWN: frozenset({BeliefStatus.PROPOSED, BeliefStatus.RETRACTED}),
    BeliefStatus.PROPOSED: frozenset(
        {BeliefStatus.SUPPORTED, BeliefStatus.DISPUTED, BeliefStatus.RETRACTED}
    ),
    BeliefStatus.SUPPORTED: frozenset(
        {BeliefStatus.DISPUTED, BeliefStatus.SUPERSEDED, BeliefStatus.RETRACTED}
    ),
    BeliefStatus.DISPUTED: frozenset(
        {BeliefStatus.SUPPORTED, BeliefStatus.SUPERSEDED, BeliefStatus.RETRACTED}
    ),
    BeliefStatus.SUPERSEDED: frozenset(),
    BeliefStatus.RETRACTED: frozenset(),
}


def assert_legal_transition(current: BeliefStatus, target: BeliefStatus) -> None:
    if target not in _LEGAL_TRANSITIONS[current]:
        raise ValueError(f"illegal belief transition: {current.value} -> {target.value}")


def aggregate_confidence(
    *,
    extraction: float,
    source: float | None = None,
    grounding: float | None = None,
    evidence: float | None = None,
    verification: float | None = None,
    consistency: float | None = None,
) -> ConfidenceDimensions:
    values = [
        item
        for item in (extraction, source, grounding, evidence, verification, consistency)
        if item is not None
    ]
    return ConfidenceDimensions(
        extraction_confidence=extraction,
        source_reliability=source,
        grounding_confidence=grounding,
        evidence_confidence=evidence,
        verification_confidence=verification,
        consistency_confidence=consistency,
        overall_confidence=min(values),
    )
