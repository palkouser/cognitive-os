"""The in-process governed-teacher rig the provider benchmark drives.

Everything is in memory: a stub provider that counts its own calls, a `MemoryEventStore`, a
content-addressed dictionary standing in for the Artifact Store, and the in-memory
provider-output repository. That is what keeps the benchmark credential-free, network-free
and binary-free while still running the real `GovernedTeacherService` decision path rather
than a re-implementation of it.

Identities are derived from one fixed namespace, so two runs of the same manifest build the
same records and comparing hashes between runs is meaningful.
"""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid5

from cognitive_os.application.services.governed_teacher import (
    GovernedTeacherService,
    RightsDecision,
    VerifierOutcome,
)
from cognitive_os.application.services.model_execution import ModelExecutionService
from cognitive_os.domain.common import ArtifactRef
from cognitive_os.domain.memory import MemorySensitivity
from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ModelProviderResponse,
    ProviderMessage,
    ProviderMessageRole,
)
from cognitive_os.domain.provider import ModelFinishReason
from cognitive_os.domain.provider_output import (
    ProviderAdapterKind,
    ProviderOutputIntendedUse,
    ProviderOutputRecord,
    ProviderOutputRetentionMode,
    ProviderOutputVerifierStatus,
    SecretScanStatus,
    UsageRightsDecision,
)
from cognitive_os.events.memory_store import MemoryEventStore
from cognitive_os.events.provider_event_service import (
    ProviderArtifactPolicy,
    ProviderArtifactService,
    ProviderEventService,
)
from cognitive_os.infrastructure.learned.memory_provider_output import (
    InMemoryProviderOutputRepository,
)
from cognitive_os.providers.mock import MockProvider
from cognitive_os.providers.redaction import REDACTION_RULESET_VERSION
from cognitive_os.providers.registry import ProviderRegistry

HARNESS_NAMESPACE = UUID("6d3f0b28-91a7-5c44-8f16-2ad5e79c4b60")
FIXTURE_NOW = datetime(2026, 7, 28, tzinfo=UTC)

HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64

CLEAN_CONTENT = "the helper divides by a length that can be zero"
#: Synthetic and obviously fake, but shaped like the thing the scanner must catch.
LEAKY_CONTENT = "the key is sk-or-v1-" + "a" * 32  # pragma: allowlist secret

__all__ = [
    "CLEAN_CONTENT",
    "LEAKY_CONTENT",
    "CountingProvider",
    "RightsDecision",
    "VerifierOutcome",
    "a_governance_record",
    "a_request",
    "build_governed_teacher",
]


class CountingProvider:
    """A provider that records how many times it was actually called.

    The count is the point: "the provider is called exactly once whatever else happens" is a
    property no amount of reading the service can establish.
    """

    def __init__(self, response: ModelProviderResponse) -> None:
        self._inner = MockProvider(outcomes=(response,) * 8)
        self.calls = 0

    @property
    def provider_id(self) -> str:
        return self._inner.provider_id

    @property
    def identity(self) -> Any:
        return self._inner.identity

    @property
    def enabled(self) -> bool:
        return True

    async def complete(self, request: ModelProviderRequest) -> ModelProviderResponse:
        self.calls += 1
        return await self._inner.complete(request)

    def stream(self, request: ModelProviderRequest) -> Any:
        return self._inner.stream(request)

    async def health_check(self) -> Any:
        return await self._inner.health_check()

    async def get_model_capabilities(self, model_id: str) -> Any:
        return await self._inner.get_model_capabilities(model_id)


class MemoryArtifactStore:
    """Content-addressed `put_bytes` and nothing else — the narrowest useful stand-in."""

    def __init__(self) -> None:
        self.blobs: dict[UUID, bytes] = {}

    async def put_bytes(
        self, data: bytes, *, media_type: str, source_event_id: UUID | None = None
    ) -> ArtifactRef:
        del source_event_id
        content_hash = sha256(data).hexdigest()
        artifact_id = uuid5(HARNESS_NAMESPACE, content_hash)
        self.blobs[artifact_id] = data
        return ArtifactRef(
            artifact_id=artifact_id,
            media_type=media_type,
            content_hash=content_hash,
            size_bytes=len(data),
            storage_key=f"sha256/{content_hash[:2]}/{content_hash}",
            created_at=FIXTURE_NOW,
        )


def a_request(suffix: str = "case") -> ModelProviderRequest:
    """A fixed request. Derived identities, so receipts repeat across runs."""
    return ModelProviderRequest(
        model_call_id=uuid5(HARNESS_NAMESPACE, f"model-call:{suffix}"),
        task_run_id=uuid5(HARNESS_NAMESPACE, f"task-run:{suffix}"),
        correlation_id=uuid5(HARNESS_NAMESPACE, f"correlation:{suffix}"),
        requested_model="openrouter/free",
        messages=(ProviderMessage(role=ProviderMessageRole.USER, content="review this"),),
    )


def _a_response(request: ModelProviderRequest, *, content: str) -> ModelProviderResponse:
    return ModelProviderResponse(
        model_call_id=request.model_call_id,
        provider_id="mock",
        requested_model=request.requested_model,
        resolved_model="vendor/free-small",
        content=content,
        structured_output={"summary": content, "findings": []},
        finish_reason=ModelFinishReason.COMPLETED,
        latency_ms=1.0,
    )


def build_governed_teacher(
    *, leaky: bool = False, suffix: str = "case"
) -> tuple[GovernedTeacherService, CountingProvider, InMemoryProviderOutputRepository]:
    """A complete governed path with no durable store behind any part of it."""
    content = LEAKY_CONTENT if leaky else CLEAN_CONTENT
    provider = CountingProvider(_a_response(a_request(suffix), content=content))
    execution = ModelExecutionService(
        ProviderRegistry((provider,)),
        default_provider_id=provider.provider_id,
        event_service=ProviderEventService(MemoryEventStore()),
        artifact_service=ProviderArtifactService(
            MemoryArtifactStore(),  # type: ignore[arg-type]
            policy=ProviderArtifactPolicy.NORMALIZED_ONLY,
        ),
    )
    repository = InMemoryProviderOutputRepository()
    service = GovernedTeacherService(
        execution,
        repository=repository,
        intake=None,
        clock=lambda: FIXTURE_NOW,
    )
    return service, provider, repository


def a_governance_record(**overrides: Any) -> ProviderOutputRecord:
    """A verified, hash-only revision: the shape the selection cases vary from."""
    adapter = overrides.pop("adapter", "openrouter")
    fields: dict[str, Any] = {
        "provider_output_revision_id": uuid5(HARNESS_NAMESPACE, f"revision:{adapter}"),
        "provider_output_id": uuid5(HARNESS_NAMESPACE, f"output:{adapter}"),
        "revision": 1,
        "model_call_id": uuid5(HARNESS_NAMESPACE, f"model-call:{adapter}"),
        "provider_id": adapter,
        "adapter_kind": ProviderAdapterKind(adapter),
        "requested_model": "openrouter/free",
        "resolved_model": "vendor/free-small",
        "request_hash": HASH_A,
        "normalized_response_hash": HASH_B,
        "completed_event_id": uuid5(HARNESS_NAMESPACE, f"completed:{adapter}"),
        "parameter_hash": HASH_C,
        "intended_use": ProviderOutputIntendedUse.CORPUS_CANDIDATE,
        "rights_decision": UsageRightsDecision.VERIFIED,
        "rights_evidence_hash": HASH_A,
        "sensitivity": MemorySensitivity.PUBLIC,
        "secret_scan_status": SecretScanStatus.PASSED,
        "secret_scan_evidence_hash": HASH_B,
        "secret_scan_ruleset_version": REDACTION_RULESET_VERSION,
        "retention_mode": ProviderOutputRetentionMode.HASH_ONLY,
        "physical_deletion_required": False,
        "verifier_status": ProviderOutputVerifierStatus.PASSED,
        "verifier_identity": "synthetic-verifier",
        "verifier_evidence_hash": HASH_C,
        "recorded_by": "provider-benchmark",
        "recorded_at": FIXTURE_NOW,
        "idempotency_key": f"provider-output:benchmark:{adapter}",
    }
    fields.update(overrides)
    return ProviderOutputRecord(**fields)
