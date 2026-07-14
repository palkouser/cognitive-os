"""Application facade for native benchmark execution."""

from cognitive_os.benchmarks.runner import BenchmarkRunner
from cognitive_os.domain.benchmarks import BenchmarkManifest, BenchmarkRun


class BenchmarkService:
    def __init__(self, runner: BenchmarkRunner) -> None:
        self._runner = runner

    async def run(self, manifest: BenchmarkManifest, *, seed: int = 0) -> BenchmarkRun:
        return await self._runner.run_manifest(manifest, random_seed=seed)
