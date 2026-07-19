"""Exact-revision skill orchestration through an injected existing Controller adapter."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.application.ports.artifact_store import ArtifactStorePort
from cognitive_os.application.ports.context_builder import ContextBuilderPort
from cognitive_os.application.ports.skill_repository import SkillRepositoryPort
from cognitive_os.domain.context import ContextBuildStatus, ContextRequest
from cognitive_os.domain.skills import (
    SkillAccessRecord,
    SkillAccessType,
    SkillExecutionRequest,
    SkillExecutionResult,
    SkillExecutionStatus,
    SkillRegistrySnapshot,
    SkillRevision,
    SkillStatus,
)
from cognitive_os.events.skill_event_service import SkillEventService
from cognitive_os.events.skill_events import (
    SkillExecutionCompleted,
    SkillExecutionFailed,
    SkillExecutionStarted,
)

from .errors import SkillPolicyError
from .statistics import rebuild_statistics


class ExistingControllerSkillRunner(Protocol):
    """Adapter implemented by the existing Controller, never a second control loop."""

    async def start(
        self, request: SkillExecutionRequest, revision: SkillRevision
    ) -> SkillExecutionResult: ...

    async def resume(self, execution_id: UUID) -> SkillExecutionResult: ...

    async def cancel(self, execution_id: UUID, reason: str) -> SkillExecutionResult: ...


class SkillExecutionService:
    def __init__(
        self,
        repository: SkillRepositoryPort,
        artifacts: ArtifactStorePort,
        context_builder: ContextBuilderPort,
        controller: ExistingControllerSkillRunner,
        context_request_factory: Callable[[SkillExecutionRequest, SkillRevision], ContextRequest],
        registry_snapshot: Callable[[], SkillRegistrySnapshot],
        events: SkillEventService | None = None,
    ) -> None:
        self._repository = repository
        self._artifacts = artifacts
        self._context_builder = context_builder
        self._controller = controller
        self._context_request_factory = context_request_factory
        self._registry_snapshot = registry_snapshot
        self._events = events
        self._requests: dict[UUID, SkillExecutionRequest] = {}

    async def prepare_execution(self, request: SkillExecutionRequest) -> SkillExecutionRequest:
        revision = await self._repository.get_revision(request.skill_id, request.skill_revision)
        if revision is None or revision.status is not SkillStatus.VERIFIED:
            raise SkillPolicyError("only an exact verified skill revision may execute")
        if revision.package_hash != request.package_hash:
            raise SkillPolicyError("skill package hash does not match the requested revision")
        if request.expected_registry_snapshots != self._registry_snapshot():
            raise SkillPolicyError("skill execution registry snapshot is stale")
        if not await self._artifacts.verify(revision.package_artifact.artifact_id):
            raise SkillPolicyError("skill package artifact integrity check failed")
        self._validate_budget(request, revision)
        self._validate_inputs(request, revision)
        if request.context_bundle_reference is not None:
            bundle = await self._context_builder.load_bundle(
                request.context_bundle_reference.context_bundle_id,
                request.context_bundle_reference.context_bundle_revision,
            )
            if not await self._context_builder.validate_bundle(bundle):
                raise SkillPolicyError("skill Context Bundle validation failed")
            return request
        context_request = self._context_request_factory(request, revision)
        built = await self._context_builder.build_context(context_request)
        if (
            built.status is not ContextBuildStatus.CREATED
            or built.bundle is None
            or built.bundle_reference is None
        ):
            raise SkillPolicyError("skill Context Bundle could not be created")
        if not await self._context_builder.validate_bundle(built.bundle):
            raise SkillPolicyError("skill Context Bundle validation failed")
        return request.model_copy(update={"context_bundle_reference": built.bundle_reference})

    async def start_execution(self, request: SkillExecutionRequest) -> SkillExecutionResult:
        prepared = await self.prepare_execution(request)
        self._requests[prepared.execution_id] = prepared
        revision = await self._repository.get_revision(prepared.skill_id, prepared.skill_revision)
        if revision is None:
            raise SkillPolicyError("skill revision disappeared during preparation")
        if self._events is not None:
            await self._events.append(
                prepared.execution_id,
                SkillExecutionStarted(
                    execution_id=prepared.execution_id,
                    skill_id=prepared.skill_id,
                    revision=prepared.skill_revision,
                    task_run_id=prepared.task_run_id,
                    package_hash=prepared.package_hash,
                    occurred_at=prepared.created_at,
                ),
                correlation_id=prepared.task_run_id,
            )
        result = await self._controller.start(prepared, revision)
        self._validate_result(prepared, result)
        if result.status is SkillExecutionStatus.WAITING:
            return result
        return await self._persist_result(result, revision)

    async def resume_execution(self, execution_id: UUID) -> SkillExecutionResult:
        existing = await self._repository.get_execution(execution_id)
        if existing is not None:
            return existing
        request = self._requests.get(execution_id)
        if request is None:
            raise SkillPolicyError("skill execution resume state is unavailable")
        result = await self._controller.resume(execution_id)
        self._validate_result(request, result)
        if result.status is SkillExecutionStatus.WAITING:
            return result
        revision = await self._repository.get_revision(result.skill_id, result.skill_revision)
        if revision is None:
            raise SkillPolicyError("resumed skill revision is unavailable")
        return await self._persist_result(result, revision)

    async def cancel_execution(self, execution_id: UUID, reason: str) -> SkillExecutionResult:
        if not reason.strip():
            raise ValueError("skill cancellation requires a reason")
        existing = await self._repository.get_execution(execution_id)
        if existing is not None:
            return existing
        request = self._requests.get(execution_id)
        if request is None:
            raise SkillPolicyError("skill execution cancellation state is unavailable")
        result = await self._controller.cancel(execution_id, reason)
        self._validate_result(request, result)
        revision = await self._repository.get_revision(result.skill_id, result.skill_revision)
        if revision is None:
            raise SkillPolicyError("cancelled skill revision is unavailable")
        return await self._persist_result(result, revision)

    async def read_execution(self, execution_id: UUID) -> SkillExecutionResult | None:
        return await self._repository.get_execution(execution_id)

    @staticmethod
    def _validate_budget(request: SkillExecutionRequest, revision: SkillRevision) -> None:
        requested = request.controller_budget
        allowed = revision.resource_budget
        for field in type(requested).model_fields:
            if getattr(requested, field) > getattr(allowed, field):
                raise SkillPolicyError(f"skill execution exceeds {field}")

    @staticmethod
    def _validate_inputs(request: SkillExecutionRequest, revision: SkillRevision) -> None:
        bindings = {item.name for item in request.input_bindings}
        if len(bindings) != len(request.input_bindings):
            raise SkillPolicyError("skill input bindings must be unique")
        fields = {item.name: item for item in revision.input_specification.fields}
        if bindings - fields.keys():
            raise SkillPolicyError("skill request contains an unknown input binding")
        missing = {name for name, field in fields.items() if field.required} - bindings
        if missing:
            raise SkillPolicyError("skill request is missing required input bindings")

    @staticmethod
    def _validate_result(request: SkillExecutionRequest, result: SkillExecutionResult) -> None:
        if (
            result.execution_id != request.execution_id
            or result.skill_id != request.skill_id
            or result.skill_revision != request.skill_revision
            or result.task_run_id != request.task_run_id
        ):
            raise SkillPolicyError("Controller result changed exact skill execution identity")

    async def _persist_result(
        self, result: SkillExecutionResult, revision: SkillRevision
    ) -> SkillExecutionResult:
        stored = await self._repository.record_execution(result)
        if self._events is not None:
            event = (
                SkillExecutionFailed(
                    execution_id=result.execution_id,
                    skill_id=result.skill_id,
                    revision=result.skill_revision,
                    task_run_id=result.task_run_id,
                    status=result.status,
                    result_hash=result.result_hash,
                    reason_code=result.failure or result.status.value,
                    occurred_at=result.finished_at,
                )
                if result.status
                in {
                    SkillExecutionStatus.FAILED,
                    SkillExecutionStatus.REJECTED,
                    SkillExecutionStatus.UNVERIFIABLE,
                    SkillExecutionStatus.CANCELLED,
                }
                else SkillExecutionCompleted(
                    execution_id=result.execution_id,
                    skill_id=result.skill_id,
                    revision=result.skill_revision,
                    task_run_id=result.task_run_id,
                    status=result.status,
                    result_hash=result.result_hash,
                    occurred_at=result.finished_at,
                )
            )
            await self._events.append(result.execution_id, event, correlation_id=result.task_run_id)
        executions = await self._repository.list_executions(revision.skill_id, revision.revision)
        await self._repository.write_statistics(
            rebuild_statistics(revision.skill_id, revision.revision, executions)
        )
        current = await self._repository.get_current(revision.skill_id)
        if current is None:
            raise SkillPolicyError("skill identity disappeared during execution")
        await self._repository.record_access(
            (
                SkillAccessRecord(
                    access_id=uuid5(
                        NAMESPACE_URL,
                        f"skill-execution:{result.execution_id}:{revision.content_hash}",
                    ),
                    skill_id=revision.skill_id,
                    revision=revision.revision,
                    access_type=SkillAccessType.EXECUTION,
                    task_run_id=result.task_run_id,
                    scope=current[0].identity.scope,
                    sensitivity=revision.sensitivity,
                    accessed_at=result.finished_at,
                ),
            )
        )
        return stored
