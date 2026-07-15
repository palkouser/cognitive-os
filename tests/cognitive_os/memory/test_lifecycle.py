from datetime import UTC, datetime
from uuid import UUID

import pytest

from cognitive_os.domain.memory import (
    EpisodeMemoryContent,
    MemoryCreator,
    MemoryCreatorType,
    MemoryRecord,
    MemoryRevision,
    MemoryScope,
    MemoryScopeType,
    MemorySensitivity,
    MemoryStatus,
    MemoryTransitionReason,
    MemoryType,
    memory_revision_hash,
)
from cognitive_os.events.memory_events import MemoryItemCreated, MemoryPromoted
from cognitive_os.memory.revisions import MemoryStreamReducer, can_transition_memory

NOW = datetime(2026, 7, 15, tzinfo=UTC)
MEMORY_ID = UUID("00000000-0000-0000-0000-000000000931")
ACTOR = MemoryCreator(creator_type=MemoryCreatorType.OPERATOR, creator_id="operator")
CONTENT = EpisodeMemoryContent(
    task_run_id=UUID("00000000-0000-0000-0000-000000000932"),
    title="Accepted task",
    problem_summary="Bounded task",
    repository_identity="a" * 64,
    base_commit="b" * 40,
    outcome="accepted",
    patch_attempt_count=1,
    repair_count=0,
    verifier_summary="passed",
    trajectory_hash="c" * 64,
)


def revision(number: int, status: MemoryStatus) -> MemoryRevision:
    return MemoryRevision(
        memory_id=MEMORY_ID,
        revision=number,
        previous_revision=None if number == 1 else number - 1,
        content=CONTENT,
        content_hash=memory_revision_hash(
            memory_id=MEMORY_ID,
            revision=number,
            content=CONTENT,
            status=status,
            confidence=1.0,
            salience=0.5,
            sensitivity=MemorySensitivity.INTERNAL,
        ),
        status=status,
        confidence=1.0,
        salience=0.5,
        sensitivity=MemorySensitivity.INTERNAL,
        reason=(
            MemoryTransitionReason.CREATED
            if number == 1
            else MemoryTransitionReason.AUTHORITATIVE_EVIDENCE_VERIFIED
        ),
        created_at=NOW,
        created_by=ACTOR,
    )


def creation() -> MemoryItemCreated:
    first = revision(1, MemoryStatus.CANDIDATE)
    return MemoryItemCreated(
        record=MemoryRecord(
            memory_id=MEMORY_ID,
            memory_type=MemoryType.EPISODE,
            scope=MemoryScope(scope_type=MemoryScopeType.TASK, scope_id="task-1"),
            status=MemoryStatus.CANDIDATE,
            current_revision=1,
            title="Accepted task",
            created_at=NOW,
            created_by=ACTOR,
        ),
        revision=first,
    )


def test_replay_reconstructs_revision_and_status() -> None:
    second = revision(2, MemoryStatus.VERIFIED)
    promoted = MemoryPromoted(
        memory_id=MEMORY_ID,
        expected_revision=1,
        revision=second,
        reason="accepted authoritative evidence",
        transitioned_at=NOW,
    )
    state = MemoryStreamReducer().reduce((creation(), promoted))
    assert state.current_revision == 2
    assert state.status is MemoryStatus.VERIFIED
    assert state.revision_hashes == (
        creation().revision.content_hash,
        second.content_hash,
    )


def test_replay_rejects_gap_duplicate_and_illegal_transition() -> None:
    with pytest.raises(ValueError, match="revision mismatch"):
        MemoryStreamReducer().reduce(
            (
                creation(),
                MemoryPromoted(
                    memory_id=MEMORY_ID,
                    expected_revision=2,
                    revision=revision(2, MemoryStatus.VERIFIED),
                    reason="invalid expected revision",
                    transitioned_at=NOW,
                ),
            )
        )
    assert not can_transition_memory(MemoryStatus.RETRACTED, MemoryStatus.VERIFIED)
