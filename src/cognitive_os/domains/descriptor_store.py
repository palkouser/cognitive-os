"""Storage without a schema: domain descriptors as events over content-addressed bytes.

Sprint 22A's exit forbids a storage-schema change, so a domain registration may not have a
table of its own. It does not need one. The released spine already has both halves:

*The bytes* are a content-addressed artifact, exactly as every Sprint 21 sealed object was —
the package as it arrived, not a re-serialisation of what we parsed out of it, so what is
replayed later is what was actually accepted.

*The index* is the event store. One `domain.descriptor_registered` event per registration
names the artifact holding its package, so a rebuild has everything it needs: read the
registry stream in order, follow each event to its artifact, load the bytes back.

**The bytes are written before the event that names them.** A registration is two writes to
two stores and nothing makes them atomic, so the only choice is which half a crash may
strand. Bytes-first strands an orphan blob, which is inert and which the released store
already knows how to find; event-first would strand a registration whose package never
arrived, and since a rebuild must refuse what it cannot verify, that single stranded write
would take every other domain down with it at startup (Sprint 22A W1-F2).

**What makes a rebuild safe to trust is that it can refuse.** The event records two hashes —
the package bytes and the descriptor those bytes mean — and the rebuild recomputes both. A
descriptor whose stored bytes no longer reproduce the hash its registration recorded is a
refusal, not a load. Content-addressed storage makes silent corruption unlikely; it does not
make it impossible, and "unlikely" is not a property a registry should rest a domain on.

Three refusals live here, and the third is the one Sprint 22A's W0 left as an advisory:

- **re-registration** of an existing (`domain_id`, `revision`) is refused rather than
  replacing it — D7's W1-F2, where a duplicate key silently replaced its predecessor;
- **a tampered or truncated package** is refused at rebuild, naming the domain;
- **impersonation of a released domain id** is refused *here*, at registration, because this
  is the layer that knows what is registered. `validate_domain_package` deliberately does not:
  it parses bytes into a contract and has no business holding that list (Sprint 22A W0-A1).
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID

from cognitive_os.application.ports.artifact_store import ArtifactStorePort
from cognitive_os.application.ports.event_store import EventStorePort
from cognitive_os.domain.common import ActorRef, utc_now
from cognitive_os.domain.descriptors import (
    RELEASED_DOMAIN_IDS,
    DomainDescriptorV1,
    DomainPackageError,
    validate_domain_package,
)
from cognitive_os.domain.enums import ActorType, PrivacyClass, StreamType
from cognitive_os.events.base import create_event_envelope
from cognitive_os.events.domain_events import DomainDescriptorRegistered
from cognitive_os.infrastructure.errors import ArtifactIntegrityError

#: The one stream every domain registration is appended to. A fixed identity rather than a
#: configured one: a registry whose location is a setting can be pointed at an empty stream,
#: and a registry that silently rebuilds from nothing is worse than one that fails.
DOMAIN_REGISTRY_STREAM_ID = UUID("22a00000-0000-4000-8000-000000000001")

#: The media type the package bytes are stored under. Names the contract, not the encoding.
DOMAIN_PACKAGE_MEDIA_TYPE = "application/vnd.cogos.domain-package+json"

SOURCE_COMPONENT = "domain-registry"


class DomainRegistrationError(RuntimeError):
    """A registration or a rebuild was refused. The message names the domain and the reason."""


@dataclass(frozen=True, slots=True)
class DomainRegistration:
    """What one registration bound: the domain, its bytes, and the event that indexes them."""

    domain_id: str
    revision: int
    descriptor_content_hash: str
    package_sha256: str
    artifact_id: UUID
    event_id: UUID
    stream_version: int


@dataclass(frozen=True, slots=True)
class StoredRegistration:
    """A registration as replayed: the payload, plus the event id its artifact points at.

    The event id is not in the payload and must not be — an event that names its own id is a
    record with two answers to the same question. It comes from the envelope, where the
    artifact's foreign key already points.
    """

    event_id: UUID
    payload: DomainDescriptorRegistered


def _package_digest(payload: bytes) -> str:
    return sha256(payload).hexdigest()


async def register_domain_package(
    events: EventStorePort,
    artifacts: ArtifactStorePort,
    package: bytes,
    *,
    actor: str,
    authority: str,
    reason: str,
) -> DomainRegistration:
    """Validate an untrusted package and bind it as a registration, or refuse with a reason.

    The order matters and is not an implementation detail: the package is validated before
    anything is written, the bytes are stored before the event that names them (see the
    module docstring on which half a crash may strand), and the event carries both hashes so
    the rebuild has something to check the bytes against rather than merely somewhere to
    find them.
    """
    descriptor = validate_domain_package(package)

    if descriptor.domain_id in set(RELEASED_DOMAIN_IDS.values()):
        raise DomainRegistrationError(
            f"refusing to register {descriptor.domain_id!r}: it is a released domain, and a "
            "released domain's revisions are a governance path rather than a package upload"
        )

    for stored_registration in await load_registrations(events):
        existing = stored_registration.payload
        if (existing.domain_id, existing.revision) == (descriptor.domain_id, descriptor.revision):
            raise DomainRegistrationError(
                f"refusing to re-register {descriptor.domain_id!r} revision "
                f"{descriptor.revision}: it is already registered at content hash "
                f"{existing.descriptor_content_hash}. A registry that replaces a duplicate key "
                "loses the thing it replaced"
            )

    stored = await artifacts.put_bytes(package, media_type=DOMAIN_PACKAGE_MEDIA_TYPE)
    payload = DomainDescriptorRegistered(
        domain_id=descriptor.domain_id,
        revision=descriptor.revision,
        lifecycle=descriptor.lifecycle.value,
        artifact_id=stored.artifact_id,
        descriptor_content_hash=descriptor.content_hash,
        package_sha256=_package_digest(package),
        actor=actor,
        authority=authority,
        reason=reason,
        occurred_at=utc_now(),
    )
    version = await events.get_stream_version(DOMAIN_REGISTRY_STREAM_ID) or 0
    envelope = create_event_envelope(
        payload=payload,
        stream_id=DOMAIN_REGISTRY_STREAM_ID,
        stream_type=StreamType.SYSTEM,
        stream_version=version + 1,
        correlation_id=DOMAIN_REGISTRY_STREAM_ID,
        causation_event_id=None,
        actor=ActorRef(actor_type=ActorType.SYSTEM, actor_id=actor),
        source_component=SOURCE_COMPONENT,
        privacy_class=PrivacyClass.INTERNAL,
    )
    await events.append((envelope,), expected_version=version)
    return DomainRegistration(
        domain_id=descriptor.domain_id,
        revision=descriptor.revision,
        descriptor_content_hash=descriptor.content_hash,
        package_sha256=payload.package_sha256,
        artifact_id=stored.artifact_id,
        event_id=envelope.event_id,
        stream_version=version + 1,
    )


async def load_registrations(events: EventStorePort) -> tuple[StoredRegistration, ...]:
    """Every registration in the order it was made. Metadata only; no bytes are loaded."""
    stored = await events.read_stream(DOMAIN_REGISTRY_STREAM_ID)
    return tuple(
        StoredRegistration(
            event_id=item.envelope.event_id,
            payload=DomainDescriptorRegistered.model_validate(item.envelope.payload),
        )
        for item in stored
        if item.envelope.event_type == DomainDescriptorRegistered.event_type
    )


async def rebuild_descriptors(
    events: EventStorePort, artifacts: ArtifactStorePort
) -> tuple[DomainDescriptorV1, ...]:
    """Rebuild the registered descriptors from stored bytes, refusing anything that moved.

    This is the startup path, and it is deliberately the strict one: every package is read
    back, re-validated through the same fail-closed boundary an untrusted package meets, and
    checked against **both** hashes its registration recorded. A rebuild that trusted the
    event's metadata and skipped the bytes would prove only that a registration once
    happened — which is the failure D7's W3-F1 named in another form: a digest recomputed
    unchanged proves the bytes did not move, not that anything can use them.
    """
    descriptors: list[DomainDescriptorV1] = []
    for stored_registration in await load_registrations(events):
        registration = stored_registration.payload
        try:
            package = await artifacts.get_bytes(registration.artifact_id)
        except ArtifactIntegrityError as error:
            # W1-F1. The content-addressed filesystem verifies on read and refuses first, so
            # this branch is where a tampered package is actually caught. It is translated
            # rather than propagated: the released error names a storage key, and an operator
            # reading a startup refusal needs to know *which domain* will not load.
            raise DomainRegistrationError(
                f"refusing {registration.domain_id!r} revision {registration.revision}: its "
                f"stored package failed the artifact store's integrity check, so the bytes on "
                f"disk are not the bytes that were registered ({error})"
            ) from error
        actual_package_hash = _package_digest(package)
        if actual_package_hash != registration.package_sha256:
            # Reached when the bytes are intact but the *index* is wrong — a registration
            # event pointing at an artifact that is not the package it recorded. The blob
            # check above cannot see that: each blob is individually valid.
            raise DomainRegistrationError(
                f"refusing {registration.domain_id!r} revision {registration.revision}: the "
                f"artifact its registration indexes hashes to {actual_package_hash}, but the "
                f"registration recorded {registration.package_sha256}"
            )
        try:
            descriptor = validate_domain_package(package)
        except DomainPackageError as error:
            raise DomainRegistrationError(
                f"refusing {registration.domain_id!r} revision {registration.revision}: the "
                f"stored package no longer validates: {error}"
            ) from error
        if descriptor.content_hash != registration.descriptor_content_hash:
            raise DomainRegistrationError(
                f"refusing {registration.domain_id!r} revision {registration.revision}: the "
                f"stored package means a descriptor with content hash "
                f"{descriptor.content_hash}, but its registration recorded "
                f"{registration.descriptor_content_hash}"
            )
        if (descriptor.domain_id, descriptor.revision) != (
            registration.domain_id,
            registration.revision,
        ):
            raise DomainRegistrationError(
                f"refusing {registration.domain_id!r} revision {registration.revision}: the "
                f"stored package identifies itself as {descriptor.domain_id!r} revision "
                f"{descriptor.revision}"
            )
        descriptors.append(descriptor)
    return tuple(descriptors)

    return tuple(descriptors)
