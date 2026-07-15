"""Host-bounded provider proposals with no semantic write authority."""

import base64
import json
import time
from collections.abc import Callable
from datetime import datetime
from uuid import UUID, uuid4

from cognitive_os.application.services.model_execution import ModelExecutionService
from cognitive_os.domain.common import JsonValue, utc_now
from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ProviderMessage,
    ProviderMessageRole,
)
from cognitive_os.domain.provider import (
    ModelFinishReason,
    ResponseFormat,
    ToolChoiceMode,
)
from cognitive_os.domain.semantic_memory import (
    SemanticEntityRef,
    SemanticExtractionProposal,
    SemanticExtractionRequest,
    SemanticLiteral,
    semantic_hash,
)
from cognitive_os.events.semantic_memory_event_service import SemanticMemoryEventService
from cognitive_os.events.semantic_memory_events import SemanticExtractionRejected

from .canonicalization import canonical_identifier, canonical_value
from .errors import SemanticPolicyError
from .grounding import TrustedSourceResolver
from .predicates import PredicateRegistry
from .service import SemanticMemoryService


class ProviderSemanticExtractionService:
    """Ask a configured provider for a proposal, then revalidate it on the host."""

    def __init__(
        self,
        model_execution: ModelExecutionService,
        semantic_memory: SemanticMemoryService,
        registry: PredicateRegistry,
        source_resolver: TrustedSourceResolver,
        *,
        events: SemanticMemoryEventService | None = None,
        clock: Callable[[], datetime] = utc_now,
        monotonic_clock: Callable[[], float] = time.monotonic,
        id_factory: Callable[[], UUID] = uuid4,
    ) -> None:
        self._models = model_execution
        self._semantic_memory = semantic_memory
        self._registry = registry
        self._sources = source_resolver
        self._events = events
        self._clock = clock
        self._monotonic = monotonic_clock
        self._id_factory = id_factory

    @staticmethod
    def required_schema() -> dict[str, JsonValue]:
        return SemanticExtractionProposal.model_json_schema(mode="serialization")

    async def propose(
        self,
        request: SemanticExtractionRequest,
        *,
        task_run_id: UUID,
        requested_model: str,
        provider_id: str | None = None,
    ) -> SemanticExtractionProposal:
        started = self._monotonic()
        try:
            self._validate_request(request)
            excerpts = []
            for span in request.source_spans:
                excerpt = await self._sources.resolve_span(
                    span,
                    scope=request.scope,
                    sensitivity=request.sensitivity_ceiling,
                )
                excerpts.append(
                    {
                        "span": span.model_dump(mode="json"),
                        "excerpt_base64": base64.b64encode(excerpt).decode("ascii"),
                    }
                )
            model_call_id = self._id_factory()
            provider_request = ModelProviderRequest(
                model_call_id=model_call_id,
                task_run_id=task_run_id,
                correlation_id=model_call_id,
                requested_model=requested_model,
                messages=(
                    ProviderMessage(
                        role=ProviderMessageRole.USER,
                        content=json.dumps(
                            {
                                "semantic_extraction_request": request.model_dump(mode="json"),
                                "authoritative_excerpts": excerpts,
                            },
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                    ),
                ),
                system_instructions=(
                    "Return only the requested semantic extraction proposal. The supplied "
                    "spans, scope, registry, and budgets are immutable. Do not call tools, "
                    "invent sources, or claim write authority."
                ),
                tools=(),
                tool_choice=ToolChoiceMode.NONE,
                response_format=ResponseFormat.JSON_SCHEMA,
                response_schema=request.required_output_schema,
                temperature=0,
                max_output_tokens=32_768,
                timeout_seconds=float(
                    self._semantic_memory.configuration.maximum_extraction_elapsed_seconds
                ),
                metadata={
                    "purpose": "semantic_extraction_proposal",
                    "semantic_request_id": str(request.request_id),
                },
            )
            response = await self._models.execute(provider_request, provider_id=provider_id)
            if self._monotonic() - started > (
                self._semantic_memory.configuration.maximum_extraction_elapsed_seconds
            ):
                raise SemanticPolicyError("provider extraction elapsed-time budget exceeded")
            if response.finish_reason is not ModelFinishReason.COMPLETED:
                raise SemanticPolicyError("provider extraction did not complete normally")
            if response.tool_calls:
                raise SemanticPolicyError("provider extraction returned forbidden tool calls")
            if not isinstance(response.structured_output, dict):
                raise SemanticPolicyError("provider extraction requires structured output")
            proposal = SemanticExtractionProposal.model_validate(response.structured_output)
            await self._validate_proposal(request, proposal)
            return proposal
        except Exception as error:
            await self._record_rejection(request, error)
            raise

    def _validate_request(self, request: SemanticExtractionRequest) -> None:
        configuration = self._semantic_memory.configuration
        if configuration.maximum_provider_extraction_calls < 1:
            raise SemanticPolicyError("provider semantic extraction is disabled")
        if not self._models.artifact_persistence_enabled:
            raise SemanticPolicyError("provider extraction requires durable provider artifacts")
        if request.registry_snapshot_hash != self._registry.snapshot_hash():
            raise SemanticPolicyError("semantic extraction registry snapshot is stale")
        if request.required_output_schema != self.required_schema():
            raise SemanticPolicyError("semantic extraction output schema is not host-owned")
        if (
            request.budget.maximum_observations > configuration.maximum_observations_per_request
            or request.budget.maximum_claims > configuration.maximum_claims_per_request
            or request.budget.maximum_relations > configuration.maximum_relations_per_request
            or request.budget.maximum_evidence_links
            > configuration.maximum_claims_per_request
            * configuration.maximum_evidence_links_per_claim
        ):
            raise SemanticPolicyError("semantic extraction request exceeds host policy")

    async def _validate_proposal(
        self,
        request: SemanticExtractionRequest,
        proposal: SemanticExtractionProposal,
    ) -> None:
        configuration = self._semantic_memory.configuration
        if proposal.extraction_id != request.request_id:
            raise SemanticPolicyError("provider changed the semantic extraction identity")
        if proposal.registry_snapshot_hash != request.registry_snapshot_hash:
            raise SemanticPolicyError("provider changed the predicate registry snapshot")
        if proposal.budget != request.budget:
            raise SemanticPolicyError("provider changed the semantic extraction budget")
        if len(proposal.contradictions) > configuration.maximum_contradiction_candidates:
            raise SemanticPolicyError("provider contradiction candidate limit exceeded")
        authorized_spans = set(request.source_spans)
        for observation in proposal.observations:
            if not set(observation.source_spans) <= authorized_spans:
                raise SemanticPolicyError("provider proposal contains an unauthorized source span")
            for span in observation.source_spans:
                await self._sources.validate_span(
                    span,
                    scope=request.scope,
                    sensitivity=request.sensitivity_ceiling,
                )
        for claim in proposal.claims:
            if claim.existing_observation_ids:
                raise SemanticPolicyError(
                    "provider proposals cannot select stored observations by identifier"
                )
            predicate_id = canonical_identifier(claim.predicate_id)
            descriptor = self._registry.require(predicate_id)
            subject_type = (
                claim.subject.entity_type
                if isinstance(claim.subject, SemanticEntityRef)
                else claim.subject.namespace
            )
            if subject_type not in descriptor.allowed_subject_types:
                raise SemanticPolicyError("provider proposal contains an invalid subject type")
            object_type = (
                claim.object.literal_kind
                if isinstance(claim.object, SemanticLiteral)
                else claim.object.value_type
            )
            if object_type not in descriptor.allowed_object_types:
                raise SemanticPolicyError("provider proposal contains an invalid object type")
            subject_value = (
                claim.subject.entity_id
                if isinstance(claim.subject, SemanticEntityRef)
                else claim.subject.identifier
            )
            if len(subject_value.encode()) > configuration.maximum_subject_bytes:
                raise SemanticPolicyError("provider proposal subject exceeds the host byte limit")
            if len(canonical_value(claim.object).encode()) > configuration.maximum_object_bytes:
                raise SemanticPolicyError("provider proposal object exceeds the host byte limit")

    async def _record_rejection(
        self,
        request: SemanticExtractionRequest,
        error: Exception,
    ) -> None:
        if self._events is None:
            return
        version = await self._events.current_version(request.request_id)
        await self._events.append(
            aggregate_id=request.request_id,
            payload=SemanticExtractionRejected(
                extraction_id=request.request_id,
                reason_code=type(error).__name__,
                proposal_hash=semantic_hash(
                    {"request_id": str(request.request_id), "reason": type(error).__name__}
                ),
                rejected_at=self._clock(),
            ),
            expected_version=version,
            correlation_id=request.request_id,
        )
