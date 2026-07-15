"""Bounded deterministic contradiction rules."""

from cognitive_os.domain.semantic_memory import (
    Cardinality,
    ClaimIdentity,
    ClaimRevision,
    ClaimRevisionReference,
    ClaimTemporalInterval,
    ContradictionCandidate,
    EvidenceLink,
    EvidenceRelation,
    SemanticLiteral,
    SemanticLiteralKind,
)

from .canonicalization import canonical_value
from .predicates import PredicateRegistry


def detect_functional_conflict(
    left_identity: ClaimIdentity,
    left: ClaimRevision,
    right_identity: ClaimIdentity,
    right: ClaimRevision,
    registry: PredicateRegistry,
) -> ContradictionCandidate | None:
    if (
        left_identity.scope != right_identity.scope
        or left_identity.canonical_subject_key != right_identity.canonical_subject_key
        or left_identity.predicate_id != right_identity.predicate_id
        or left.claim_id == right.claim_id
    ):
        return None
    descriptor = registry.require(left_identity.predicate_id)
    if descriptor.cardinality is not Cardinality.FUNCTIONAL:
        return None
    if canonical_value(left.object) == canonical_value(right.object):
        return None
    if not left.valid_interval.overlaps(right.valid_interval):
        return None
    start = max(left.valid_interval.valid_from, right.valid_interval.valid_from)
    ends = [
        value for value in (left.valid_interval.valid_to, right.valid_interval.valid_to) if value
    ]
    end = min(ends) if ends else None
    return ContradictionCandidate(
        claims=(
            ClaimRevisionReference(claim_id=left.claim_id, revision=left.revision),
            ClaimRevisionReference(claim_id=right.claim_id, revision=right.revision),
        ),
        overlap=ClaimTemporalInterval(valid_from=start, valid_to=end),
        rule_id="functional_overlap.v1",
        deterministic=True,
    )


def detect_registered_conflict(
    left_identity: ClaimIdentity,
    left: ClaimRevision,
    right_identity: ClaimIdentity,
    right: ClaimRevision,
    registry: PredicateRegistry,
) -> ContradictionCandidate | None:
    if (
        left_identity.scope != right_identity.scope
        or left_identity.canonical_subject_key != right_identity.canonical_subject_key
        or left.claim_id == right.claim_id
        or not left.valid_interval.overlaps(right.valid_interval)
    ):
        return None
    left_descriptor = registry.require(left_identity.predicate_id)
    right_descriptor = registry.require(right_identity.predicate_id)
    same_predicate = left_identity.predicate_id == right_identity.predicate_id
    boolean_opposite = (
        same_predicate
        and left_descriptor.negatable
        and isinstance(left.object, SemanticLiteral)
        and isinstance(right.object, SemanticLiteral)
        and left.object.literal_kind is SemanticLiteralKind.BOOLEAN
        and right.object.literal_kind is SemanticLiteralKind.BOOLEAN
        and left.object.value != right.object.value
    )
    exclusive = (
        left_descriptor.exclusive_value_group is not None
        and left_descriptor.exclusive_value_group == right_descriptor.exclusive_value_group
        and (
            left_identity.predicate_id != right_identity.predicate_id
            or canonical_value(left.object) != canonical_value(right.object)
        )
    )
    if not boolean_opposite and not exclusive:
        return None
    return _candidate(
        left,
        right,
        "boolean_opposite.v1" if boolean_opposite else "exclusive_value_group.v1",
    )


def detect_evidence_conflict(
    left: ClaimRevision,
    left_evidence: tuple[EvidenceLink, ...],
    right: ClaimRevision,
    right_evidence: tuple[EvidenceLink, ...],
) -> ContradictionCandidate | None:
    if left.claim_id == right.claim_id or not left.valid_interval.overlaps(right.valid_interval):
        return None
    for left_link in left_evidence:
        for right_link in right_evidence:
            if left_link.source == right_link.source and {
                left_link.relation,
                right_link.relation,
            } == {EvidenceRelation.SUPPORTS, EvidenceRelation.CONTRADICTS}:
                return _candidate(left, right, "explicit_evidence_conflict.v1")
    return None


def _candidate(left: ClaimRevision, right: ClaimRevision, rule_id: str) -> ContradictionCandidate:
    ends = [
        value for value in (left.valid_interval.valid_to, right.valid_interval.valid_to) if value
    ]
    return ContradictionCandidate(
        claims=(
            ClaimRevisionReference(claim_id=left.claim_id, revision=left.revision),
            ClaimRevisionReference(claim_id=right.claim_id, revision=right.revision),
        ),
        overlap=ClaimTemporalInterval(
            valid_from=max(left.valid_interval.valid_from, right.valid_interval.valid_from),
            valid_to=min(ends) if ends else None,
        ),
        rule_id=rule_id,
        deterministic=True,
    )
