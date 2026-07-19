"""Bounded procedural skill lifecycle event payloads."""

from uuid import UUID

from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, UtcDatetime
from cognitive_os.domain.skills import SkillExecutionStatus, SkillStatus

from .base import EventPayload


class SkillCreated(EventPayload):
    event_type = "skill.created"
    skill_id: UUID
    revision: int
    status: SkillStatus
    package_hash: Sha256Hex
    occurred_at: UtcDatetime


class SkillRevisionAppended(SkillCreated):
    event_type = "skill.revision_appended"
    previous_revision: int


class SkillStatusChanged(EventPayload):
    skill_id: UUID
    revision: int
    previous_status: SkillStatus
    status: SkillStatus
    reason_code: NonEmptyStr
    occurred_at: UtcDatetime


class SkillStaged(SkillStatusChanged):
    event_type = "skill.staged"


class SkillVerified(SkillStatusChanged):
    event_type = "skill.verified"


class SkillDeprecated(SkillStatusChanged):
    event_type = "skill.deprecated"


class SkillSuperseded(SkillStatusChanged):
    event_type = "skill.superseded"


class SkillRetracted(SkillStatusChanged):
    event_type = "skill.retracted"


class SkillExecutionStarted(EventPayload):
    event_type = "skill.execution_started"
    execution_id: UUID
    skill_id: UUID
    revision: int
    task_run_id: UUID
    package_hash: Sha256Hex
    occurred_at: UtcDatetime


class SkillExecutionCompleted(EventPayload):
    event_type = "skill.execution_completed"
    execution_id: UUID
    skill_id: UUID
    revision: int
    task_run_id: UUID
    status: SkillExecutionStatus
    result_hash: Sha256Hex
    occurred_at: UtcDatetime


class SkillExecutionFailed(SkillExecutionCompleted):
    event_type = "skill.execution_failed"
    reason_code: NonEmptyStr


SKILL_EVENT_MODELS: tuple[type[EventPayload], ...] = (
    SkillCreated,
    SkillRevisionAppended,
    SkillStaged,
    SkillVerified,
    SkillDeprecated,
    SkillSuperseded,
    SkillRetracted,
    SkillExecutionStarted,
    SkillExecutionCompleted,
    SkillExecutionFailed,
)
