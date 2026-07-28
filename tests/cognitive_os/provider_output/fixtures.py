"""Deterministic fixtures for provider-output governance tests.

Every identity is derived from one namespace, so two runs of the same test build the same
record and a hash comparison means something. Nothing here fabricates Artifact Store
metadata: `seed_artifact` writes real bytes through `ArtifactService`, because metadata
without bytes behind it is exactly the drift Sprint 21C1 caught during restore verification.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid5

from cognitive_os.domain.memory import MemorySensitivity
from cognitive_os.domain.provider_output import (
    ProviderAdapterKind,
    ProviderOutputIntendedUse,
    ProviderOutputRecord,
    ProviderOutputRetentionMode,
    ProviderOutputVerifierStatus,
    ProviderRetentionDirective,
    SecretScanStatus,
    UsageRightsDecision,
)

FIXTURE_NAMESPACE = UUID("6f0f0e1a-2b3c-5d4e-8f90-a1b2c3d4e5f6")
FIXTURE_NOW = datetime(2026, 7, 27, 12, 0, 0, tzinfo=UTC)

OUTPUT_ID = uuid5(FIXTURE_NAMESPACE, "provider-output")
REVISION_ONE_ID = uuid5(FIXTURE_NAMESPACE, "provider-output-revision-1")
REVISION_TWO_ID = uuid5(FIXTURE_NAMESPACE, "provider-output-revision-2")
MODEL_CALL_ID = uuid5(FIXTURE_NAMESPACE, "model-call")

#: Public synthetic bytes. Nothing here is repository content or a real provider response.
ARTIFACT_BYTES = b'{"summary":"synthetic advisory result","findings":[]}\n'

HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


def directive(**overrides: Any) -> ProviderRetentionDirective:
    fields: dict[str, Any] = {
        "intended_use": ProviderOutputIntendedUse.TRANSIENT_ADVICE,
        "retention_mode": ProviderOutputRetentionMode.NONE,
        "sensitivity": MemorySensitivity.PUBLIC,
    }
    fields.update(overrides)
    return ProviderRetentionDirective(**fields)


def record(**overrides: Any) -> ProviderOutputRecord:
    """A governed, verified, hash-only revision: the shape most tests want to vary from."""
    fields: dict[str, Any] = {
        "provider_output_revision_id": REVISION_ONE_ID,
        "provider_output_id": OUTPUT_ID,
        "revision": 1,
        "model_call_id": MODEL_CALL_ID,
        "provider_id": "openrouter",
        "adapter_kind": ProviderAdapterKind.OPENROUTER,
        "requested_model": "openrouter/free",
        "resolved_model": "vendor/model:free",
        "request_hash": HASH_A,
        "normalized_response_hash": HASH_B,
        "completed_event_id": uuid5(FIXTURE_NAMESPACE, "completed-event"),
        "parameter_hash": HASH_C,
        "intended_use": ProviderOutputIntendedUse.CORPUS_CANDIDATE,
        "rights_decision": UsageRightsDecision.VERIFIED,
        "rights_evidence_hash": HASH_A,
        "sensitivity": MemorySensitivity.PUBLIC,
        "secret_scan_status": SecretScanStatus.PASSED,
        "secret_scan_evidence_hash": HASH_B,
        "secret_scan_ruleset_version": "2026.07-c2",  # pragma: allowlist secret
        "retention_mode": ProviderOutputRetentionMode.HASH_ONLY,
        "physical_deletion_required": False,
        "verifier_status": ProviderOutputVerifierStatus.PASSED,
        "verifier_identity": "synthetic-fixture-verifier",
        "verifier_evidence_hash": HASH_C,
        "recorded_by": "governed-teacher",
        "recorded_at": FIXTURE_NOW,
        "idempotency_key": "provider-output:fixture",
    }
    fields.update(overrides)
    return ProviderOutputRecord(**fields)


def superseding_record(previous: ProviderOutputRecord, **overrides: Any) -> ProviderOutputRecord:
    """Revision N+1 of the same decision, correctly chained to its predecessor."""
    fields: dict[str, Any] = {
        "provider_output_revision_id": REVISION_TWO_ID,
        "revision": previous.revision + 1,
        "previous_revision_id": previous.provider_output_revision_id,
        "recorded_at": previous.recorded_at + timedelta(minutes=5),
        "idempotency_key": f"{previous.idempotency_key}:r{previous.revision + 1}",
        "supersession_reason": "rights review corrected the decision",
    }
    merged = previous.model_dump()
    merged.pop("content_hash", None)
    merged.update(fields)
    merged.update(overrides)
    return ProviderOutputRecord(**merged)


async def seed_artifact(engine: object, root: object) -> tuple[UUID, str]:
    """Store the fixture bytes through the real Artifact Store and return ID and hash.

    The bytes go to `COGOS_ARTIFACT_ROOT` when it is configured, *not* to the caller's
    temporary directory. Writing metadata into the shared database while the bytes live in
    a directory pytest deletes produces precisely the metadata-without-bytes drift Sprint
    21C1 diagnosed — and the restore verifier walks every artifact row, so it surfaces
    several release steps later as a failed backup check rather than as a failed test.
    """
    import os
    from pathlib import Path

    from cognitive_os.infrastructure.artifacts.filesystem import ContentAddressedFilesystem
    from cognitive_os.infrastructure.artifacts.service import ArtifactService
    from cognitive_os.infrastructure.postgres.artifact_repository import (
        PostgresArtifactRepository,
    )

    configured = os.environ.get("COGOS_ARTIFACT_ROOT")
    destination = Path(configured) if configured else Path(str(root))
    service = ArtifactService(
        ContentAddressedFilesystem(destination),
        PostgresArtifactRepository(engine),  # type: ignore[arg-type]
    )
    reference = await service.put_bytes(ARTIFACT_BYTES, media_type="application/json")
    return reference.artifact_id, reference.content_hash


async def seed_completed_model_call(engine: object, *, model_call_id: UUID) -> UUID:
    """Append a real `model_call.completed` envelope and return its event ID.

    Through `ProviderEventService` rather than a raw INSERT: the governance ledger's foreign
    key points at the Event Store, and a hand-built row would prove the constraint holds
    against a shape the application never produces.
    """
    from uuid import uuid4

    from cognitive_os.domain.model_requests import (
        ModelProviderRequest,
        ModelProviderResponse,
        ProviderMessage,
        ProviderMessageRole,
    )
    from cognitive_os.domain.provider import ModelFinishReason
    from cognitive_os.events.catalog import build_default_event_catalog
    from cognitive_os.events.provider_event_service import ProviderEventService
    from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore

    store = PostgresEventStore(engine, build_default_event_catalog())  # type: ignore[arg-type]
    events = ProviderEventService(store)
    request = ModelProviderRequest(
        model_call_id=model_call_id,
        task_run_id=uuid4(),
        correlation_id=model_call_id,
        requested_model="openrouter/free",
        messages=(ProviderMessage(role=ProviderMessageRole.USER, content="synthetic"),),
    )
    response = ModelProviderResponse(
        model_call_id=model_call_id,
        provider_id="openrouter",
        requested_model=request.requested_model,
        resolved_model="vendor/model:free",
        content="synthetic advisory result",
        finish_reason=ModelFinishReason.COMPLETED,
        latency_ms=1.0,
    )
    await events.requested(request, provider_id="openrouter")
    completed = await events.completed(request, response, started_at=FIXTURE_NOW)
    return completed
