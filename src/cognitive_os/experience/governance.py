"""Candidate validation, append-only status, and deterministic export."""

from __future__ import annotations

import json
from hashlib import sha256

from cognitive_os.domain.experience import (
    CandidateRevision,
    ExperienceCandidate,
    ExperienceCandidateStatus,
)

from .errors import ExperiencePolicyError

_TRANSITIONS = {
    ExperienceCandidateStatus.PROPOSED: {
        ExperienceCandidateStatus.VALIDATED,
        ExperienceCandidateStatus.REJECTED,
    },
    ExperienceCandidateStatus.VALIDATED: {
        ExperienceCandidateStatus.ROUTED,
        ExperienceCandidateStatus.REJECTED,
        ExperienceCandidateStatus.SUPERSEDED,
    },
    ExperienceCandidateStatus.ROUTED: {ExperienceCandidateStatus.SUPERSEDED},
    ExperienceCandidateStatus.REJECTED: set(),
    ExperienceCandidateStatus.SUPERSEDED: set(),
}


def validate_candidate(candidate: ExperienceCandidate, snapshot_hash: str) -> tuple[str, ...]:
    errors: list[str] = []
    if not candidate.source_refs:
        errors.append("missing candidate source")
    if not candidate.evidence_refs:
        errors.append("missing candidate evidence")
    if candidate.structured_body.get("snapshot_hash") != snapshot_hash:
        errors.append("candidate snapshot provenance mismatch")
    if candidate.status is not ExperienceCandidateStatus.PROPOSED:
        errors.append("compiler candidate does not begin as proposed")
    if not candidate.target_schema_version.startswith("v1/"):
        errors.append("unknown candidate destination schema")
    return tuple(errors)


def append_candidate_status(
    candidate: ExperienceCandidate,
    history: tuple[CandidateRevision, ...],
    target: ExperienceCandidateStatus,
    *,
    actor_id: str,
    reason: str,
) -> CandidateRevision:
    current = history[-1].status if history else candidate.status
    if target not in _TRANSITIONS[current]:
        raise ExperiencePolicyError(
            f"invalid candidate lifecycle transition: {current.value} -> {target.value}"
        )
    return CandidateRevision(
        candidate_id=candidate.candidate_id,
        revision=(history[-1].revision + 1 if history else 2),
        previous_status=current,
        status=target,
        actor_id=actor_id,
        reason=reason,
        created_at=candidate.created_at,
    )


def export_candidate(candidate: ExperienceCandidate) -> dict[str, bytes]:
    """Build the Sprint 15 hand-off package without writing a destination."""

    payloads = {
        "candidate.json": candidate.model_dump(mode="json", exclude={"structured_body"}),
        "candidate-body.json": candidate.structured_body,
        "sources.json": [item.model_dump(mode="json") for item in candidate.source_refs],
        "evidence.json": list(candidate.evidence_refs),
        "generalizability.json": candidate.generalizability.model_dump(mode="json"),
        "limitations.json": list(candidate.limitations),
        "verification.json": {
            "compiler_status": candidate.status.value,
            "destination_approved": False,
        },
    }
    encoded = {
        name: json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        for name, value in payloads.items()
    }
    manifest = {
        "candidate_id": str(candidate.candidate_id),
        "candidate_revision": candidate.candidate_revision,
        "files": {name: sha256(data).hexdigest() for name, data in sorted(encoded.items())},
        "destination_write_performed": False,
    }
    encoded["manifest.json"] = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    return encoded
