"""S21C3-012: an outcome is bytes plus an event, or it is not an outcome."""

from __future__ import annotations

from uuid import uuid4

import pytest

from cognitive_os.coding.hidden_verification import HiddenVerificationStatus
from cognitive_os.coding.outcome_recording import (
    CodingOutcomeRecorder,
    OutcomeRecordingError,
)
from cognitive_os.domain.coding import CodingOutcomeStatus
from cognitive_os.domain.reality import (
    RealityCandidateSource,
    RealityCandidateStrategy,
    RealityRunIdentity,
    RealityRunKind,
)
from cognitive_os.events.coding_event_service import CodingEventService
from cognitive_os.events.coding_events import CodingOutcomeRecorded, CodingResultPackaged
from cognitive_os.events.memory_store import MemoryEventStore

from .reality_fixtures import (
    InMemoryArtifactStore,
    candidate_manifest,
    coding_outcome,
    digest,
    hidden_evidence,
    task_manifest,
)


def _recorder() -> tuple[CodingOutcomeRecorder, InMemoryArtifactStore, MemoryEventStore]:
    artifacts = InMemoryArtifactStore()
    store = MemoryEventStore()
    recorder = CodingOutcomeRecorder(artifacts, CodingEventService(store), store)
    return recorder, artifacts, store


@pytest.mark.asyncio
async def test_recorded_outcome_resolves_to_bytes_and_to_an_event() -> None:
    recorder, artifacts, store = _recorder()
    task = task_manifest()
    task_run_id = uuid4()
    outcome = coding_outcome(task_run_id=task_run_id)

    recorded = await recorder.record(
        outcome=outcome,
        task=task,
        evidence=hidden_evidence(task=task, task_run_id=task_run_id),
        candidate=None,
        correlation_id=task_run_id,
    )

    reference = recorded.reference
    assert recorded.replayed is False
    assert reference.run_kind is RealityRunKind.BASELINE
    assert reference.outcome_hash == outcome.canonical_hash()
    assert await artifacts.verify(reference.outcome_artifact_id)
    assert await artifacts.verify(reference.hidden_evidence_artifact_id)

    stored = await store.get_event(reference.source_event_id)
    assert stored is not None
    assert stored.envelope.event_type == "coding.outcome_recorded"

    written = await artifacts.get_bytes(reference.outcome_artifact_id)
    assert written == outcome.canonical_json().encode()


@pytest.mark.asyncio
async def test_the_historical_result_packaged_event_is_untouched() -> None:
    """C3 adds an event; it does not widen one that already has rows."""
    assert CodingResultPackaged.event_type == "coding.result_packaged"
    assert set(CodingResultPackaged.model_fields) == {
        "task_run_id",
        "outcome_hash",
        "status",
        "packaged_at",
    }
    assert CodingOutcomeRecorded.event_type != CodingResultPackaged.event_type


@pytest.mark.asyncio
async def test_recording_the_same_outcome_twice_yields_one_identity() -> None:
    recorder, _, store = _recorder()
    task = task_manifest()
    task_run_id = uuid4()
    outcome = coding_outcome(task_run_id=task_run_id)
    evidence = hidden_evidence(task=task, task_run_id=task_run_id)

    first = await recorder.record(
        outcome=outcome, task=task, evidence=evidence, candidate=None, correlation_id=task_run_id
    )
    second = await recorder.record(
        outcome=outcome, task=task, evidence=evidence, candidate=None, correlation_id=task_run_id
    )

    assert second.replayed is True
    assert second.reference.source_event_id == first.reference.source_event_id
    assert second.reference.outcome_hash == first.reference.outcome_hash
    recorded_events = [
        item for item in store.stored_events() if item.envelope.event_type.endswith("recorded")
    ]
    assert len(recorded_events) == 1


@pytest.mark.asyncio
async def test_a_different_outcome_under_the_same_run_is_a_second_execution() -> None:
    recorder, _, _store = _recorder()
    task = task_manifest()
    task_run_id = uuid4()

    first = await recorder.record(
        outcome=coding_outcome(task_run_id=task_run_id, marker="first"),
        task=task,
        evidence=hidden_evidence(task=task, task_run_id=task_run_id),
        candidate=None,
        correlation_id=task_run_id,
    )
    second = await recorder.record(
        outcome=coding_outcome(task_run_id=task_run_id, marker="second"),
        task=task,
        evidence=hidden_evidence(task=task, task_run_id=task_run_id),
        candidate=None,
        correlation_id=task_run_id,
    )

    assert second.replayed is False
    assert second.reference.outcome_hash != first.reference.outcome_hash


@pytest.mark.asyncio
async def test_bytes_that_cannot_be_read_back_stop_the_event() -> None:
    """A metadata row whose file is missing is the C1 defect. It must not become an event."""
    recorder, artifacts, store = _recorder()
    task = task_manifest()
    task_run_id = uuid4()

    original_put = artifacts.put_bytes

    async def losing_put(data: bytes, **kwargs: object) -> object:
        reference = await original_put(data, **kwargs)  # type: ignore[arg-type]
        artifacts.forget(reference.artifact_id)
        return reference

    artifacts.put_bytes = losing_put  # type: ignore[method-assign, assignment]

    with pytest.raises(OutcomeRecordingError, match="could not be read back"):
        await recorder.record(
            outcome=coding_outcome(task_run_id=task_run_id),
            task=task,
            evidence=hidden_evidence(task=task, task_run_id=task_run_id),
            candidate=None,
            correlation_id=task_run_id,
        )

    assert not [
        item for item in store.stored_events() if item.envelope.event_type.endswith("recorded")
    ]


@pytest.mark.asyncio
async def test_evidence_from_another_run_is_refused() -> None:
    recorder, _, _ = _recorder()
    task = task_manifest()
    task_run_id = uuid4()

    with pytest.raises(OutcomeRecordingError, match="different task run"):
        await recorder.record(
            outcome=coding_outcome(task_run_id=task_run_id),
            task=task,
            evidence=hidden_evidence(task=task, task_run_id=uuid4()),
            candidate=None,
            correlation_id=task_run_id,
        )


@pytest.mark.asyncio
async def test_candidate_from_another_task_is_refused() -> None:
    recorder, _, _ = _recorder()
    task = task_manifest()
    task_run_id = uuid4()

    with pytest.raises(OutcomeRecordingError, match="different task"):
        await recorder.record(
            outcome=coding_outcome(task_run_id=task_run_id),
            task=task,
            evidence=hidden_evidence(task=task, task_run_id=task_run_id),
            candidate=candidate_manifest(task_manifest()),
            correlation_id=task_run_id,
        )


@pytest.mark.asyncio
async def test_a_run_identity_that_describes_another_run_is_refused() -> None:
    """Resume trusts this key, so a wrong one is worse than a missing one."""
    recorder, _, _ = _recorder()
    task = task_manifest()
    task_run_id = uuid4()
    mismatched = RealityRunIdentity(
        task_id=task.task_id,
        task_manifest_hash=task.content_hash,
        run_kind=RealityRunKind.CANDIDATE,
        candidate_id=uuid4(),
        strategy=RealityCandidateStrategy.CORRECT_NARROW,
        source=RealityCandidateSource.CURATED,
        generator_profile_id="reality.tasks",
        verifier_profile_hash=digest("profile"),
        campaign_version=1,
    )

    with pytest.raises(OutcomeRecordingError, match="different kind of run"):
        await recorder.record(
            outcome=coding_outcome(task_run_id=task_run_id),
            task=task,
            evidence=hidden_evidence(task=task, task_run_id=task_run_id),
            candidate=None,
            correlation_id=task_run_id,
            run_identity=mismatched,
        )


@pytest.mark.asyncio
async def test_a_candidate_run_binds_its_strategy_and_provider_output() -> None:
    recorder, _, _ = _recorder()
    task = task_manifest()
    task_run_id = uuid4()
    provider_output_id = uuid4()
    candidate = candidate_manifest(
        task,
        RealityCandidateStrategy.PROVIDER_PROPOSED,
        source=RealityCandidateSource.OPENROUTER,
        provider_id="openrouter",
        provider_output_id=provider_output_id,
    )

    recorded = await recorder.record(
        outcome=coding_outcome(task_run_id=task_run_id, status=CodingOutcomeStatus.FAILED),
        task=task,
        evidence=hidden_evidence(
            task=task, task_run_id=task_run_id, status=HiddenVerificationStatus.FAILED
        ),
        candidate=candidate,
        correlation_id=task_run_id,
    )

    assert recorded.reference.strategy is RealityCandidateStrategy.PROVIDER_PROPOSED
    assert recorded.reference.provider_output_id == provider_output_id
    assert recorded.reference.hidden_verification_passed is False
