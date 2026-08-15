"""22B W3-F1, repaired: the governed create asks the stream, not the record.

The defect and its repair are both about *which question decides the append*.

`MemoryService.create` used to append `memory.item_created` when `get_current` had returned
`None` immediately before the write — "was this memory new a moment ago?". A crash between
the record's transaction and the event's leaves a row with an empty stream, and on the resume
that re-runs the crashed range the idempotency key makes that question answer "not new". The
append is skipped, and skipped again on every later resume: the orphan is permanent, and the
recovery procedure is what makes it so.

The repair asks the stream instead — "does this record have its creation event?" — so the
same resume repairs. These tests pin both halves: that the new question repairs, and that the
old question would not have, asserted over the ports rather than against a copy of the old
service kept alive to be wrong at.

The postgres-side proof is `scripts/repairs_22c.py --orphan-repair` and the crash
reproduction beside it; these run with no database so the behaviour is pinned in CI.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from cognitive_os.application.services.memory_service import MemoryService
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
    MemoryWritePolicy,
    MemoryWriteRequest,
    ObservationMemoryContent,
    memory_revision_hash,
)
from cognitive_os.events.memory_event_service import MemoryEventService
from cognitive_os.events.memory_store import MemoryEventStore
from cognitive_os.memory.repository import InMemoryMemoryRepository

MEMORY_ID = UUID("00000000-0000-0000-0000-0000000009f1")
REQUEST_ID = UUID("00000000-0000-0000-0000-0000000009f2")
SOURCE_ID = UUID("00000000-0000-0000-0000-0000000009f3")
HASH = "e" * 64


def _request(memory_id: UUID = MEMORY_ID, *, key: str = "f" * 64) -> MemoryWriteRequest:
    return MemoryWriteRequest(
        request_id=REQUEST_ID,
        memory_id=memory_id,
        idempotency_key=key,
        memory_type=MemoryType.OBSERVATION,
        scope=MemoryScope(scope_type=MemoryScopeType.PROJECT, scope_id="scope-00"),
        title="Governed ingest item",
        content=ObservationMemoryContent(
            observation="a governed write that a crash may interrupt",
            evidence_summary="The record and its event are two transactions.",
        ),
        confidence=0.5,
        salience=0.5,
        sensitivity=MemorySensitivity.INTERNAL,
        actor=MemoryCreator(
            creator_type=MemoryCreatorType.INGESTION_SERVICE, creator_id="repair-test"
        ),
        provenance=MemoryProvenanceBundle(
            sources=(
                MemorySourceRef(
                    identity=MemorySourceIdentity(
                        source_type=MemorySourceType.TASK_RUN, source_id=SOURCE_ID
                    ),
                    source_hash=HASH,
                ),
            )
        ),
    )


def _policy() -> MemoryWritePolicy:
    return MemoryWritePolicy(
        allowed_types=frozenset(MemoryType),
        allowed_scopes=frozenset(MemoryScopeType),
        maximum_sensitivity=MemorySensitivity.INTERNAL,
    )


def _service(repository: InMemoryMemoryRepository, store: MemoryEventStore) -> MemoryService:
    return MemoryService(
        repository,
        _policy(),
        event_service=MemoryEventService(store),
    )


def _creation_events(store: MemoryEventStore, memory_id: UUID) -> int:
    return len(
        [
            item
            for item in store._events  # the store exposes no filter by event type
            if item.envelope.stream_id == memory_id
            and item.envelope.event_type == "memory.item_created"
        ]
    )


@pytest.mark.asyncio
async def test_an_ordinary_create_appends_exactly_one_creation_event() -> None:
    repository, store = InMemoryMemoryRepository(), MemoryEventStore()
    await _service(repository, store).create(_request())
    assert _creation_events(store, MEMORY_ID) == 1


@pytest.mark.asyncio
async def test_the_resume_repairs_the_orphan_a_crash_leaves() -> None:
    """The crash state, written the way a crash writes it: the record, and no event."""
    repository, store = InMemoryMemoryRepository(), MemoryEventStore()
    await repository.create_memory(_request())
    assert _creation_events(store, MEMORY_ID) == 0

    await _service(repository, store).create(_request())
    assert _creation_events(store, MEMORY_ID) == 1


@pytest.mark.asyncio
async def test_the_released_decision_would_not_have_repaired_it() -> None:
    """The counterfactual, pinned where it can be asserted instead of narrated.

    The released code appended when `get_current` returned `None` before the write. After a
    crash the record is there, so that question answers "not new" and the append never runs —
    no matter how many times the range is resumed.
    """
    repository, store = InMemoryMemoryRepository(), MemoryEventStore()
    await repository.create_memory(_request())

    released_decision_to_append = await repository.get_current(MEMORY_ID) is None
    assert released_decision_to_append is False
    assert _creation_events(store, MEMORY_ID) == 0

    # The repaired decision, on the same state, answers the other way.
    assert await store.get_stream_version(MEMORY_ID) is None
    await _service(repository, store).create(_request())
    assert _creation_events(store, MEMORY_ID) == 1


@pytest.mark.asyncio
async def test_repeated_resumes_do_not_append_a_second_creation_event() -> None:
    """A repair that traded an orphan for a duplicate would be the worse defect."""
    repository, store = InMemoryMemoryRepository(), MemoryEventStore()
    service = _service(repository, store)
    for _ in range(4):
        await service.create(_request())
    assert _creation_events(store, MEMORY_ID) == 1


@pytest.mark.asyncio
async def test_the_creation_event_carries_revision_one_however_late_the_repair() -> None:
    """An event announcing a creation must not carry a revision the creation did not have."""
    repository, store = InMemoryMemoryRepository(), MemoryEventStore()
    request = _request()
    record, first = await repository.create_memory(request)

    later = first.model_copy(
        update={
            "revision": 2,
            "previous_revision": 1,
            "content_hash": memory_revision_hash(
                memory_id=record.memory_id,
                revision=2,
                content=first.content,
                status=first.status,
                confidence=first.confidence,
                salience=first.salience,
                sensitivity=first.sensitivity,
            ),
        }
    )
    await repository.append_revision(later, request.provenance, expected_revision=1)

    await _service(repository, store).create(request)
    created = next(
        item.envelope for item in store._events if item.envelope.stream_id == record.memory_id
    )
    assert created.payload["revision"]["revision"] == 1


@pytest.mark.asyncio
async def test_a_service_without_an_event_service_still_creates() -> None:
    """The event stream is optional wiring; the repair must not make it mandatory."""
    repository = InMemoryMemoryRepository()
    service = MemoryService(repository, _policy())
    _, created = await service.create(_request())
    assert created is not None
    assert created[0].memory_id == MEMORY_ID


@pytest.mark.asyncio
async def test_a_dry_run_writes_neither_a_record_nor_an_event() -> None:
    repository, store = InMemoryMemoryRepository(), MemoryEventStore()
    decision, created = await _service(repository, store).create(_request(), dry_run=True)
    assert created is None
    assert decision is not None
    assert await repository.get_current(MEMORY_ID) is None
    assert _creation_events(store, MEMORY_ID) == 0


@pytest.mark.asyncio
async def test_an_idempotent_recreate_under_a_new_memory_id_streams_the_record_it_returned() -> (
    None
):
    """The stream id follows the record the create returned, not the request that asked.

    The released code appended to `request.memory_id` while the payload described whatever
    the idempotency key resolved to, so a re-create under a fresh id would have opened a
    stream for a memory that does not exist and left the real one without its event.
    """
    repository, store = InMemoryMemoryRepository(), MemoryEventStore()
    service = _service(repository, store)
    await service.create(_request())

    other = uuid4()
    _, created = await service.create(_request(other))
    assert created is not None
    assert created[0].memory_id == MEMORY_ID
    assert _creation_events(store, MEMORY_ID) == 1
    assert _creation_events(store, other) == 0
