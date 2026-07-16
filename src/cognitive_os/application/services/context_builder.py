"""Deterministic, bounded Context Builder orchestration."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from hashlib import sha256
from time import monotonic
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.config.context_config import ContextConfiguration
from cognitive_os.context.assembly import assemble_bundle, render_bundle
from cognitive_os.context.errors import (
    ContextBudgetError,
    ContextBuilderError,
    ContextRetrieverError,
    ContextSafetyError,
    ContextSourceStaleError,
)
from cognitive_os.context.persistence import ContextArtifactService
from cognitive_os.context.query import build_query_plan, reseal_candidate
from cognitive_os.context.ranking import (
    deduplicate_candidates,
    rank_candidates,
    ranking_profile,
    select_candidates,
)
from cognitive_os.context.registry import ContextRetrieverRegistry
from cognitive_os.context.safety import filter_unsafe_candidates
from cognitive_os.context.tokenization import ConservativeUtf8TokenEstimator
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.context import (
    ContextBuildFailure,
    ContextBuildResult,
    ContextBuildStatus,
    ContextBundleReference,
    ContextBundleRevision,
    ContextCandidate,
    ContextExclusion,
    ContextExclusionReason,
    ContextRequest,
    ContextRetrievalTrace,
    ContextSourceType,
    ContextTrustClass,
    ContextWarning,
    ContextWarningType,
    HydrationLevel,
    ProviderContextProfile,
    RetrieverCallTrace,
)
from cognitive_os.events.context_event_service import ContextEventService
from cognitive_os.events.context_events import (
    ContextBuildFailed,
    ContextBuildRequested,
    ContextBundleAttached,
    ContextBundleCreated,
)
from cognitive_os.memory.governance import sensitivity_allows
from cognitive_os.verification.context import build_context_verification_snapshot

type SourceSnapshotValidator = Callable[[ContextRequest], Awaitable[bool]]

_REQUIRED_SOURCES = {
    ContextSourceType.TASK_STATE,
    ContextSourceType.EXECUTION_PLAN,
}


class ContextBuilderService:
    def __init__(
        self,
        registry: ContextRetrieverRegistry,
        configuration: ContextConfiguration,
        provider_profiles: Mapping[str, ProviderContextProfile],
        *,
        artifacts: ContextArtifactService,
        estimator: ConservativeUtf8TokenEstimator | None = None,
        events: ContextEventService | None = None,
        source_snapshot_validator: SourceSnapshotValidator | None = None,
    ) -> None:
        self._registry = registry
        self._configuration = configuration
        self._profiles = dict(provider_profiles)
        self._estimator = estimator or ConservativeUtf8TokenEstimator()
        self._artifacts = artifacts
        self._events = events
        self._snapshot_validator = source_snapshot_validator
        self._builds: dict[UUID, ContextBuildResult] = {}

    async def build_context(self, request: ContextRequest) -> ContextBuildResult:
        return await self._build(request, revision=1, previous_revision=None)

    async def rebuild_context(
        self, request: ContextRequest, previous: ContextBundleRevision
    ) -> ContextBuildResult:
        if previous.context_request_id != request.context_request_id:
            raise ValueError("rebuild request does not match the previous bundle")
        return await self._build(
            request,
            revision=previous.revision + 1,
            previous_revision=previous.revision,
        )

    async def validate_bundle(self, bundle: ContextBundleRevision) -> bool:
        ContextBundleRevision.model_validate(bundle.model_dump(mode="python"))
        result = self._builds.get(bundle.context_request_id)
        if result is None or result.trace is None or result.rendered_context is None:
            raise ContextSourceStaleError("Context Bundle build evidence is unavailable")
        verification = build_context_verification_snapshot(
            bundle, result.trace, result.request, result.rendered_context
        )
        if not all(verification.values()):
            raise ContextSafetyError("Context Bundle verification failed")
        if self._snapshot_validator is None:
            return True
        if not await self._snapshot_validator(result.request):
            raise ContextSourceStaleError("Context Bundle source snapshot is stale")
        return True

    async def load_bundle(self, context_bundle_id: UUID, revision: int) -> ContextBundleRevision:
        return await self._artifacts.load(context_bundle_id, revision)

    async def record_attachment(
        self,
        request: ContextRequest,
        reference: ContextBundleReference,
        model_call_id: UUID,
    ) -> None:
        if self._events is not None:
            await self._events.append(
                request.context_request_id,
                request.task_run_id,
                ContextBundleAttached(
                    context_request_id=request.context_request_id,
                    context_bundle_id=reference.context_bundle_id,
                    revision=reference.context_bundle_revision,
                    model_call_id=model_call_id,
                    content_hash=reference.content_hash,
                    attached_at=utc_now(),
                ),
                correlation_id=request.task_run_id,
            )

    async def _build(
        self,
        request: ContextRequest,
        *,
        revision: int,
        previous_revision: int | None,
    ) -> ContextBuildResult:
        if request.provider_profile not in self._profiles:
            raise ContextBuilderError("unknown provider context profile")
        profile = self._profiles[request.provider_profile]
        self._validate_host_limits(request, profile)
        if self._events is not None:
            await self._events.append(
                request.context_request_id,
                request.task_run_id,
                ContextBuildRequested(
                    context_request_id=request.context_request_id,
                    task_run_id=request.task_run_id,
                    step_id=request.step_id,
                    query_hash=sha256(request.query.encode()).hexdigest(),
                    requested_at=request.created_at,
                ),
                correlation_id=request.task_run_id,
            )
        try:
            async with asyncio.timeout(
                min(
                    request.budget.maximum_elapsed_seconds,
                    self._configuration.maximum_build_seconds,
                )
            ):
                result = await self._execute_build(
                    request,
                    profile,
                    revision=revision,
                    previous_revision=previous_revision,
                )
        except asyncio.CancelledError:
            await self._record_failure(
                request, ContextBuildFailure.FAILED, "context_build_cancelled"
            )
            raise
        except ContextSafetyError:
            await self._record_failure(
                request, ContextBuildFailure.SAFETY_REJECTED, "safety_rejected"
            )
            raise
        except ContextBudgetError:
            await self._record_failure(
                request, ContextBuildFailure.BUDGET_EXHAUSTED, "required_content_does_not_fit"
            )
            raise
        except ContextRetrieverError:
            await self._record_failure(
                request,
                ContextBuildFailure.REQUIRED_SOURCE_MISSING,
                "required_retriever_unavailable",
            )
            raise
        except TimeoutError as error:
            await self._record_failure(
                request, ContextBuildFailure.BUDGET_EXHAUSTED, "context_build_timeout"
            )
            raise ContextBudgetError("Context Builder exceeded its elapsed-time budget") from error
        self._builds[request.context_request_id] = result
        return result

    async def _execute_build(
        self,
        request: ContextRequest,
        provider_profile: ProviderContextProfile,
        *,
        revision: int,
        previous_revision: int | None,
    ) -> ContextBuildResult:
        started = monotonic()
        query_plan = build_query_plan(request)
        semaphore = asyncio.Semaphore(self._configuration.maximum_parallel_retrievers)

        async def retrieve(
            subquery: object,
        ) -> tuple[tuple[ContextCandidate, ...], RetrieverCallTrace]:
            from cognitive_os.domain.context import RetrievalSubquery

            if not isinstance(subquery, RetrievalSubquery):
                raise TypeError("invalid retrieval subquery")
            try:
                retriever = self._registry.resolve(subquery.source_type)
            except ContextRetrieverError:
                if subquery.source_type in _REQUIRED_SOURCES:
                    raise
                return (), RetrieverCallTrace(
                    retriever_id=f"unavailable.{subquery.source_type.value}",
                    subquery_id=subquery.subquery_id,
                    returned_count=0,
                    elapsed_ms=0,
                    available=False,
                )
            if (
                retriever.descriptor.requires_network
                or subquery.mode not in retriever.descriptor.supported_modes
            ):
                if subquery.source_type in _REQUIRED_SOURCES:
                    raise ContextRetrieverError("required retriever is prohibited or incompatible")
                return (), RetrieverCallTrace(
                    retriever_id=retriever.descriptor.retriever_id,
                    subquery_id=subquery.subquery_id,
                    returned_count=0,
                    elapsed_ms=0,
                    available=False,
                )
            async with semaphore:
                values = await retriever.retrieve(subquery, request)
            return values, RetrieverCallTrace(
                retriever_id=retriever.descriptor.retriever_id,
                subquery_id=subquery.subquery_id,
                returned_count=len(values),
                elapsed_ms=0,
                access_audit_ids=tuple(
                    sorted(
                        {access_id for item in values for access_id in item.access_audit_ids},
                        key=str,
                    )
                ),
            )

        retrieved = await asyncio.gather(*(retrieve(item) for item in query_plan.subqueries))
        candidates = tuple(item for values, _ in retrieved for item in values)
        if len(candidates) > min(
            request.budget.maximum_candidates, self._configuration.maximum_candidates
        ):
            raise ContextBudgetError("retrievers exceeded the candidate budget")
        if not any(item.source_type is ContextSourceType.TASK_STATE for item in candidates):
            raise ContextRetrieverError("required current task context is missing")
        if not any(item.source_type is ContextSourceType.EXECUTION_PLAN for item in candidates):
            raise ContextRetrieverError("required execution-plan context is missing")

        policy_candidates, policy_exclusions = self._filter_policy(candidates, request)
        safe, safety_exclusions, safety_warnings = filter_unsafe_candidates(
            policy_candidates, sensitivity_limit=request.sensitivity_limit
        )
        deduplicated, duplicate_exclusions, decisions = deduplicate_candidates(safe)
        profile = ranking_profile(self._configuration)
        ranked = rank_candidates(deduplicated, request, profile)
        selected, packing_exclusions, quota_warnings = select_candidates(
            ranked, request, self._configuration, self._estimator
        )
        hydrated = await self._hydrate(selected)
        hydrated, hydration_byte_exclusions, hydration_byte_warnings = (
            self._enforce_hydration_bytes(hydrated)
        )
        hydrated, hydration_exclusions, hydration_warnings = filter_unsafe_candidates(
            hydrated, sensitivity_limit=request.sensitivity_limit
        )
        if any(
            item.required
            and item.candidate_id not in {candidate.candidate_id for candidate in hydrated}
            for item in selected
        ):
            raise ContextSafetyError("required content failed hydration safety validation")
        hydrated, exact_exclusions, exact_warnings = select_candidates(
            hydrated, request, self._configuration, self._estimator
        )
        exclusions = self._unique_exclusions(
            (
                *safety_exclusions,
                *policy_exclusions,
                *duplicate_exclusions,
                *packing_exclusions,
                *hydration_exclusions,
                *hydration_byte_exclusions,
                *exact_exclusions,
            ),
            selected_ids={item.candidate_id for item in hydrated},
        )
        warnings = tuple(
            (
                *safety_warnings,
                *quota_warnings,
                *hydration_warnings,
                *hydration_byte_warnings,
                *exact_warnings,
            )
        )
        bundle_id = uuid5(NAMESPACE_URL, f"context-bundle:{request.context_request_id}")
        bundle = assemble_bundle(
            bundle_id=bundle_id,
            revision=revision,
            previous_revision=previous_revision,
            request=request,
            candidates=hydrated,
            exclusions=exclusions,
            warnings=warnings,
            ranking_profile=profile,
            provider_profile=provider_profile,
            estimator=self._estimator,
        )
        rendered = render_bundle(bundle)
        if self._estimator.estimate_text(rendered) + request.budget.system_instruction_tokens > (
            request.budget.provider_context_limit - request.budget.reserved_output_tokens
        ):
            raise ContextBudgetError(
                "rendered Context Bundle exceeds the available provider budget"
            )
        trace = ContextRetrievalTrace(
            trace_id=uuid5(NAMESPACE_URL, f"context-trace:{request.context_request_id}:{revision}"),
            context_request_id=request.context_request_id,
            query_hash=query_plan.canonical_hash(),
            registry_snapshot_hash=self._registry.snapshot(),
            retriever_calls=tuple(call for _, call in retrieved),
            candidate_count=len({item.candidate_id for item in candidates}),
            ranked_candidate_ids=tuple(item.candidate_id for item in ranked),
            score_breakdowns={str(item.candidate_id): item.score_breakdown for item in ranked},
            deduplication_decisions=decisions,
            selected_candidate_ids=tuple(item.candidate_id for item in hydrated),
            selected_access_audit_ids=tuple(
                sorted(
                    {access_id for item in hydrated for access_id in item.access_audit_ids},
                    key=str,
                )
            ),
            exclusions=exclusions,
            token_estimates={str(item.candidate_id): item.token_estimate for item in hydrated},
            safety_warnings=warnings,
            source_snapshot=request.source_snapshot,
            elapsed_ms=0,
        )
        if len(trace.canonical_json().encode()) > self._configuration.maximum_trace_bytes:
            raise ContextBudgetError("retrieval trace exceeds the host byte limit")
        verification = build_context_verification_snapshot(bundle, trace, request, rendered)
        if not all(verification.values()):
            raise ContextSafetyError("required Context Bundle verification failed")
        bundle, reference, _, bundle_artifact = await self._artifacts.persist(
            request, trace, bundle, rendered
        )
        rendered = render_bundle(bundle)
        if self._events is not None:
            if (
                bundle.retrieval_trace_reference is None
                or bundle.rendered_context_reference is None
            ):
                raise ContextSafetyError("persisted Context Bundle references are incomplete")
            await self._events.append(
                request.context_request_id,
                request.task_run_id,
                ContextBundleCreated(
                    context_request_id=request.context_request_id,
                    context_bundle_id=bundle.context_bundle_id,
                    revision=bundle.revision,
                    bundle_artifact=bundle_artifact,
                    trace_artifact=bundle.retrieval_trace_reference,
                    rendered_context_artifact=bundle.rendered_context_reference,
                    content_hash=bundle.content_hash,
                    created_at=bundle.created_at,
                ),
                correlation_id=request.task_run_id,
            )
        result = ContextBuildResult(
            status=ContextBuildStatus.CREATED,
            request=request,
            bundle=bundle,
            trace=trace,
            rendered_context=rendered,
            bundle_reference=reference,
            warnings=warnings,
        )
        _ = monotonic() - started
        return result

    async def _hydrate(
        self, candidates: tuple[ContextCandidate, ...]
    ) -> tuple[ContextCandidate, ...]:
        hydrated = []
        for candidate in candidates[: self._configuration.maximum_hydrated_candidates]:
            retriever = self._registry.resolve(candidate.source_type)
            levels = candidate.available_hydration_levels
            level = (
                HydrationLevel.EXCERPT
                if candidate.evidence and HydrationLevel.EXCERPT in levels
                else HydrationLevel.SUMMARY
                if HydrationLevel.SUMMARY in levels
                else HydrationLevel.EXCERPT
                if HydrationLevel.EXCERPT in levels
                else HydrationLevel.FULL
                if HydrationLevel.FULL in levels
                else HydrationLevel.METADATA
            )
            hydrated.append(await retriever.hydrate(candidate, level))
        return tuple(hydrated)

    async def _record_failure(
        self, request: ContextRequest, failure: ContextBuildFailure, reason_code: str
    ) -> None:
        if self._events is not None:
            await self._events.append(
                request.context_request_id,
                request.task_run_id,
                ContextBuildFailed(
                    context_request_id=request.context_request_id,
                    failure=failure,
                    reason_code=reason_code,
                    failed_at=utc_now(),
                ),
                correlation_id=request.task_run_id,
            )

    def _validate_host_limits(
        self, request: ContextRequest, profile: ProviderContextProfile
    ) -> None:
        if request.budget.provider_context_limit > min(
            profile.maximum_context_tokens, self._configuration.default_context_limit
        ):
            raise ContextBudgetError("request exceeds the host or provider context limit")
        if request.budget.reserved_output_tokens > profile.maximum_output_tokens:
            raise ContextBudgetError("reserved output exceeds the provider output limit")
        if not sensitivity_allows(request.sensitivity_limit, profile.sensitivity_ceiling):
            raise ContextSafetyError("request sensitivity exceeds the provider profile ceiling")
        if (
            request.budget.maximum_retriever_calls
            > self._configuration.maximum_retriever_calls_per_build
        ):
            raise ContextBudgetError("request exceeds the retriever-call limit")
        if request.budget.maximum_candidates > self._configuration.maximum_candidates:
            raise ContextBudgetError("request exceeds the candidate limit")
        if request.budget.maximum_items > self._configuration.maximum_selected_items:
            raise ContextBudgetError("request exceeds the selected-item limit")
        if request.sensitivity_limit.value not in {
            "public",
            "internal",
            "confidential",
            "restricted",
        }:
            raise ContextSafetyError("unknown sensitivity ceiling")

    def _filter_policy(
        self, candidates: tuple[ContextCandidate, ...], request: ContextRequest
    ) -> tuple[tuple[ContextCandidate, ...], tuple[ContextExclusion, ...]]:
        kept: list[ContextCandidate] = []
        excluded: list[ContextExclusion] = []
        for candidate in candidates:
            reason = None
            detail = "candidate_status_is_not_allowed"
            if not any(scope in request.required_scopes for scope in candidate.scopes):
                reason = ContextExclusionReason.SCOPE_MISMATCH
                detail = "candidate_scope_does_not_match_request"
            elif (
                (
                    candidate.trust_class is ContextTrustClass.EXTERNAL
                    and not self._configuration.allow_external_sources
                )
                or (
                    candidate.trust_class is ContextTrustClass.UNVERIFIED
                    and not self._configuration.allow_unverified_sources
                )
                or (
                    candidate.trust_class is ContextTrustClass.DISPUTED
                    and not self._configuration.allow_disputed_sources
                )
            ):
                reason = ContextExclusionReason.STATUS_NOT_ALLOWED
            if reason is None:
                kept.append(candidate)
            else:
                excluded.append(
                    ContextExclusion(
                        candidate_id=candidate.candidate_id,
                        source_identity_hash=sha256(candidate.source_identity.encode()).hexdigest(),
                        reason=reason,
                        detail_code=detail,
                    )
                )
        return tuple(kept), tuple(excluded)

    def _enforce_hydration_bytes(
        self, candidates: tuple[ContextCandidate, ...]
    ) -> tuple[
        tuple[ContextCandidate, ...],
        tuple[ContextExclusion, ...],
        tuple[ContextWarning, ...],
    ]:
        kept: list[ContextCandidate] = []
        exclusions: list[ContextExclusion] = []
        warnings: list[ContextWarning] = []
        total = 0
        for candidate in candidates:
            value = candidate.content
            if value is not None:
                encoded = value.encode()
                if len(encoded) > self._configuration.maximum_source_excerpt_bytes:
                    value = encoded[: self._configuration.maximum_source_excerpt_bytes].decode(
                        "utf-8", errors="ignore"
                    )
                    warning = ContextWarning(
                        warning_type=ContextWarningType.CONTENT_TRUNCATED,
                        code="source_excerpt_byte_limit",
                        message="Hydrated content was truncated to the host byte limit.",
                        candidate_id=candidate.candidate_id,
                        source_references=candidate.provenance,
                    )
                    warnings.append(warning)
                    candidate = reseal_candidate(
                        candidate,
                        content=value,
                        content_hash=sha256(value.encode()).hexdigest(),
                        warnings=tuple((*candidate.warnings, warning)),
                    )
                size = len(value.encode())
            else:
                size = 0
            if total + size > self._configuration.maximum_total_hydrated_bytes:
                if candidate.required:
                    raise ContextBudgetError("required hydrated content exceeds the byte budget")
                exclusions.append(
                    ContextExclusion(
                        candidate_id=candidate.candidate_id,
                        source_identity_hash=sha256(candidate.source_identity.encode()).hexdigest(),
                        reason=ContextExclusionReason.TOKEN_BUDGET,
                        detail_code="total_hydrated_byte_limit",
                    )
                )
                continue
            total += size
            kept.append(candidate)
        return tuple(kept), tuple(exclusions), tuple(warnings)

    @staticmethod
    def _unique_exclusions(
        values: tuple[ContextExclusion, ...], *, selected_ids: set[UUID]
    ) -> tuple[ContextExclusion, ...]:
        unique = {
            item.candidate_id: item
            for item in values
            if item.candidate_id is not None and item.candidate_id not in selected_ids
        }
        return tuple(unique[key] for key in sorted(unique, key=str))
