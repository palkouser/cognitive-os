from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from cognitive_os.domain.memory import (
    EpisodeMemoryContent,
    MemoryCreator,
    MemoryCreatorType,
    MemoryProvenanceBundle,
    MemoryQuery,
    MemoryRetrievalMode,
    MemoryScope,
    MemoryScopeType,
    MemorySensitivity,
    MemorySourceIdentity,
    MemorySourceRef,
    MemorySourceType,
    MemoryStatus,
    MemoryTransitionReason,
    MemoryType,
    MemoryWriteRequest,
    memory_revision_hash,
)

NOW = datetime(2026, 7, 15, tzinfo=UTC)
MEMORY_ID = UUID("00000000-0000-0000-0000-000000000901")
TASK_RUN_ID = UUID("00000000-0000-0000-0000-000000000902")
SOURCE_ID = UUID("00000000-0000-0000-0000-000000000903")
HASH = "a" * 64


def episode() -> EpisodeMemoryContent:
    return EpisodeMemoryContent(
        task_run_id=TASK_RUN_ID,
        title="Accepted coding task",
        problem_summary="Repair a bounded defect.",
        repository_identity=HASH,
        base_commit="b" * 40,
        outcome="accepted",
        patch_attempt_count=1,
        repair_count=0,
        verifier_summary="All required checks passed.",
        trajectory_hash="c" * 64,
    )


def provenance() -> MemoryProvenanceBundle:
    return MemoryProvenanceBundle(
        sources=(
            MemorySourceRef(
                identity=MemorySourceIdentity(
                    source_type=MemorySourceType.CODING_TRAJECTORY,
                    source_id=SOURCE_ID,
                    content_hash="c" * 64,
                ),
                source_hash="c" * 64,
            ),
        )
    )


def test_core_enums_exclude_fact_and_contracts_are_immutable() -> None:
    assert "fact" not in {item.value for item in MemoryType}
    scope = MemoryScope(scope_type=MemoryScopeType.PROJECT, scope_id="cognitive-os")
    with pytest.raises(ValidationError):
        scope.scope_id = "changed"  # type: ignore[misc]


@pytest.mark.parametrize("scope_id", ["/home/user/repository", r"C:\Users\user\repo"])
def test_repository_scope_rejects_host_paths(scope_id: str) -> None:
    with pytest.raises(ValidationError, match="stable identity"):
        MemoryScope(scope_type=MemoryScopeType.REPOSITORY, scope_id=scope_id)


def test_write_request_requires_matching_typed_content_and_provenance() -> None:
    request = MemoryWriteRequest(
        request_id=UUID("00000000-0000-0000-0000-000000000904"),
        idempotency_key="d" * 64,
        memory_id=MEMORY_ID,
        memory_type=MemoryType.EPISODE,
        scope=MemoryScope(scope_type=MemoryScopeType.REPOSITORY, scope_id=HASH),
        title="Accepted coding task",
        content=episode(),
        confidence=0.9,
        salience=0.5,
        sensitivity=MemorySensitivity.INTERNAL,
        provenance=provenance(),
        actor=MemoryCreator(
            creator_type=MemoryCreatorType.INGESTION_SERVICE,
            creator_id="trajectory-ingestion",
        ),
    )
    assert request.canonical_hash() == request.canonical_hash()

    with pytest.raises(ValidationError, match="memory type must match"):
        MemoryWriteRequest.model_validate(
            {**request.model_dump(mode="json"), "memory_type": "observation"}
        )


def test_provider_cannot_self_authorize_verified_memory() -> None:
    with pytest.raises(ValidationError, match="cannot self-authorize"):
        MemoryWriteRequest(
            request_id=UUID("00000000-0000-0000-0000-000000000905"),
            idempotency_key="e" * 64,
            memory_id=MEMORY_ID,
            memory_type=MemoryType.EPISODE,
            scope=MemoryScope(scope_type=MemoryScopeType.TASK, scope_id=str(TASK_RUN_ID)),
            title="Untrusted provider memory",
            content=episode(),
            status=MemoryStatus.VERIFIED,
            confidence=1.0,
            salience=1.0,
            sensitivity=MemorySensitivity.PUBLIC,
            provenance=provenance(),
            actor=MemoryCreator(creator_type=MemoryCreatorType.PROVIDER, creator_id="model"),
        )


def test_retrieval_mode_is_explicit_and_has_no_hybrid_value() -> None:
    assert "hybrid" not in {item.value for item in MemoryRetrievalMode}
    query = MemoryQuery(
        query_id=UUID("00000000-0000-0000-0000-000000000906"),
        mode=MemoryRetrievalMode.METADATA,
    )
    with pytest.raises(ValidationError, match="accepts no text"):
        MemoryQuery.model_validate(
            {
                **query.model_dump(mode="json"),
                "text": {"text": "unexpected"},
            }
        )


def test_revision_hash_covers_governance_metadata() -> None:
    common = {
        "memory_id": MEMORY_ID,
        "revision": 1,
        "content": episode(),
        "status": MemoryStatus.CANDIDATE,
        "confidence": 0.5,
        "salience": 0.5,
        "sensitivity": MemorySensitivity.INTERNAL,
    }
    first = memory_revision_hash(**common)
    changed = memory_revision_hash(**{**common, "salience": 0.6})
    assert first != changed


def test_provenance_rejects_duplicate_and_self_reference() -> None:
    source = provenance().sources[0]
    with pytest.raises(ValidationError, match="unique"):
        MemoryProvenanceBundle(sources=(source, source))
    self_source = MemoryProvenanceBundle(
        sources=(
            MemorySourceRef(
                identity=MemorySourceIdentity(
                    source_type=MemorySourceType.MEMORY_REVISION,
                    memory_id=MEMORY_ID,
                    revision=1,
                ),
                source_hash=HASH,
            ),
        )
    )
    with pytest.raises(ValueError, match="cannot reference itself"):
        self_source.assert_no_cycle(MEMORY_ID, 1)


def test_transition_reason_is_typed() -> None:
    assert MemoryTransitionReason.CREATED.value == "created"
    with pytest.raises(ValueError):
        MemoryTransitionReason("provider_said_so")
