"""Correlate durable learned evidence with the existing Event Store.

One focused service rather than append logic embedded in every learned caller, for the
same reason the corpus, weakness and benchmark planes each have one: the stream choice,
the actor, the privacy class and the retry rule are decisions that must be made once.

Two properties this service is responsible for:

* **Stable replay order.** Every event about a component lands on one deterministic
  stream derived from the component ID, so reading that stream returns the lifecycle in
  the order it happened without sorting by timestamp.
* **Idempotent retry.** A learned write commits before its event is appended. If the
  append fails and the caller retries the whole operation, the same event must not be
  recorded twice. Retry is resolved against the stream that already exists — the event
  type plus the content hash of the learned record — rather than by adding a second
  dedupe store.

The service never decides anything. A failure here is a correlation warning, because the
append-only learned history is still the authority. See ADR 0086.
"""

from __future__ import annotations

from uuid import UUID, uuid5

from pydantic import Field

from cognitive_os.application.ports.event_store import EventStorePort
from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import ActorRef, NonEmptyStr, Sha256Hex
from cognitive_os.domain.enums import ActorType, PrivacyClass, StreamType

from .base import EventPayload, create_event_envelope
from .learned_events import LEARNED_EVENT_MODELS

SOURCE_COMPONENT = "learned-evidence"

#: Namespace for deterministic learned stream IDs. Fixed forever: changing it would
#: split every existing component's history across two streams.
LEARNED_STREAM_NAMESPACE = UUID("6f0c2a3d-4e5b-5f70-9a81-0b2c3d4e5f60")

#: Learned datasets and read-audit records may describe sensitive material by reference.
#: The event carries identity and hashes only, never an example body.
LEARNED_PRIVACY_CLASS = PrivacyClass.INTERNAL


def learned_stream_id(subject: str) -> UUID:
    """The one stream a subject's learned events belong to.

    Deterministic, so a restarted process appends to the same stream, and so an
    integrity query can find a record's correlated events without an index.
    """
    return uuid5(LEARNED_STREAM_NAMESPACE, subject)


class LearnedCorrelation(ImmutableContractModel):
    """What happened when one learned record was correlated with the audit stream."""

    stream_id: UUID
    event_id: UUID
    event_type: NonEmptyStr
    content_hash: Sha256Hex
    stream_version: int = Field(ge=1)
    appended: bool


class LearnedCorrelationGap(ImmutableContractModel):
    """A learned record whose audit event is missing or does not match.

    Warning-level by construction: it names what to reconcile, and never implies the
    learned history is wrong.
    """

    subject: NonEmptyStr
    content_hash: Sha256Hex
    expected_event_type: NonEmptyStr
    detail: NonEmptyStr


class LearnedEventService:
    """Append and query learned audit events. Adds no second event store."""

    def __init__(self, store: EventStorePort) -> None:
        self._store = store
        self._actor = ActorRef(actor_type=ActorType.SYSTEM, actor_id=SOURCE_COMPONENT)
        self._models = {model.event_type: model for model in LEARNED_EVENT_MODELS}

    async def append(
        self,
        subject: str,
        payload: EventPayload,
        *,
        correlation_id: UUID,
        causation_event_id: UUID | None = None,
    ) -> LearnedCorrelation:
        """Append one learned event, or return the existing one on retry.

        Idempotency is by `(event_type, content_hash)` within the subject's stream.
        Two genuinely distinct learned records cannot collide there, because the hash
        covers the whole record including its identifiers and timestamps.
        """
        if payload.event_type not in self._models:
            raise ValueError(f"unregistered learned event type: {payload.event_type}")
        content_hash = self._content_hash(payload)
        stream_id = learned_stream_id(subject)

        existing = await self._find(stream_id, payload.event_type, content_hash)
        if existing is not None:
            return existing

        version = await self._store.get_stream_version(stream_id) or 0
        envelope = create_event_envelope(
            payload=payload,
            stream_id=stream_id,
            stream_type=StreamType.SYSTEM,
            stream_version=version + 1,
            correlation_id=correlation_id,
            causation_event_id=causation_event_id,
            actor=self._actor,
            source_component=SOURCE_COMPONENT,
            privacy_class=LEARNED_PRIVACY_CLASS,
        )
        result = await self._store.append((envelope,), expected_version=version)
        return LearnedCorrelation(
            stream_id=stream_id,
            event_id=result.event_ids[-1],
            event_type=payload.event_type,
            content_hash=content_hash,
            stream_version=result.current_stream_version,
            appended=True,
        )

    async def replay(self, subject: str) -> tuple[EventPayload, ...]:
        """Decoded learned events for a subject, in stream-version order."""
        events = await self._store.read_stream(learned_stream_id(subject))
        return tuple(
            self._models[item.envelope.event_type].model_validate(item.envelope.payload)
            for item in events
            if item.envelope.event_type in self._models
        )

    async def correlation_gaps(
        self, expected: tuple[tuple[str, str, str], ...]
    ) -> tuple[LearnedCorrelationGap, ...]:
        """Which of the expected `(subject, event_type, content_hash)` triples are absent.

        Health calls this to turn "the audit stream lags the learned ledger" into named
        records rather than a count. It reads and compares; it repairs nothing, because
        silently back-filling an audit event would forge the timestamp of a decision.
        """
        gaps: list[LearnedCorrelationGap] = []
        for subject, event_type, content_hash in expected:
            stream_id = learned_stream_id(subject)
            found = await self._find(stream_id, event_type, content_hash)
            if found is not None:
                continue
            present = await self._store.read_stream(stream_id)
            same_type = [item for item in present if item.envelope.event_type == event_type]
            detail = (
                f"no {event_type} event on stream {stream_id} carries this content hash"
                if same_type
                else f"stream {stream_id} holds no {event_type} event at all"
            )
            gaps.append(
                LearnedCorrelationGap(
                    subject=subject,
                    content_hash=content_hash,
                    expected_event_type=event_type,
                    detail=detail,
                )
            )
        return tuple(gaps)

    async def _find(
        self, stream_id: UUID, event_type: str, content_hash: str
    ) -> LearnedCorrelation | None:
        for item in await self._store.read_stream(stream_id):
            envelope = item.envelope
            if envelope.event_type != event_type:
                continue
            if envelope.payload.get("content_hash") != content_hash:
                continue
            return LearnedCorrelation(
                stream_id=stream_id,
                event_id=envelope.event_id,
                event_type=event_type,
                content_hash=content_hash,
                stream_version=envelope.stream_version,
                appended=False,
            )
        return None

    @staticmethod
    def _content_hash(payload: EventPayload) -> str:
        value = getattr(payload, "content_hash", None)
        if not isinstance(value, str) or not value:
            raise ValueError(
                f"{payload.event_type} carries no content hash, so it cannot be "
                "correlated with the learned record it describes"
            )
        return value
