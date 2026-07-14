"""Sequential bounded native benchmark runner."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from hashlib import sha256
from uuid import UUID, uuid4

from cognitive_os.application.ports.artifact_store import ArtifactStorePort
from cognitive_os.domain.benchmarks import (
    BenchmarkCase,
    BenchmarkCaseResult,
    BenchmarkCaseStatus,
    BenchmarkManifest,
    BenchmarkRun,
    BenchmarkRunStatus,
)
from cognitive_os.domain.common import ErrorInfo, utc_now
from cognitive_os.events.benchmark_event_service import BenchmarkEventService
from cognitive_os.events.benchmark_events import (
    BenchmarkCaseCompleted,
    BenchmarkCaseFailed,
    BenchmarkCaseStarted,
    BenchmarkRunCompleted,
    BenchmarkRunStarted,
)

from .metrics import aggregate_metrics
from .reporting import render_json

CaseExecutor = Callable[[BenchmarkCase], Awaitable[BenchmarkCaseResult]]


class BenchmarkRunner:
    def __init__(
        self,
        case_executor: CaseExecutor,
        *,
        events: BenchmarkEventService | None = None,
        artifacts: ArtifactStorePort | None = None,
        git_commit: str = "unknown",
        tool_registry_hash: str = "0" * 64,
        verifier_registry_hash: str = "0" * 64,
        sandbox_image_digest: str = "unavailable",
    ) -> None:
        self._execute_case = case_executor
        self._events = events
        self._artifacts = artifacts
        self._git_commit = git_commit
        self._tool_registry_hash = tool_registry_hash
        self._verifier_registry_hash = verifier_registry_hash
        self._sandbox_image_digest = sandbox_image_digest
        self._runs: dict[UUID, BenchmarkRun] = {}
        self._cancelled: set[UUID] = set()

    async def run_manifest(
        self, manifest: BenchmarkManifest, *, random_seed: int = 0
    ) -> BenchmarkRun:
        run_id, started = uuid4(), utc_now()
        start_event_id = None
        if self._events:
            start_event_id = await self._events.append(
                run_id,
                BenchmarkRunStarted(
                    run_id=run_id,
                    benchmark_id=manifest.benchmark_id,
                    manifest_hash=manifest.manifest_hash,
                    random_seed=random_seed,
                    started_at=started,
                ),
            )
        results: list[BenchmarkCaseResult] = []
        for case in manifest.cases:
            if run_id in self._cancelled:
                break
            case_event_id = None
            if self._events:
                case_event_id = await self._events.append(
                    run_id,
                    BenchmarkCaseStarted(run_id=run_id, case_id=case.case_id, started_at=utc_now()),
                    causation_event_id=start_event_id,
                )
            try:
                result = await self._execute_case(case)
                results.append(result)
                if self._events:
                    await self._events.append(
                        run_id,
                        BenchmarkCaseCompleted(run_id=run_id, result=result),
                        causation_event_id=case_event_id,
                    )
            except Exception as caught:
                now = utc_now()
                error = ErrorInfo(
                    code="benchmark_case_error",
                    message="benchmark case execution failed",
                    error_type=type(caught).__name__,
                )
                result = BenchmarkCaseResult(
                    case_id=case.case_id,
                    status=BenchmarkCaseStatus.ERROR,
                    started_at=now,
                    finished_at=now,
                    error=error,
                )
                results.append(result)
                if self._events:
                    await self._events.append(
                        run_id,
                        BenchmarkCaseFailed(
                            run_id=run_id, case_id=case.case_id, error=error, finished_at=now
                        ),
                        causation_event_id=case_event_id,
                    )
        finished = utc_now()
        status = (
            BenchmarkRunStatus.CANCELLED
            if run_id in self._cancelled
            else BenchmarkRunStatus.COMPLETED
        )
        configuration_hash = sha256(
            json.dumps(manifest.default_configuration, sort_keys=True).encode()
        ).hexdigest()
        run = BenchmarkRun(
            run_id=run_id,
            benchmark_id=manifest.benchmark_id,
            benchmark_version=manifest.version,
            manifest_hash=manifest.manifest_hash,
            git_commit=self._git_commit,
            configuration_hash=configuration_hash,
            provider_configuration_hash="0" * 64,
            tool_registry_hash=self._tool_registry_hash,
            verifier_registry_hash=self._verifier_registry_hash,
            sandbox_image_digest=self._sandbox_image_digest,
            random_seed=random_seed,
            status=status,
            started_at=started,
            finished_at=finished,
            case_results=tuple(results),
            aggregate_metrics=aggregate_metrics(tuple(results)),
        )
        if self._artifacts:
            artifact = await self._artifacts.put_bytes(
                render_json(run), media_type="application/json"
            )
            run = run.model_copy(update={"report_artifact": artifact})
        self._runs[run_id] = run
        if self._events and status is BenchmarkRunStatus.COMPLETED:
            await self._events.append(
                run_id,
                BenchmarkRunCompleted(
                    run_id=run_id,
                    report_hash=sha256(render_json(run)).hexdigest(),
                    finished_at=finished,
                ),
                causation_event_id=start_event_id,
            )
        return run

    async def run_case(self, case: BenchmarkCase) -> BenchmarkCaseResult:
        return await self._execute_case(case)

    async def cancel_run(self, run_id: UUID) -> None:
        self._cancelled.add(run_id)

    async def inspect_run(self, run_id: UUID) -> BenchmarkRun | None:
        return self._runs.get(run_id)
