"""S22A-W1: registration, rebuild, and the four refusals that make the rebuild worth trusting.

The vertical slice proved this chain against a real PostgreSQL store and a real process
restart, which is the evidence that matters and is also the evidence CI cannot run. These
tests hold the same properties in-process so that every later wave carries them: what the
slice proved once, the suite keeps proving.

The fakes are deliberately able to lie. An artifact store that cannot corrupt its own bytes
can only demonstrate the happy path, and a rebuild's whole job is what it does when the bytes
disagree with the record.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid4

import pytest

from cognitive_os.domain.common import ArtifactRef
from cognitive_os.domain.descriptors import DomainPackageError
from cognitive_os.domains.descriptor_store import (
    DOMAIN_PACKAGE_MEDIA_TYPE,
    DOMAIN_REGISTRY_STREAM_ID,
    DomainRegistrationError,
    load_registrations,
    rebuild_descriptors,
    register_domain_package,
)
from cognitive_os.events.storage import AppendResult, StoredEvent

FIXTURE_TIME = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)


class FakeArtifactStore:
    """Content-addressed and in-process, with a way to make the bytes lie."""

    def __init__(self) -> None:
        self.data: dict[UUID, bytes] = {}

    async def put_bytes(
        self, data: bytes, *, media_type: str, source_event_id: UUID | None = None
    ) -> ArtifactRef:
        del source_event_id
        artifact_id = uuid4()
        content_hash = sha256(data).hexdigest()
        self.data[artifact_id] = data
        return ArtifactRef(
            artifact_id=artifact_id,
            media_type=media_type,
            content_hash=content_hash,
            size_bytes=len(data),
            storage_key=f"sha256/{content_hash[:2]}/{content_hash}",
            created_at=FIXTURE_TIME,
        )

    async def get_bytes(self, artifact_id: UUID) -> bytes:
        return self.data[artifact_id]

    def replace_bytes(self, artifact_id: UUID, data: bytes) -> None:
        """What a filesystem without verification would hand back after a bad day."""
        self.data[artifact_id] = data


class FakeEventStore:
    """Append-only, version-checked, and nothing else. The stream is a list."""

    def __init__(self) -> None:
        self.events: list[StoredEvent] = []

    async def append(self, envelopes: Sequence[Any], *, expected_version: int) -> AppendResult:
        if expected_version != len(self.events):
            raise RuntimeError("optimistic concurrency violation")
        stored = [
            StoredEvent(
                global_position=len(self.events) + index + 1,
                stored_at=FIXTURE_TIME,
                envelope=envelope,
            )
            for index, envelope in enumerate(envelopes)
        ]
        self.events.extend(stored)
        return AppendResult(
            stream_id=DOMAIN_REGISTRY_STREAM_ID,
            previous_stream_version=expected_version,
            current_stream_version=len(self.events),
            event_ids=tuple(item.envelope.event_id for item in stored),
            global_positions=tuple(item.global_position for item in stored),
            stored_at=FIXTURE_TIME,
        )

    async def read_stream(self, stream_id: UUID, **_: Any) -> tuple[StoredEvent, ...]:
        return tuple(item for item in self.events if item.envelope.stream_id == stream_id)

    async def get_stream_version(self, stream_id: UUID) -> int | None:
        del stream_id
        return len(self.events) or None


def package(domain_id: str = "engineering.mechanics", revision: int = 1, **overrides: Any) -> bytes:
    import json

    payload: dict[str, Any] = {
        "domain_id": domain_id,
        "revision": revision,
        "display_name": "a pilot domain",
        "lifecycle": "pilot",
        "capabilities": {
            "verifier_capabilities": ["physics.dimension"],
            "tool_capabilities": ["physics.kernel"],
        },
        "provenance": {
            "source": "sprint-22a W1 test",
            "revision": "none",
            "licence": "internal",
            "redistributable": False,
        },
    }
    payload.update(overrides)
    return json.dumps(payload, sort_keys=True).encode()


async def _register(events: FakeEventStore, artifacts: FakeArtifactStore, payload: bytes) -> Any:
    return await register_domain_package(
        events,
        artifacts,
        payload,
        actor="sprint-22a-w1",
        authority="sprint-22a pre-registration revision 1",
        reason="test",
    )


@pytest.fixture
def stores() -> tuple[FakeEventStore, FakeArtifactStore]:
    return FakeEventStore(), FakeArtifactStore()


@pytest.mark.asyncio
async def test_a_registered_descriptor_rebuilds_to_the_same_content_hash(
    stores: tuple[FakeEventStore, FakeArtifactStore],
) -> None:
    """The round trip that the whole 'storage without a schema' claim rests on."""
    events, artifacts = stores
    registration = await _register(events, artifacts, package())

    rebuilt = await rebuild_descriptors(events, artifacts)

    assert [item.domain_id for item in rebuilt] == ["engineering.mechanics"]
    assert rebuilt[0].content_hash == registration.descriptor_content_hash


@pytest.mark.asyncio
async def test_the_bytes_are_stored_before_the_event_that_names_them(
    stores: tuple[FakeEventStore, FakeArtifactStore],
) -> None:
    """W1-F2. A crash between the two writes must strand an orphan blob, never a
    registration whose package never arrived — one of those is inert, the other refuses
    every domain at startup."""
    events, artifacts = stores
    registration = await _register(events, artifacts, package())

    assert registration.artifact_id in artifacts.data
    stored = await load_registrations(events)
    assert stored[0].payload.artifact_id == registration.artifact_id


@pytest.mark.asyncio
async def test_re_registering_the_same_domain_and_revision_is_refused(
    stores: tuple[FakeEventStore, FakeArtifactStore],
) -> None:
    """D7's W1-F2 generalised: a duplicate key that replaces its predecessor loses it."""
    events, artifacts = stores
    await _register(events, artifacts, package())

    with pytest.raises(DomainRegistrationError, match="re-register"):
        await _register(events, artifacts, package())

    assert len(await load_registrations(events)) == 1


@pytest.mark.asyncio
async def test_a_new_revision_of_a_registered_pilot_is_accepted(
    stores: tuple[FakeEventStore, FakeArtifactStore],
) -> None:
    """Identity is (domain_id, revision), so a second revision is a second descriptor."""
    events, artifacts = stores
    await _register(events, artifacts, package())
    await _register(events, artifacts, package(revision=2))

    rebuilt = await rebuild_descriptors(events, artifacts)
    assert [item.revision for item in rebuilt] == [1, 2]


@pytest.mark.asyncio
@pytest.mark.parametrize("domain_id", ["mathematics", "physics", "logic", "coding"])
async def test_a_package_impersonating_a_released_domain_is_refused(
    stores: tuple[FakeEventStore, FakeArtifactStore], domain_id: str
) -> None:
    """W0-A1, seated where it belongs: the boundary parses bytes, the registry knows the list."""
    events, artifacts = stores

    with pytest.raises(DomainRegistrationError, match="released domain"):
        await _register(events, artifacts, package(domain_id=domain_id, revision=2))

    assert await load_registrations(events) == ()


@pytest.mark.asyncio
async def test_an_invalid_package_is_refused_before_anything_is_written(
    stores: tuple[FakeEventStore, FakeArtifactStore],
) -> None:
    events, artifacts = stores

    with pytest.raises(DomainPackageError):
        await _register(events, artifacts, b"not a descriptor package")

    assert artifacts.data == {}
    assert events.events == []


@pytest.mark.asyncio
async def test_a_package_claiming_active_is_refused_at_registration(
    stores: tuple[FakeEventStore, FakeArtifactStore],
) -> None:
    """W0-F2 still holds through this path: promotion is not a field a package may set."""
    events, artifacts = stores

    with pytest.raises(DomainPackageError, match="lifecycle"):
        await _register(events, artifacts, package(lifecycle="active"))

    assert events.events == []


@pytest.mark.asyncio
async def test_a_rebuild_refuses_bytes_that_no_longer_mean_what_was_registered(
    stores: tuple[FakeEventStore, FakeArtifactStore],
) -> None:
    """The slice's tamper phase, in process: the package still parses and still claims the
    same domain at the same revision, and is refused anyway because its hash moved."""
    events, artifacts = stores
    registration = await _register(events, artifacts, package())
    artifacts.replace_bytes(
        registration.artifact_id, package(display_name="a pilot domain, quietly edited")
    )

    with pytest.raises(DomainRegistrationError) as refusal:
        await rebuild_descriptors(events, artifacts)

    assert "engineering.mechanics" in str(refusal.value)


@pytest.mark.asyncio
async def test_a_rebuild_refuses_a_registration_pointing_at_the_wrong_artifact(
    stores: tuple[FakeEventStore, FakeArtifactStore],
) -> None:
    """Each blob is individually valid here; it is the *index* that is wrong, which the
    artifact store's own verification cannot see."""
    events, artifacts = stores
    registration = await _register(events, artifacts, package())
    artifacts.replace_bytes(registration.artifact_id, package(domain_id="science.chemistry"))

    with pytest.raises(DomainRegistrationError, match="hashes to"):
        await rebuild_descriptors(events, artifacts)


@pytest.mark.asyncio
async def test_a_rebuild_of_an_empty_registry_is_empty_rather_than_an_error(
    stores: tuple[FakeEventStore, FakeArtifactStore],
) -> None:
    """A system with no registered domains still has its four released ones."""
    events, artifacts = stores
    assert await rebuild_descriptors(events, artifacts) == ()
    assert await load_registrations(events) == ()


@pytest.mark.asyncio
async def test_the_media_type_names_the_contract(
    stores: tuple[FakeEventStore, FakeArtifactStore],
) -> None:
    events, artifacts = stores
    await _register(events, artifacts, package())
    assert DOMAIN_PACKAGE_MEDIA_TYPE == "application/vnd.cogos.domain-package+json"
