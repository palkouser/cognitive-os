from pathlib import Path

import pytest

from cognitive_os.benchmarks.cases import load_manifest
from cognitive_os.benchmarks.runner import BenchmarkRunner
from cognitive_os.domain.benchmarks import BenchmarkCase, BenchmarkCaseResult, BenchmarkCaseStatus
from cognitive_os.domain.common import utc_now


async def mixed_executor(case: BenchmarkCase) -> BenchmarkCaseResult:
    if case.case_id.endswith("numeric"):
        raise RuntimeError("bounded fixture failure")
    now = utc_now()
    return BenchmarkCaseResult(
        case_id=case.case_id, status=BenchmarkCaseStatus.PASSED, started_at=now, finished_at=now
    )


@pytest.mark.asyncio
async def test_one_case_error_does_not_erase_other_case_results() -> None:
    manifest = load_manifest(Path("benchmarks/manifests/sprint7-ci.yaml"))
    run = await BenchmarkRunner(mixed_executor).run_manifest(manifest)
    assert len(run.case_results) == len(manifest.cases)
    assert any(item.status is BenchmarkCaseStatus.ERROR for item in run.case_results)
    assert any(item.status is BenchmarkCaseStatus.PASSED for item in run.case_results)
