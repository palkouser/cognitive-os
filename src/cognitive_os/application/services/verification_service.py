"""Authoritative bounded verifier execution with immutable lifecycle events."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from hashlib import sha256
from uuid import UUID, uuid4

import jsonschema

from cognitive_os.domain.common import ErrorInfo, utc_now
from cognitive_os.domain.enums import VerifierStatus
from cognitive_os.domain.verification import VerificationSubjectRef, VerifierResult
from cognitive_os.domain.verifiers import (
    VerificationExecution,
    VerificationExecutionStatus,
    VerificationRequest,
)
from cognitive_os.events.verification_events import (
    VerifierCompleted,
    VerifierFailed,
    VerifierStarted,
)
from cognitive_os.events.verifier_event_service import VerifierEventService
from cognitive_os.verification.errors import VerificationPersistenceError
from cognitive_os.verification.registry import VerifierRegistry


def configuration_hash(configuration: Mapping[str, object]) -> str:
    return sha256(
        json.dumps(configuration, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class VerificationService:
    def __init__(self, registry: VerifierRegistry, events: VerifierEventService) -> None:
        self._registry = registry
        self._events = events

    async def execute(self, request: VerificationRequest) -> VerificationExecution:
        verifier = self._registry.require(request.verifier_id, request.verifier_version)
        descriptor = verifier.descriptor
        encoded_subject = json.dumps(
            request.subject.model_dump(mode="json"), sort_keys=True
        ).encode()
        if len(encoded_subject) > descriptor.maximum_input_bytes:
            raise ValueError("verification subject exceeds verifier input limit")
        jsonschema.validate(request.configuration, descriptor.configuration_schema)
        config_hash = configuration_hash(request.configuration)
        started = utc_now()
        subject_ref = VerificationSubjectRef(
            subject_type=request.subject.subject_type.value, subject_id=str(request.verification_id)
        )
        try:
            start_append = await self._events.append(
                verification_id=request.verification_id,
                payload=VerifierStarted(
                    verifier_result_id=request.verification_id,
                    verifier_id=request.verifier_id,
                    verifier_version=request.verifier_version,
                    subject=subject_ref,
                    started_at=started,
                    configuration_hash=config_hash,
                ),
                correlation_id=request.correlation_id,
                causation_event_id=request.causation_event_id,
            )
        except Exception as caught:
            raise VerificationPersistenceError(
                "verifier.started could not be persisted"
            ) from caught
        start_event_id = start_append.event_ids[-1]
        try:
            async with asyncio.timeout(descriptor.default_timeout_seconds):
                result = await verifier.verify(request)
            if (
                result.verifier_id != descriptor.verifier_id
                or result.verifier_version != descriptor.version
            ):
                raise ValueError("verifier result identity does not match its descriptor")
            if result.subject.subject_type != request.subject.subject_type.value:
                raise ValueError("verifier result subject does not match the request")
        except TimeoutError:
            now = utc_now()
            timeout_error = ErrorInfo(
                code="verifier_timeout", message="verifier exceeded its configured timeout"
            )
            result = VerifierResult(
                verifier_result_id=uuid4(),
                verifier_id=descriptor.verifier_id,
                verifier_version=descriptor.version,
                subject=subject_ref,
                status=VerifierStatus.ERROR,
                started_at=started,
                finished_at=now,
                error=timeout_error,
            )
            await self._persist_failed(request, result, timeout_error, start_event_id)
            return VerificationExecution(
                verification_id=request.verification_id,
                verifier_id=descriptor.verifier_id,
                verifier_version=descriptor.version,
                status=VerificationExecutionStatus.TIMED_OUT,
                started_at=started,
                finished_at=now,
                result=result,
                configuration_hash=config_hash,
                error=timeout_error,
            )
        except Exception as caught:
            now = utc_now()
            execution_error = ErrorInfo(
                code="verifier_execution_error",
                message="verifier infrastructure failed",
                error_type=type(caught).__name__,
            )
            await self._persist_failed(request, None, execution_error, start_event_id)
            return VerificationExecution(
                verification_id=request.verification_id,
                verifier_id=descriptor.verifier_id,
                verifier_version=descriptor.version,
                status=VerificationExecutionStatus.FAILED,
                started_at=started,
                finished_at=now,
                configuration_hash=config_hash,
                error=execution_error,
            )
        try:
            await self._events.append(
                verification_id=request.verification_id,
                payload=VerifierCompleted(result=result),
                correlation_id=request.correlation_id,
                causation_event_id=start_event_id,
            )
        except Exception as caught:
            raise VerificationPersistenceError(
                "terminal verifier event could not be persisted; "
                "execution must not be retried automatically"
            ) from caught
        return VerificationExecution(
            verification_id=request.verification_id,
            verifier_id=descriptor.verifier_id,
            verifier_version=descriptor.version,
            status=VerificationExecutionStatus.COMPLETED,
            started_at=started,
            finished_at=result.finished_at,
            result=result,
            evidence_artifacts=result.evidence_artifacts,
            configuration_hash=config_hash,
        )

    async def _persist_failed(
        self,
        request: VerificationRequest,
        result: VerifierResult | None,
        error: ErrorInfo,
        causation_event_id: UUID,
    ) -> None:
        try:
            await self._events.append(
                verification_id=request.verification_id,
                payload=VerifierFailed(
                    verifier_result_id=result.verifier_result_id
                    if result
                    else request.verification_id,
                    finished_at=utc_now(),
                    error=error,
                ),
                correlation_id=request.correlation_id,
                causation_event_id=causation_event_id,
            )
        except Exception as caught:
            raise VerificationPersistenceError(
                "terminal verifier failure event could not be persisted; "
                "execution must not be retried automatically"
            ) from caught
