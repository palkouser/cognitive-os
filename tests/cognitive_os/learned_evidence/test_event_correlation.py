"""S21C1-014: learned evidence correlated with the one Event Store that already exists.

The properties under test are the ones that decide whether the audit stream can be
trusted without becoming a second authority: the stream a subject lands on is
deterministic, a retry does not duplicate, a gap is reportable, and an unhealthy Event
Store cannot invalidate a learned write that already committed.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID, uuid4

import pytest

from cognitive_os.application.services.learned_evidence import (
    EVIDENCE_EVENT_TYPES,
    STATE_EVENT_TYPES,
    LearnedEvidenceService,
)
from cognitive_os.domain.learned import LearnedComponentState
from cognitive_os.domain.learned_evidence import LearnedEvidenceKind
from cognitive_os.events.base import EventEnvelope
from cognitive_os.events.catalog import build_default_event_catalog
from cognitive_os.events.learned_event_service import LearnedEventService, learned_stream_id
from cognitive_os.events.learned_events import (
    LEARNED_EVENT_MODELS,
    LearnedComponentRegistered,
    LearnedObservationRecorded,
)
from cognitive_os.events.memory_store import MemoryEventStore
from cognitive_os.events.storage import AppendResult, StoredEvent
from cognitive_os.infrastructure.learned.memory_repository import (
    InMemoryLearnedEvidenceRepository,
)

from . import fixtures as fx

CORRELATION = uuid4()


def registered_payload(**overrides: object) -> LearnedComponentRegistered:
    fields: dict[str, object] = {
        "component_id": fx.INERT.component_id,
        "surface": fx.surface(),
        "content_hash": fx.ARTIFACT_HASH,
        "actor": "release-operator",
        "authority": "operator",
        "reason": "register the inert fixture",
        "occurred_at": fx.FIXTURE_NOW,
    }
    fields.update(overrides)
    return LearnedComponentRegistered(**fields)  # type: ignore[arg-type]


class BrokenEventStore:
    """An Event Store that always refuses. Nothing else about it matters."""

    async def append(
        self, events: Sequence[EventEnvelope], *, expected_version: int
    ) -> AppendResult:
        raise RuntimeError("the event store is unavailable")

    async def read_stream(
        self,
        stream_id: UUID,
        *,
        from_version: int = 1,
        to_version: int | None = None,
        limit: int | None = None,
    ) -> tuple[StoredEvent, ...]:
        return ()

    async def read_all(
        self, *, after_global_position: int = 0, limit: int = 100
    ) -> tuple[StoredEvent, ...]:
        return ()

    async def get_event(self, event_id: UUID) -> StoredEvent | None:
        return None

    async def get_stream_version(self, stream_id: UUID) -> int | None:
        return None

    async def get_stream_type(self, stream_id: UUID) -> None:
        return None


class TestStreamsAreDeterministic:
    def test_the_same_subject_always_lands_on_the_same_stream(self) -> None:
        assert learned_stream_id("a-component") == learned_stream_id("a-component")

    def test_different_subjects_land_on_different_streams(self) -> None:
        assert learned_stream_id("a-component") != learned_stream_id("b-component")


class TestRetryIsIdempotent:
    @pytest.mark.asyncio
    async def test_appending_the_same_record_twice_stores_one_event(self) -> None:
        service = LearnedEventService(MemoryEventStore())
        payload = registered_payload()
        first = await service.append("subject", payload, correlation_id=CORRELATION)
        second = await service.append("subject", payload, correlation_id=CORRELATION)
        assert first.appended and not second.appended
        assert first.event_id == second.event_id
        assert len(await service.replay("subject")) == 1

    @pytest.mark.asyncio
    async def test_a_different_record_of_the_same_type_is_a_separate_event(self) -> None:
        service = LearnedEventService(MemoryEventStore())
        await service.append("subject", registered_payload(), correlation_id=CORRELATION)
        await service.append(
            "subject",
            registered_payload(content_hash="b" * 64, reason="a later revision"),
            correlation_id=CORRELATION,
        )
        assert len(await service.replay("subject")) == 2

    @pytest.mark.asyncio
    async def test_replay_returns_events_in_append_order(self) -> None:
        service = LearnedEventService(MemoryEventStore())
        hashes = ["a" * 64, "b" * 64, "c" * 64]
        for digest in hashes:
            await service.append(
                "subject", registered_payload(content_hash=digest), correlation_id=CORRELATION
            )
        replayed = await service.replay("subject")
        assert [item.content_hash for item in replayed] == hashes  # type: ignore[attr-defined]


class TestGapsAreNamedNotCounted:
    @pytest.mark.asyncio
    async def test_an_empty_stream_is_reported_as_holding_no_such_event(self) -> None:
        service = LearnedEventService(MemoryEventStore())
        gaps = await service.correlation_gaps(
            (("subject", "learned.component_registered", fx.ARTIFACT_HASH),)
        )
        assert len(gaps) == 1
        assert "holds no learned.component_registered event at all" in gaps[0].detail

    @pytest.mark.asyncio
    async def test_a_wrong_content_hash_is_distinguished_from_an_absent_event(self) -> None:
        """The two need different remedies, so they cannot share one message."""
        service = LearnedEventService(MemoryEventStore())
        await service.append("subject", registered_payload(), correlation_id=CORRELATION)
        gaps = await service.correlation_gaps(
            (("subject", "learned.component_registered", "9" * 64),)
        )
        assert len(gaps) == 1
        assert "carries this content hash" in gaps[0].detail

    @pytest.mark.asyncio
    async def test_a_present_event_produces_no_gap(self) -> None:
        service = LearnedEventService(MemoryEventStore())
        payload = registered_payload()
        await service.append("subject", payload, correlation_id=CORRELATION)
        assert (
            await service.correlation_gaps((("subject", payload.event_type, payload.content_hash),))
            == ()
        )


class TestThePayloadContractIsEnforced:
    @pytest.mark.asyncio
    async def test_an_unregistered_event_type_is_refused(self) -> None:
        class Rogue(LearnedComponentRegistered):
            event_type = "learned.not_in_the_catalogue"

        service = LearnedEventService(MemoryEventStore())
        with pytest.raises(ValueError, match="unregistered learned event type"):
            await service.append(
                "subject",
                Rogue(**registered_payload().model_dump()),
                correlation_id=CORRELATION,
            )

    def test_an_observation_event_needs_no_placeholder_component_id(self) -> None:
        """A fabricated component ID would be a false fact in the audit stream."""
        payload = LearnedObservationRecorded(
            subject_type="observation",
            subject_id=str(uuid4()),
            surface=fx.surface(),
            content_hash=fx.ARTIFACT_HASH,
            actor="intake",
            authority="system",
            reason="accepted a governed outcome",
            occurred_at=fx.FIXTURE_NOW,
        )
        assert payload.component_id is None

    def test_every_new_learned_event_is_in_the_catalogue(self) -> None:
        catalog = build_default_event_catalog()
        for model in LEARNED_EVENT_MODELS:
            assert catalog.get_payload_model(model.event_type, model.schema_version) is model

    def test_every_evidence_kind_maps_to_an_existing_event_type(self) -> None:
        registered = {model.event_type for model in LEARNED_EVENT_MODELS}
        assert set(EVIDENCE_EVENT_TYPES) == set(LearnedEvidenceKind)
        assert {model.event_type for model in EVIDENCE_EVENT_TYPES.values()} <= registered

    def test_the_states_without_an_exact_event_are_left_uncorrelated(self) -> None:
        """Silence is declared, so health can tell it apart from an unexplained gap."""
        assert set(STATE_EVENT_TYPES) == {
            LearnedComponentState.REGISTERED,
            LearnedComponentState.ACTIVE,
            LearnedComponentState.DISABLED,
            LearnedComponentState.RETRACTED,
        }


class TestAnUnhealthyEventStoreCannotUndoALearnedWrite:
    @pytest.mark.asyncio
    async def test_the_learned_write_commits_and_the_failure_is_observable(self) -> None:
        repository = InMemoryLearnedEvidenceRepository()
        service = LearnedEvidenceService(
            repository,
            events=LearnedEventService(BrokenEventStore()),
            clock=lambda: fx.FIXTURE_NOW,
        )
        record = await service.register_component(
            fx.descriptor(),
            actor="release-operator",
            authority="operator",
            reason="register while the event store is down",
            idempotency_key="register-inert",
            correlation_id=CORRELATION,
        )
        assert record.revision == 1

        row = await service.get_component(fx.INERT.component_id)
        assert row is not None, "the learned ledger is the authority, not the event stream"

        failures = service.correlation_failures
        assert len(failures) == 1
        assert failures[0].expected_event_type == "learned.component_registered"
        assert "the event store is unavailable" in failures[0].detail

    @pytest.mark.asyncio
    async def test_replay_still_agrees_when_correlation_is_unhealthy(self) -> None:
        """A correlation gap is a warning; a projection that disagrees is a failure."""
        repository = InMemoryLearnedEvidenceRepository()
        service = LearnedEvidenceService(
            repository,
            events=LearnedEventService(BrokenEventStore()),
            clock=lambda: fx.FIXTURE_NOW,
        )
        await service.register_component(
            fx.descriptor(),
            actor="release-operator",
            authority="operator",
            reason="register while the event store is down",
            idempotency_key="register-inert",
            correlation_id=CORRELATION,
        )
        result = await service.replay()
        assert result.projection_matches and result.failures == ()
        assert service.correlation_failures
