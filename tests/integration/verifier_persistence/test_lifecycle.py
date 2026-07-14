from datetime import UTC, datetime
from uuid import uuid4

import pytest

from cognitive_os.application.services.verification_service import VerificationService
from cognitive_os.domain.verifiers import (
    VerificationRequest,
    VerificationSubject,
    VerificationSubjectType,
)
from cognitive_os.events.storage import AppendResult
from cognitive_os.events.verifier_event_service import VerifierEventService
from cognitive_os.verification.errors import VerificationPersistenceError
from cognitive_os.verification.generic import ExactValueVerifier
from cognitive_os.verification.registry import VerifierRegistry


class MemoryStore:
    def __init__(self, fail_terminal: bool = False) -> None:
        self.events = []
        self.fail_terminal = fail_terminal

    async def get_stream_version(self, stream_id):
        values = [item for item in self.events if item.stream_id == stream_id]
        return values[-1].stream_version if values else None

    async def append(self, events, *, expected_version):
        event = events[0]
        if self.fail_terminal and event.event_type in {"verifier.completed", "verifier.failed"}:
            raise RuntimeError("terminal persistence unavailable")
        current = len([item for item in self.events if item.stream_id == event.stream_id])
        assert current == expected_version
        self.events.append(event)
        return AppendResult(
            stream_id=event.stream_id,
            previous_stream_version=current,
            current_stream_version=current + 1,
            event_ids=(event.event_id,),
            global_positions=(len(self.events),),
            stored_at=event.recorded_at,
        )


def request() -> VerificationRequest:
    return VerificationRequest(
        verification_id=uuid4(),
        task_run_id=uuid4(),
        criterion_id=uuid4(),
        verifier_id="generic.exact",
        verifier_version="1",
        subject=VerificationSubject(
            subject_type=VerificationSubjectType.STRUCTURED_VALUE, inline_value=42
        ),
        configuration={"expected": 42},
        requested_at=datetime.now(UTC),
        correlation_id=uuid4(),
    )


def service(store: MemoryStore) -> VerificationService:
    registry = VerifierRegistry()
    registry.register(ExactValueVerifier())
    return VerificationService(registry, VerifierEventService(store))


@pytest.mark.asyncio
async def test_verifier_lifecycle_has_exactly_one_terminal_event() -> None:
    store = MemoryStore()
    execution = await service(store).execute(request())
    assert execution.result and execution.result.status.value == "passed"
    assert [item.event_type for item in store.events] == ["verifier.started", "verifier.completed"]
    assert store.events[0].payload["configuration_hash"] == execution.configuration_hash


@pytest.mark.asyncio
async def test_terminal_persistence_failure_is_uncertain_and_not_hidden() -> None:
    store = MemoryStore(fail_terminal=True)
    with pytest.raises(VerificationPersistenceError, match="must not be retried"):
        await service(store).execute(request())
    assert [item.event_type for item in store.events] == ["verifier.started"]
