"""Bounded append-only lifecycle evidence for weakness mining."""

from uuid import UUID

from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, UtcDatetime

from .base import EventPayload


class WeaknessMiningStarted(EventPayload):
    event_type = "weakness.mining_started"
    mining_run_id: UUID
    request_hash: Sha256Hex
    occurred_at: UtcDatetime


class WeaknessMiningCompleted(EventPayload):
    event_type = "weakness.mining_completed"
    mining_run_id: UUID
    manifest_hash: Sha256Hex
    occurred_at: UtcDatetime


class WeaknessMiningFailed(EventPayload):
    event_type = "weakness.mining_failed"
    mining_run_id: UUID
    failure_code: NonEmptyStr
    occurred_at: UtcDatetime


class WeaknessSignalRecorded(EventPayload):
    event_type = "weakness.signal_recorded"
    mining_run_id: UUID
    signal_id: UUID
    signal_hash: Sha256Hex
    occurred_at: UtcDatetime


class WeaknessClusterCreated(EventPayload):
    event_type = "weakness.cluster_created"
    cluster_id: UUID
    cluster_hash: Sha256Hex
    occurred_at: UtcDatetime


class WeaknessClusterRebuilt(EventPayload):
    event_type = "weakness.cluster_rebuilt"
    snapshot_id: UUID
    snapshot_hash: Sha256Hex
    occurred_at: UtcDatetime


class WeaknessCreated(EventPayload):
    event_type = "weakness.created"
    weakness_id: UUID
    revision_hash: Sha256Hex
    occurred_at: UtcDatetime


class WeaknessRevisionAppended(EventPayload):
    event_type = "weakness.revision_appended"
    weakness_id: UUID
    revision: int
    revision_hash: Sha256Hex
    occurred_at: UtcDatetime


class WeaknessConfirmed(EventPayload):
    event_type = "weakness.confirmed"
    weakness_id: UUID
    revision: int
    approval_reference: NonEmptyStr | None = None
    occurred_at: UtcDatetime


class WeaknessMonitoringStarted(EventPayload):
    event_type = "weakness.monitoring_started"
    weakness_id: UUID
    revision: int
    occurred_at: UtcDatetime


class WeaknessResolved(EventPayload):
    event_type = "weakness.resolved"
    weakness_id: UUID
    revision: int
    occurred_at: UtcDatetime


class WeaknessSuperseded(EventPayload):
    event_type = "weakness.superseded"
    weakness_id: UUID
    successor_weakness_id: UUID
    occurred_at: UtcDatetime


class WeaknessRetracted(EventPayload):
    event_type = "weakness.retracted"
    weakness_id: UUID
    revision: int
    reason_code: NonEmptyStr
    occurred_at: UtcDatetime


class WeaknessQueued(EventPayload):
    event_type = "weakness.queued"
    weakness_id: UUID
    revision: int
    queue_entry_id: UUID
    queue_entry_hash: Sha256Hex
    occurred_at: UtcDatetime


WEAKNESS_EVENT_MODELS: tuple[type[EventPayload], ...] = (
    WeaknessMiningStarted,
    WeaknessMiningCompleted,
    WeaknessMiningFailed,
    WeaknessSignalRecorded,
    WeaknessClusterCreated,
    WeaknessClusterRebuilt,
    WeaknessCreated,
    WeaknessRevisionAppended,
    WeaknessConfirmed,
    WeaknessMonitoringStarted,
    WeaknessResolved,
    WeaknessSuperseded,
    WeaknessRetracted,
    WeaknessQueued,
)
