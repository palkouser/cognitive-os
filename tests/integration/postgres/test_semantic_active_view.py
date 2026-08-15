"""Sprint 22C W2-F2. A retired claim leaves the active view, and both stores agree.

The defect this pins was invisible to the whole suite, because the whole suite runs against
the in-memory repository and the defect existed only in PostgreSQL. `query_claims` filtered
on belief status inside the same `SELECT` that picked the current revision, so the database
threw away the superseded revision and returned the newest one that survived the filter —
the last revision the claim held *before* it was retired. A superseded claim therefore stayed
in the active view wearing its old belief, and a retracted one did too.

Sprint 22C's cycle 1 found it the only way it could be found: by superseding a real acquired
claim on the campaign store and watching the successor be refused promotion, because the
predecessor it had just replaced went on contradicting it.

Every test here is written twice, once per repository, and the two are asserted to agree.
A parity assertion is the part that would have caught this: either implementation alone looks
reasonable, and only the pair shows that one of them is wrong.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest

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
    claim_revision_hash,
)
from cognitive_os.infrastructure.semantic_memory.postgres.repository import (
    PostgresSemanticMemoryRepository,
)
from cognitive_os.semantic_memory.beliefs import aggregate_confidence
from cognitive_os.semantic_memory.repository import InMemorySemanticMemoryRepository

CLAIM_ID = UUID("00000000-0000-0000-0000-000000002001")
CREATED = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)
RETIRED = datetime(2026, 8, 15, 13, 0, tzinfo=UTC)
ACTOR = SemanticActor(actor_type=SemanticActorType.OPERATOR, actor_id="s22c-w2")
SCOPE = MemoryScope(scope_type=MemoryScopeType.DOMAIN, scope_id="engineering.mechanics")
SUBJECT = "mechanics:ch2-worked-example"
PREDICATE = "domain.worked_example"


def revision(
    number: int,
    value: str,
    status: BeliefStatus,
    *,
    valid_to: datetime | None = None,
) -> ClaimRevision:
    literal = SemanticLiteral(literal_kind=SemanticLiteralKind.STRING, value=value, unit=None)
    # A supported revision must carry every confidence dimension, so the whole ladder is built
    # from the full set rather than switching shape at the rung that happens to need it.
    confidence = aggregate_confidence(
        extraction=0.9,
        source=0.9,
        grounding=0.9,
        evidence=0.9,
        verification=0.9,
        consistency=0.9,
    )
    interval = ClaimTemporalInterval(valid_from=CREATED, valid_to=valid_to)
    statement = f"worked example {value}"
    reason = "sprint-22c-w2"
    return ClaimRevision(
        claim_id=CLAIM_ID,
        revision=number,
        previous_revision=None if number == 1 else number - 1,
        object=literal,
        statement=statement,
        belief_status=status,
        confidence=confidence,
        valid_interval=interval,
        reason=reason,
        recorded_at=CREATED if number == 1 else RETIRED,
        created_by=ACTOR,
        evidence_snapshot_hash="c" * 64,
        content_hash=claim_revision_hash(
            claim_id=CLAIM_ID,
            revision=number,
            object_value=literal,
            statement=statement,
            belief_status=status,
            confidence=confidence,
            valid_interval=interval,
            reason=reason,
            evidence_snapshot_hash="c" * 64,
        ),
    )


def a_claim() -> Claim:
    return Claim(
        identity=ClaimIdentity(
            claim_id=CLAIM_ID,
            scope=SCOPE,
            canonical_subject_key=SUBJECT,
            predicate_id=PREDICATE,
        ),
        current_revision=1,
        current_belief_status=BeliefStatus.PROPOSED,
        sensitivity=MemorySensitivity.INTERNAL,
        created_at=CREATED,
        created_by=ACTOR,
        idempotency_key="d" * 64,
    )


def an_active_view_query(number: int) -> TemporalClaimQuery:
    """The released default: `belief_statuses` already excludes superseded and retracted."""
    return TemporalClaimQuery(
        query_id=UUID(int=number),
        scopes=(SCOPE,),
        subject_key=SUBJECT,
        predicate_id=PREDICATE,
    )


async def _retire(repository: Any, final: BeliefStatus) -> list[tuple[int, str]]:
    """Create, support, retire — then ask the store what it believes about the subject."""
    await repository.create_claim(a_claim(), revision(1, "as extracted", BeliefStatus.PROPOSED))
    await repository.append_claim_revision(
        revision(2, "as extracted", BeliefStatus.SUPPORTED), expected_revision=1
    )
    await repository.append_claim_revision(
        revision(3, "as extracted", final, valid_to=RETIRED), expected_revision=2
    )
    result = await repository.query_claims(an_active_view_query(2002))
    return [(item.revision, item.belief_status.value) for item in result.claims]


@pytest.mark.asyncio
@pytest.mark.parametrize("final", [BeliefStatus.SUPERSEDED, BeliefStatus.RETRACTED])
async def test_a_retired_claim_leaves_the_postgres_active_view(engines, final) -> None:
    app, _admin = engines
    assert await _retire(PostgresSemanticMemoryRepository(app), final) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("final", [BeliefStatus.SUPERSEDED, BeliefStatus.RETRACTED])
async def test_a_retired_claim_leaves_the_in_memory_active_view(final) -> None:
    assert await _retire(InMemorySemanticMemoryRepository(), final) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("final", [BeliefStatus.SUPERSEDED, BeliefStatus.RETRACTED])
async def test_the_two_stores_answer_the_active_view_identically(engines, final) -> None:
    """The assertion that would have caught it. Either store alone looks reasonable."""
    app, _admin = engines
    assert await _retire(PostgresSemanticMemoryRepository(app), final) == await _retire(
        InMemorySemanticMemoryRepository(), final
    )


@pytest.mark.asyncio
async def test_the_history_of_a_retired_claim_is_still_loadable(engines) -> None:
    """Leaving the active view is not deletion: §2.2e's other half, on the store itself."""
    app, _admin = engines
    repository = PostgresSemanticMemoryRepository(app)
    await _retire(repository, BeliefStatus.SUPERSEDED)

    history = await repository.list_claim_history(CLAIM_ID)
    assert [item.revision for item in history] == [1, 2, 3]
    assert [item.belief_status.value for item in history] == [
        "proposed",
        "supported",
        "superseded",
    ]
    claim = await repository.get_claim(CLAIM_ID)
    assert claim is not None
    assert claim.current_belief_status is BeliefStatus.SUPERSEDED


@pytest.mark.asyncio
async def test_a_believed_claim_is_still_returned(engines) -> None:
    """The repair must not empty the active view of claims that *are* believed."""
    app, _admin = engines
    repository = PostgresSemanticMemoryRepository(app)
    await repository.create_claim(a_claim(), revision(1, "as extracted", BeliefStatus.PROPOSED))
    await repository.append_claim_revision(
        revision(2, "as extracted", BeliefStatus.SUPPORTED), expected_revision=1
    )

    result = await repository.query_claims(an_active_view_query(2003))
    assert [(item.revision, item.belief_status.value) for item in result.claims] == [
        (2, "supported")
    ]
