"""Benchmark execution application boundary."""

from typing import Protocol
from uuid import UUID

from cognitive_os.domain.benchmarks import (
    BenchmarkCase,
    BenchmarkCaseResult,
    BenchmarkManifest,
    BenchmarkRun,
)


class BenchmarkRunnerPort(Protocol):
    async def run_manifest(
        self, manifest: BenchmarkManifest, *, random_seed: int = 0
    ) -> BenchmarkRun: ...
    async def run_case(self, case: BenchmarkCase) -> BenchmarkCaseResult: ...
    async def cancel_run(self, run_id: UUID) -> None: ...
    async def inspect_run(self, run_id: UUID) -> BenchmarkRun | None: ...
