"""Benchmark lifecycle event payloads."""

from uuid import UUID

from cognitive_os.domain.benchmarks import BenchmarkCaseResult
from cognitive_os.domain.common import ErrorInfo, NonEmptyStr, Sha256Hex, UtcDatetime

from .base import EventPayload


class BenchmarkRunStarted(EventPayload):
    event_type = "benchmark.run_started"
    run_id: UUID
    benchmark_id: NonEmptyStr
    manifest_hash: Sha256Hex
    random_seed: int
    started_at: UtcDatetime


class BenchmarkCaseStarted(EventPayload):
    event_type = "benchmark.case_started"
    run_id: UUID
    case_id: NonEmptyStr
    started_at: UtcDatetime


class BenchmarkCaseCompleted(EventPayload):
    event_type = "benchmark.case_completed"
    run_id: UUID
    result: BenchmarkCaseResult


class BenchmarkCaseFailed(EventPayload):
    event_type = "benchmark.case_failed"
    run_id: UUID
    case_id: NonEmptyStr
    error: ErrorInfo
    finished_at: UtcDatetime


class BenchmarkRunCompleted(EventPayload):
    event_type = "benchmark.run_completed"
    run_id: UUID
    report_hash: Sha256Hex
    finished_at: UtcDatetime


class BenchmarkRunFailed(EventPayload):
    event_type = "benchmark.run_failed"
    run_id: UUID
    error: ErrorInfo
    finished_at: UtcDatetime


class BenchmarkRunCancelled(EventPayload):
    event_type = "benchmark.run_cancelled"
    run_id: UUID
    reason: NonEmptyStr
    finished_at: UtcDatetime
