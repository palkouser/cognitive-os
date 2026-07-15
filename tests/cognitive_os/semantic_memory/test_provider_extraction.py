from datetime import UTC, datetime
from hashlib import sha256
from typing import cast
from uuid import UUID

import pytest
from pydantic import ValidationError

from cognitive_os.application.ports.artifact_store import ArtifactStorePort
from cognitive_os.application.services.model_execution import ModelExecutionService
from cognitive_os.config.semantic_memory_config import SemanticMemoryConfiguration
from cognitive_os.domain.common import ArtifactRef, JsonValue
from cognitive_os.domain.memory import MemoryScope, MemoryScopeType, MemorySensitivity
from cognitive_os.domain.model_requests import ModelProviderResponse, NormalizedToolCall
from cognitive_os.domain.provider import ModelFinishReason, ResponseFormat, ToolChoiceMode
from cognitive_os.domain.semantic_memory import (
    ClaimProposal,
    ClaimTemporalInterval,
    ExtractionBudget,
    GroundedSourceSpan,
    GroundingMode,
    ObservationProposal,
    SemanticEntityRef,
    SemanticExtractionProposal,
    SemanticExtractionRequest,
    SemanticLiteral,
    SemanticLiteralKind,
    SemanticSourceRef,
    SemanticSourceType,
)
from cognitive_os.events.provider_event_service import ProviderArtifactService
from cognitive_os.providers.mock import MockProvider
from cognitive_os.providers.registry import ProviderRegistry
from cognitive_os.semantic_memory.errors import SemanticPolicyError
from cognitive_os.semantic_memory.predicates import build_default_predicate_registry
from cognitive_os.semantic_memory.provider_extraction import (
    ProviderSemanticExtractionService,
)
from cognitive_os.semantic_memory.repository import InMemorySemanticMemoryRepository
from cognitive_os.semantic_memory.service import SemanticMemoryService

NOW = datetime(2026, 7, 15, tzinfo=UTC)
SCOPE = MemoryScope(scope_type=MemoryScopeType.PROJECT, scope_id="cognitive-os")
SOURCE = SemanticSourceRef(
    source_type=SemanticSourceType.ARTIFACT,
    source_id=UUID(int=1),
    content_hash="a" * 64,
)
SPAN = GroundedSourceSpan(
    source=SOURCE,
    mode=GroundingMode.ARTIFACT_BYTES,
    start=0,
    end=11,
    path=None,
    excerpt_hash=sha256(b"Python 3.12").hexdigest(),
)
BUDGET = ExtractionBudget(
    maximum_observations=1,
    maximum_claims=1,
    maximum_evidence_links=1,
    maximum_relations=0,
)


class ArtifactStore:
    def __init__(self) -> None:
        self.values: list[bytes] = []

    async def put_bytes(
        self,
        data: bytes,
        *,
        media_type: str,
        source_event_id: UUID | None = None,
    ) -> ArtifactRef:
        self.values.append(data)
        return ArtifactRef(
            artifact_id=UUID(int=100 + len(self.values)),
            media_type=media_type,
            content_hash=sha256(data).hexdigest(),
            size_bytes=len(data),
            storage_key=f"provider/{len(self.values)}",
            created_at=NOW,
        )


class SourceResolver:
    async def resolve_span(
        self,
        span: GroundedSourceSpan,
        *,
        scope: MemoryScope | None = None,
        sensitivity: MemorySensitivity | None = None,
    ) -> bytes:
        assert span == SPAN
        assert scope == SCOPE
        assert sensitivity is MemorySensitivity.INTERNAL
        return b"Python 3.12"

    async def validate_span(
        self,
        span: GroundedSourceSpan,
        *,
        scope: MemoryScope | None = None,
        sensitivity: MemorySensitivity | None = None,
    ) -> None:
        await self.resolve_span(span, scope=scope, sensitivity=sensitivity)


def proposal_payload(*, source_span: GroundedSourceSpan = SPAN) -> dict[str, JsonValue]:
    registry = build_default_predicate_registry()
    observation_id = UUID(int=3)
    return SemanticExtractionProposal(
        extraction_id=UUID(int=2),
        registry_snapshot_hash=registry.snapshot_hash(),
        observations=(
            ObservationProposal(
                proposal_id=observation_id,
                content="Python 3.12",
                source_spans=(source_span,),
            ),
        ),
        claims=(
            ClaimProposal(
                proposal_id=UUID(int=4),
                subject=SemanticEntityRef(
                    entity_id="project:cognitive-os",
                    entity_type="project",
                    display_label=None,
                ),
                predicate_id="project.python_version",
                object=SemanticLiteral(
                    literal_kind=SemanticLiteralKind.VERSION,
                    value="3.12",
                    unit=None,
                ),
                valid_interval=ClaimTemporalInterval(valid_from=NOW),
                observation_proposal_ids=(observation_id,),
            ),
        ),
        budget=BUDGET,
    ).model_dump(mode="json")


def extraction_request() -> SemanticExtractionRequest:
    registry = build_default_predicate_registry()
    return SemanticExtractionRequest(
        request_id=UUID(int=2),
        source_spans=(SPAN,),
        registry_snapshot_hash=registry.snapshot_hash(),
        scope=SCOPE,
        sensitivity_ceiling=MemorySensitivity.INTERNAL,
        budget=BUDGET,
        required_output_schema=ProviderSemanticExtractionService.required_schema(),
        requested_at=NOW,
    )


def build_service(
    response: ModelProviderResponse,
    *,
    with_artifacts: bool = True,
) -> tuple[
    ProviderSemanticExtractionService,
    MockProvider,
    ArtifactStore,
    InMemorySemanticMemoryRepository,
]:
    provider = MockProvider(outcomes=(response,))
    artifacts = ArtifactStore()
    execution = ModelExecutionService(
        ProviderRegistry((provider,)),
        default_provider_id="mock",
        artifact_service=(
            ProviderArtifactService(cast(ArtifactStorePort, artifacts)) if with_artifacts else None
        ),
        monotonic_clock=lambda: 1,
    )
    registry = build_default_predicate_registry()
    repository = InMemorySemanticMemoryRepository()
    semantic_memory = SemanticMemoryService(
        repository,
        registry,
        SemanticMemoryConfiguration(),
        source_resolver=SourceResolver(),  # type: ignore[arg-type]
    )
    return (
        ProviderSemanticExtractionService(
            execution,
            semantic_memory,
            registry,
            SourceResolver(),  # type: ignore[arg-type]
            monotonic_clock=lambda: 1,
            id_factory=lambda: UUID(int=9),
        ),
        provider,
        artifacts,
        repository,
    )


def response(
    structured_output: dict[str, JsonValue] | list[JsonValue],
    *,
    tool_calls: tuple[NormalizedToolCall, ...] = (),
) -> ModelProviderResponse:
    return ModelProviderResponse(
        model_call_id=UUID(int=8),
        provider_id="mock",
        requested_model="mock-model",
        resolved_model="mock-model",
        structured_output=structured_output,
        tool_calls=tool_calls,
        finish_reason=ModelFinishReason.COMPLETED,
        latency_ms=0,
    )


@pytest.mark.asyncio
async def test_provider_extraction_is_artifacted_bounded_and_proposal_only() -> None:
    service, provider, artifacts, repository = build_service(response(proposal_payload()))
    proposal = await service.propose(
        extraction_request(), task_run_id=UUID(int=10), requested_model="mock-model"
    )
    assert proposal.extraction_id == UUID(int=2)
    assert len(artifacts.values) == 2
    sent = provider.received_requests[0]
    assert sent.tools == ()
    assert sent.tool_choice is ToolChoiceMode.NONE
    assert sent.response_format is ResponseFormat.JSON_SCHEMA
    assert not repository.observations
    assert not repository.claims


@pytest.mark.asyncio
async def test_provider_extraction_rejects_fabricated_spans_and_unknown_fields() -> None:
    fabricated = SPAN.model_copy(update={"excerpt_hash": "f" * 64})
    service, _, _, repository = build_service(response(proposal_payload(source_span=fabricated)))
    with pytest.raises(SemanticPolicyError, match="unauthorized source span"):
        await service.propose(
            extraction_request(), task_run_id=UUID(int=10), requested_model="mock-model"
        )
    assert not repository.observations

    unknown = proposal_payload()
    unknown["provider_write_authority"] = True
    service, _, _, _ = build_service(response(unknown))
    with pytest.raises(ValidationError, match="Extra inputs"):
        await service.propose(
            extraction_request(), task_run_id=UUID(int=10), requested_model="mock-model"
        )


@pytest.mark.asyncio
async def test_provider_extraction_requires_artifacts_and_rejects_tool_calls() -> None:
    service, provider, _, _ = build_service(response(proposal_payload()), with_artifacts=False)
    with pytest.raises(SemanticPolicyError, match="durable provider artifacts"):
        await service.propose(
            extraction_request(), task_run_id=UUID(int=10), requested_model="mock-model"
        )
    assert provider.call_count == 0

    tool_call = NormalizedToolCall(
        tool_call_id="call-1",
        name="write_database",
        arguments={"claim": "fabricated"},
    )
    service, _, artifacts, repository = build_service(
        response(proposal_payload(), tool_calls=(tool_call,))
    )
    with pytest.raises(SemanticPolicyError, match="forbidden tool calls"):
        await service.propose(
            extraction_request(), task_run_id=UUID(int=10), requested_model="mock-model"
        )
    assert len(artifacts.values) == 2
    assert not repository.claims
