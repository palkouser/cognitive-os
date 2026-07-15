"""Credential-free deterministic Sprint 10 semantic fixture proposals."""

import re
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from cognitive_os.domain.memory import CodeContextMemoryContent, MemoryRecord, MemoryRevision
from cognitive_os.domain.semantic_memory import (
    ClaimProposal,
    ClaimTemporalInterval,
    ExtractionBudget,
    GroundedSourceSpan,
    GroundingMode,
    ObservationProposal,
    SemanticEntityRef,
    SemanticExtractionProposal,
    SemanticLiteral,
    SemanticLiteralKind,
    SemanticSourceRef,
    SemanticSourceType,
)

from .predicates import PredicateRegistry


def project_version_proposal(
    record: MemoryRecord,
    revision: MemoryRevision,
    registry: PredicateRegistry,
) -> SemanticExtractionProposal:
    """Extract the exact Python version from a typed Sprint 9 code-context field."""
    if not isinstance(revision.content, CodeContextMemoryContent):
        raise ValueError("project version fixture requires code-context memory")
    match = re.match(r"^Python ([^;]+);", revision.content.repository_profile)
    if match is None or match.group(1) == "unknown":
        raise ValueError("code-context memory has no exact Python version")
    registry.require("project.python_version")
    root = f"sprint10:{record.memory_id}:{revision.revision}:{revision.content_hash}"
    observation_id = uuid5(NAMESPACE_URL, root + ":observation")
    source = SemanticSourceRef(
        source_type=SemanticSourceType.MEMORY_REVISION,
        source_id=record.memory_id,
        revision=revision.revision,
        content_hash=revision.content_hash,
    )
    span = GroundedSourceSpan(
        source=source,
        mode=GroundingMode.MEMORY_FIELD,
        path="content.repository_profile",
        excerpt_hash=sha256(revision.content.repository_profile.encode()).hexdigest(),
    )
    return SemanticExtractionProposal(
        extraction_id=uuid5(NAMESPACE_URL, root),
        registry_snapshot_hash=registry.snapshot_hash(),
        observations=(
            ObservationProposal(
                proposal_id=observation_id,
                content=revision.content.repository_profile,
                source_spans=(span,),
            ),
        ),
        claims=(
            ClaimProposal(
                proposal_id=uuid5(NAMESPACE_URL, root + ":claim"),
                subject=SemanticEntityRef(
                    entity_id="project:cognitive-os",
                    entity_type="project",
                    display_label="Cognitive OS",
                ),
                predicate_id="project.python_version",
                object=SemanticLiteral(
                    literal_kind=SemanticLiteralKind.VERSION,
                    value=match.group(1),
                    unit=None,
                ),
                valid_interval=ClaimTemporalInterval(valid_from=revision.created_at),
                observation_proposal_ids=(observation_id,),
            ),
        ),
        budget=ExtractionBudget(
            maximum_observations=1,
            maximum_claims=1,
            maximum_evidence_links=1,
            maximum_relations=0,
        ),
    )
