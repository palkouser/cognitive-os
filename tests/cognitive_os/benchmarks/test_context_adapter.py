from pathlib import Path

import pytest

from cognitive_os.benchmarks.cases import load_manifest
from cognitive_os.benchmarks.context_adapter import context_benchmark_case
from cognitive_os.domain.benchmarks import BenchmarkCaseStatus


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "manifest_path,expected_count",
    (
        ("benchmarks/manifests/sprint11-context-ci.yaml", 6),
        ("benchmarks/manifests/sprint11-context-seed.yaml", 32),
    ),
)
async def test_context_benchmark_manifests_match_exact_fixture(
    manifest_path: str, expected_count: int
) -> None:
    manifest = load_manifest(Path(manifest_path))
    results = tuple([await context_benchmark_case(case) for case in manifest.cases])
    assert len(results) == expected_count
    assert all(item.status is BenchmarkCaseStatus.PASSED for item in results)
    assert all(item.metrics["scope_leaks"] == 0 for item in results)
    assert all(item.metrics["sensitivity_leaks"] == 0 for item in results)
    assert all(item.metrics["unsafe_content_inclusions"] == 0 for item in results)


def test_context_metrics_handle_empty_denominators() -> None:
    from cognitive_os.benchmarks.context_adapter import context_quality_metrics

    metrics = context_quality_metrics(relevant=set(), selected=(), ranked=())
    assert metrics["recall_at_k"] == 1
    assert metrics["precision_at_k"] == 1
    assert metrics["ndcg"] == 1
