import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from cognitive_os.domain.memory import MemoryScope, MemoryScopeType, MemorySensitivity
from cognitive_os.domain.semantic_memory import (
    BeliefStatus,
    Claim,
    ClaimIdentity,
    ClaimRevision,
    ClaimTemporalInterval,
    SemanticActor,
    SemanticActorType,
    SemanticLiteral,
    SemanticLiteralKind,
    TemporalClaimQuery,
    TemporalQueryMode,
    claim_revision_hash,
)
from cognitive_os.infrastructure.semantic_memory.postgres.repository import (
    PostgresSemanticMemoryRepository,
)
from cognitive_os.semantic_memory.beliefs import aggregate_confidence
from cognitive_os.semantic_memory.errors import SemanticConcurrencyError

CLAIM_ID = UUID("00000000-0000-0000-0000-000000001001")
NOW = datetime(2026, 7, 15, tzinfo=UTC)
FUTURE = datetime(2027, 1, 10, tzinfo=UTC)
ACTOR = SemanticActor(actor_type=SemanticActorType.OPERATOR, actor_id="integration")
SCOPE = MemoryScope(scope_type=MemoryScopeType.PROJECT, scope_id="cognitive-os")


def make_revision(
    number: int,
    value: str,
    valid_from: datetime,
    recorded_at: datetime,
    *,
    claim_id: UUID = CLAIM_ID,
) -> ClaimRevision:
    semantic_value = SemanticLiteral(
        literal_kind=SemanticLiteralKind.VERSION, value=value, unit=None
    )
    confidence = aggregate_confidence(extraction=0.9)
    interval = ClaimTemporalInterval(valid_from=valid_from)
    content_hash = claim_revision_hash(
        claim_id=claim_id,
        revision=number,
        object_value=semantic_value,
        statement=f"Python {value}",
        belief_status=BeliefStatus.PROPOSED,
        confidence=confidence,
        valid_interval=interval,
        reason="integration",
        evidence_snapshot_hash="a" * 64,
    )
    return ClaimRevision(
        claim_id=claim_id,
        revision=number,
        previous_revision=None if number == 1 else number - 1,
        object=semantic_value,
        statement=f"Python {value}",
        belief_status=BeliefStatus.PROPOSED,
        confidence=confidence,
        valid_interval=interval,
        reason="integration",
        recorded_at=recorded_at,
        created_by=ACTOR,
        evidence_snapshot_hash="a" * 64,
        content_hash=content_hash,
    )


@pytest.mark.asyncio
async def test_postgres_semantic_bitemporal_history_and_runtime_grants(engines) -> None:
    app, _admin = engines
    repository = PostgresSemanticMemoryRepository(app)
    claim = Claim(
        identity=ClaimIdentity(
            claim_id=CLAIM_ID,
            scope=SCOPE,
            canonical_subject_key="project:cognitive-os",
            predicate_id="project.python_version",
        ),
        current_revision=1,
        current_belief_status=BeliefStatus.PROPOSED,
        sensitivity=MemorySensitivity.INTERNAL,
        created_at=NOW,
        created_by=ACTOR,
        idempotency_key="b" * 64,
    )
    first = make_revision(1, "3.12", NOW, NOW)
    second = make_revision(2, "3.13", FUTURE, datetime(2027, 1, 11, tzinfo=UTC))
    await repository.create_claim(claim, first)
    await repository.append_claim_revision(second, expected_revision=1)

    result = await repository.query_claims(
        TemporalClaimQuery(
            query_id=UUID(int=1002),
            mode=TemporalQueryMode.BITEMPORAL,
            scopes=(SCOPE,),
            valid_at=datetime(2026, 8, 1, tzinfo=UTC),
            known_at=datetime(2027, 1, 5, tzinfo=UTC),
        )
    )
    assert [(item.revision, item.object.value) for item in result.claims] == [(1, "3.12")]
    assert [item.revision for item in await repository.list_claim_history(CLAIM_ID)] == [1, 2]

    with pytest.raises(DBAPIError):
        async with app.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE cognitive_os.semantic_claim_revisions "
                    "SET statement='rewritten'"
                )
            )


@pytest.mark.asyncio
async def test_postgres_semantic_revision_concurrency_has_one_winner(engines) -> None:
    app, _admin = engines
    repository = PostgresSemanticMemoryRepository(app)
    claim_id = UUID("00000000-0000-0000-0000-000000001010")
    claim = Claim(
        identity=ClaimIdentity(
            claim_id=claim_id,
            scope=SCOPE,
            canonical_subject_key="project:concurrency",
            predicate_id="project.python_version",
        ),
        current_revision=1,
        current_belief_status=BeliefStatus.PROPOSED,
        sensitivity=MemorySensitivity.INTERNAL,
        created_at=NOW,
        created_by=ACTOR,
        idempotency_key="c" * 64,
    )
    await repository.create_claim(
        claim, make_revision(1, "3.12", NOW, NOW, claim_id=claim_id)
    )
    candidates = (
        make_revision(2, "3.13", FUTURE, FUTURE, claim_id=claim_id),
        make_revision(2, "3.14", FUTURE, FUTURE, claim_id=claim_id),
    )
    results = await asyncio.gather(
        *(repository.append_claim_revision(item, expected_revision=1) for item in candidates),
        return_exceptions=True,
    )
    assert sum(isinstance(item, ClaimRevision) for item in results) == 1
    assert sum(isinstance(item, SemanticConcurrencyError) for item in results) == 1
    assert len(await repository.list_claim_history(claim_id)) == 2
