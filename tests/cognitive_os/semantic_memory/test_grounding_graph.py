from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

import pytest

from cognitive_os.domain.memory import (
    MemoryCreator,
    MemoryCreatorType,
    MemoryProvenanceBundle,
    MemoryScope,
    MemoryScopeType,
    MemorySensitivity,
    MemorySourceIdentity,
    MemorySourceRef,
    MemorySourceType,
    MemoryType,
    MemoryWriteRequest,
    ObservationMemoryContent,
)
from cognitive_os.domain.semantic_memory import (
    BeliefStatus,
    Cardinality,
    ClaimIdentity,
    ClaimRelation,
    ClaimRelationType,
    ClaimRevision,
    ClaimRevisionReference,
    ClaimTemporalInterval,
    GroundedSourceSpan,
    GroundingMode,
    PredicateDescriptor,
    SemanticActor,
    SemanticActorType,
    SemanticLiteral,
    SemanticLiteralKind,
    SemanticSourceRef,
    SemanticSourceType,
    claim_revision_hash,
)
from cognitive_os.memory.repository import InMemoryMemoryRepository
from cognitive_os.semantic_memory.beliefs import aggregate_confidence
from cognitive_os.semantic_memory.contradictions import detect_registered_conflict
from cognitive_os.semantic_memory.errors import SemanticIntegrityError
from cognitive_os.semantic_memory.graph import (
    bounded_neighbours,
    has_restricted_cycle,
    networkx_snapshot,
)
from cognitive_os.semantic_memory.grounding import TrustedSourceResolver
from cognitive_os.semantic_memory.predicates import PredicateRegistry

NOW = datetime(2026, 7, 15, tzinfo=UTC)


@pytest.mark.asyncio
async def test_memory_revision_grounding_checks_exact_field_and_hash() -> None:
    repository = InMemoryMemoryRepository()
    memory_id, source_id = UUID(int=101), UUID(int=102)
    _, revision = await repository.create_memory(
        MemoryWriteRequest(
            request_id=UUID(int=103),
            idempotency_key="a" * 64,
            memory_id=memory_id,
            memory_type=MemoryType.OBSERVATION,
            scope=MemoryScope(scope_type=MemoryScopeType.PROJECT, scope_id="cognitive-os"),
            title="Grounded source",
            content=ObservationMemoryContent(
                observation="Python 3.12",
                evidence_summary="Exact fixture",
            ),
            confidence=1,
            salience=1,
            sensitivity=MemorySensitivity.INTERNAL,
            provenance=MemoryProvenanceBundle(
                sources=(
                    MemorySourceRef(
                        identity=MemorySourceIdentity(
                            source_type=MemorySourceType.EVENT,
                            source_id=source_id,
                            content_hash="b" * 64,
                        ),
                        source_hash="b" * 64,
                    ),
                )
            ),
            actor=MemoryCreator(
                creator_type=MemoryCreatorType.INGESTION_SERVICE,
                creator_id="fixture",
            ),
        )
    )
    source = SemanticSourceRef(
        source_type=SemanticSourceType.MEMORY_REVISION,
        source_id=memory_id,
        revision=1,
        content_hash=revision.content_hash,
    )
    span = GroundedSourceSpan(
        source=source,
        mode=GroundingMode.MEMORY_FIELD,
        path="content.observation",
        excerpt_hash=sha256(b"Python 3.12").hexdigest(),
    )
    resolver = TrustedSourceResolver(repository)
    await resolver.validate_span(span)
    with pytest.raises(SemanticIntegrityError, match="excerpt hash"):
        await resolver.validate_span(span.model_copy(update={"excerpt_hash": "c" * 64}))


def relation(source: int, target: int) -> ClaimRelation:
    return ClaimRelation(
        relation_id=UUID(int=source * 10 + target),
        source=ClaimRevisionReference(claim_id=UUID(int=source), revision=1),
        target=ClaimRevisionReference(claim_id=UUID(int=target), revision=1),
        relation_type=ClaimRelationType.SUPERSEDES,
        valid_interval=ClaimTemporalInterval(valid_from=NOW),
        provenance=SemanticSourceRef(
            source_type=SemanticSourceType.EVENT,
            source_id=UUID(int=200),
            content_hash="d" * 64,
        ),
        created_at=NOW,
    )


def test_graph_projection_is_bounded_deterministic_and_cycle_aware() -> None:
    relations = (relation(1, 2), relation(2, 3))
    start = ClaimRevisionReference(claim_id=UUID(int=1), revision=1)
    assert [
        item.claim_id.int
        for item in bounded_neighbours(
            relations, start, maximum_depth=2, maximum_nodes=3, maximum_edges=2
        )
    ] == [1, 2, 3]
    assert not has_restricted_cycle(relations)
    assert has_restricted_cycle((*relations, relation(3, 1)))
    with pytest.raises(ValueError, match="edge limit"):
        bounded_neighbours(relations, start, maximum_depth=2, maximum_nodes=3, maximum_edges=1)


def test_optional_networkx_snapshot_is_exact_bounded_and_deterministic() -> None:
    pytest.importorskip("networkx")
    relations = (relation(1, 2), relation(2, 3))
    first = networkx_snapshot(relations, maximum_nodes=3, maximum_edges=2)
    assert first == networkx_snapshot(relations, maximum_nodes=3, maximum_edges=2)
    assert len(first["nodes"]) == 3
    assert first["connected_components"] == [first["nodes"]]
    assert first["cycles"] == []
    with pytest.raises(ValueError, match="node limit"):
        networkx_snapshot(relations, maximum_nodes=2, maximum_edges=2)


def test_registered_boolean_opposites_are_contradictory() -> None:
    registry = PredicateRegistry()
    registry.register(
        PredicateDescriptor(
            predicate_id="project.is_active",
            version="1",
            display_name="Project is active",
            description="Whether the project is active.",
            allowed_subject_types=("project",),
            allowed_object_types=(SemanticLiteralKind.BOOLEAN,),
            cardinality=Cardinality.MULTI,
            temporal_behavior="bitemporal",
            negatable=True,
            rendering_label="project.is_active",
            contradiction_rule="boolean_opposite",
        )
    )
    registry.freeze()
    scope = MemoryScope(scope_type=MemoryScopeType.PROJECT, scope_id="cognitive-os")
    actor = SemanticActor(actor_type=SemanticActorType.OPERATOR, actor_id="test")

    def claim(claim_id: UUID, value: bool) -> tuple[ClaimIdentity, ClaimRevision]:
        identity = ClaimIdentity(
            claim_id=claim_id,
            scope=scope,
            canonical_subject_key="project:cognitive-os",
            predicate_id="project.is_active",
        )
        interval = ClaimTemporalInterval(valid_from=NOW)
        object_value = SemanticLiteral(
            literal_kind=SemanticLiteralKind.BOOLEAN, value=value, unit=None
        )
        confidence = aggregate_confidence(extraction=1)
        statement = f"Project active: {value}"
        revision = ClaimRevision(
            claim_id=claim_id,
            revision=1,
            object=object_value,
            statement=statement,
            belief_status=BeliefStatus.PROPOSED,
            confidence=confidence,
            valid_interval=interval,
            reason="test",
            recorded_at=NOW,
            created_by=actor,
            evidence_snapshot_hash="e" * 64,
            content_hash=claim_revision_hash(
                claim_id=claim_id,
                revision=1,
                object_value=object_value,
                statement=statement,
                belief_status=BeliefStatus.PROPOSED,
                confidence=confidence,
                valid_interval=interval,
                reason="test",
                evidence_snapshot_hash="e" * 64,
            ),
        )
        return identity, revision

    left_identity, left = claim(UUID(int=301), True)
    right_identity, right = claim(UUID(int=302), False)
    candidate = detect_registered_conflict(left_identity, left, right_identity, right, registry)
    assert candidate is not None
    assert candidate.rule_id == "boolean_opposite.v1"
