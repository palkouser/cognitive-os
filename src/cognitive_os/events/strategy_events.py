"""Bounded Strategy Evolution Graph lifecycle evidence."""

from uuid import UUID

from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, UtcDatetime
from cognitive_os.domain.strategies import (
    StrategyExecutionStatus,
    StrategyOutcomeStatus,
    StrategySelectionStatus,
    StrategyStatus,
)

from .base import EventPayload


class StrategyCreated(EventPayload):
    event_type = "strategy.created"
    strategy_id: UUID
    revision: int
    status: StrategyStatus
    content_hash: Sha256Hex
    occurred_at: UtcDatetime


class StrategyRevisionAppended(StrategyCreated):
    event_type = "strategy.revision_appended"
    previous_revision: int


class StrategyStatusChanged(EventPayload):
    strategy_id: UUID
    revision: int
    previous_status: StrategyStatus
    status: StrategyStatus
    reason_code: NonEmptyStr
    occurred_at: UtcDatetime


class StrategyStaged(StrategyStatusChanged):
    event_type = "strategy.staged"


class StrategyVerified(StrategyStatusChanged):
    event_type = "strategy.verified"


class StrategyDeprecated(StrategyStatusChanged):
    event_type = "strategy.deprecated"


class StrategySuperseded(StrategyStatusChanged):
    event_type = "strategy.superseded"


class StrategyRetracted(StrategyStatusChanged):
    event_type = "strategy.retracted"


class StrategySelected(EventPayload):
    event_type = "strategy.selected"
    selection_id: UUID
    task_run_id: UUID
    strategy_id: UUID | None
    revision: int | None
    status: StrategySelectionStatus
    decision_hash: Sha256Hex
    occurred_at: UtcDatetime


class StrategyExecutionStarted(EventPayload):
    event_type = "strategy.execution_started"
    execution_id: UUID
    selection_id: UUID
    strategy_id: UUID
    revision: int
    task_run_id: UUID
    plan_hash: Sha256Hex
    occurred_at: UtcDatetime


class StrategyExecutionCompleted(EventPayload):
    event_type = "strategy.execution_completed"
    execution_id: UUID
    strategy_id: UUID
    revision: int
    task_run_id: UUID
    status: StrategyExecutionStatus
    outcome_status: StrategyOutcomeStatus
    outcome_hash: Sha256Hex
    occurred_at: UtcDatetime


class StrategyExecutionFailed(StrategyExecutionCompleted):
    event_type = "strategy.execution_failed"
    reason_code: NonEmptyStr


class StrategyStatisticsRebuilt(EventPayload):
    event_type = "strategy.statistics_rebuilt"
    strategy_id: UUID
    revision: int
    cohort_id: NonEmptyStr
    projection_revision: int
    projection_hash: Sha256Hex
    occurred_at: UtcDatetime


STRATEGY_EVENT_MODELS: tuple[type[EventPayload], ...] = (
    StrategyCreated,
    StrategyRevisionAppended,
    StrategyStaged,
    StrategyVerified,
    StrategyDeprecated,
    StrategySuperseded,
    StrategyRetracted,
    StrategySelected,
    StrategyExecutionStarted,
    StrategyExecutionCompleted,
    StrategyExecutionFailed,
    StrategyStatisticsRebuilt,
)
