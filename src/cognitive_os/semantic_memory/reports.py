"""Deterministic exact-reference semantic knowledge reports."""

from typing import Any

from cognitive_os.domain.semantic_memory import (
    BeliefStatus,
    ClaimRelation,
    ClaimRelationType,
    ClaimRevision,
    ContradictionRevision,
    ContradictionStatus,
    EvidenceLink,
)


def open_contradiction_report(
    revisions: tuple[ContradictionRevision, ...],
) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "contradiction_id": str(item.contradiction_id),
            "revision": item.revision,
            "severity": item.severity.value,
            "claims": [reference.model_dump(mode="json") for reference in item.claims],
            "evidence_ids": [str(value) for value in item.evidence_ids],
        }
        for item in sorted(revisions, key=lambda value: str(value.contradiction_id))
        if item.status is ContradictionStatus.OPEN
    )


def claim_timeline(revisions: tuple[ClaimRevision, ...]) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "claim_id": str(item.claim_id),
            "revision": item.revision,
            "belief_status": item.belief_status.value,
            "valid_interval": item.valid_interval.model_dump(mode="json"),
            "recorded_at": item.recorded_at.isoformat(),
            "content_hash": item.content_hash,
        }
        for item in sorted(revisions, key=lambda value: value.revision)
    )


def supersession_chain(relations: tuple[ClaimRelation, ...]) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "relation_id": str(item.relation_id),
            "source": item.source.model_dump(mode="json"),
            "target": item.target.model_dump(mode="json"),
        }
        for item in sorted(relations, key=lambda value: str(value.relation_id))
        if item.relation_type is ClaimRelationType.SUPERSEDES
    )


def evidence_matrix(links: tuple[EvidenceLink, ...]) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "evidence_id": str(item.evidence_id),
            "claim": item.claim.model_dump(mode="json"),
            "relation": item.relation.value,
            "source": item.source.model_dump(mode="json"),
            "strength": item.strength,
        }
        for item in sorted(
            links,
            key=lambda value: (
                str(value.claim.claim_id),
                value.claim.revision,
                str(value.evidence_id),
            ),
        )
    )


def unresolved_disputed_claims(
    revisions: tuple[ClaimRevision, ...],
) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "claim_id": str(item.claim_id),
            "revision": item.revision,
            "content_hash": item.content_hash,
        }
        for item in sorted(revisions, key=lambda value: (str(value.claim_id), value.revision))
        if item.belief_status is BeliefStatus.DISPUTED
    )
