import json
from pathlib import Path

import pytest

from cognitive_os.benchmarks.cases import load_manifest
from cognitive_os.benchmarks.datasets import validate_archive_members
from cognitive_os.benchmarks.registry import BenchmarkRegistry
from cognitive_os.benchmarks.reporting import compare_runs, render_json
from cognitive_os.benchmarks.runner import BenchmarkRunner
from cognitive_os.domain.benchmarks import BenchmarkCase, BenchmarkCaseResult, BenchmarkCaseStatus
from cognitive_os.domain.common import utc_now


async def execute(case: BenchmarkCase) -> BenchmarkCaseResult:
    now = utc_now()
    if case.case_id.endswith("error"):
        raise RuntimeError("fixture error")
    return BenchmarkCaseResult(
        case_id=case.case_id, status=BenchmarkCaseStatus.PASSED, started_at=now, finished_at=now
    )


def test_seed_manifest_contains_56_deterministic_cases() -> None:
    left = load_manifest(Path("benchmarks/manifests/sprint7-seed.yaml"))
    right = load_manifest(Path("benchmarks/manifests/sprint7-seed.yaml"))
    assert len(left.cases) == 56
    assert left.manifest_hash == right.manifest_hash
    assert [item.case_id for item in left.cases] == sorted(item.case_id for item in left.cases)


def test_registry_rejects_duplicates_and_freezes() -> None:
    manifest = load_manifest(Path("benchmarks/manifests/sprint7-ci.yaml"))
    registry = BenchmarkRegistry()
    registry.register_manifest(manifest)
    with pytest.raises(Exception, match="duplicate"):
        registry.register_manifest(manifest)
    registry.freeze()
    assert len(registry.snapshot()) == 64


def test_archive_path_traversal_is_rejected() -> None:
    with pytest.raises(ValueError, match="escapes"):
        validate_archive_members(("safe/file", "../escape"))


@pytest.mark.asyncio
async def test_runner_is_sequential_and_report_is_deterministic() -> None:
    manifest = load_manifest(Path("benchmarks/manifests/sprint7-ci.yaml"))
    run = await BenchmarkRunner(execute, git_commit="abc123").run_manifest(manifest, random_seed=7)
    assert run.status.value == "completed"
    assert run.aggregate_metrics["case_pass_rate"] == 1
    assert json.loads(render_json(run))["random_seed"] == 7
    comparison = compare_runs(run, run)
    assert comparison["newly_failing"] == []
