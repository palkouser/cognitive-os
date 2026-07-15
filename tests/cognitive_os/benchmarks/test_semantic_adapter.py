from pathlib import Path

import pytest

from cognitive_os.benchmarks.cases import load_manifest
from cognitive_os.benchmarks.runner import BenchmarkRunner
from cognitive_os.benchmarks.semantic_adapter import (
    SemanticBenchmarkAdapter,
    semantic_benchmark_case,
)
from cognitive_os.semantic_memory.repository import InMemorySemanticMemoryRepository


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "manifest_path,case_count",
    [
        (Path("benchmarks/manifests/sprint10-semantic-ci.yaml"), 4),
        (Path("benchmarks/manifests/sprint10-semantic-seed.yaml"), 20),
    ],
)
async def test_semantic_benchmark_executes_all_declared_scenarios(
    manifest_path: Path, case_count: int
) -> None:
    manifest = load_manifest(manifest_path)
    run = await BenchmarkRunner(semantic_benchmark_case, git_commit="semantic-test").run_manifest(
        manifest, random_seed=10
    )
    assert len(run.case_results) == case_count
    assert run.aggregate_metrics["case_pass_rate"] == 1
    assert run.aggregate_metrics["unsupported_promotions"] == 0
    assert run.aggregate_metrics["future_revision_leaks"] == 0
    assert run.aggregate_metrics["scope_leaks"] == 0
    assert run.aggregate_metrics["sensitivity_leaks"] == 0
    assert all(result.metrics["wiki_lineage_completeness"] == 1 for result in run.case_results)


@pytest.mark.asyncio
async def test_semantic_adapter_compares_exact_isolated_entity_projections() -> None:
    manifest = load_manifest(Path("benchmarks/manifests/sprint10-semantic-ci.yaml"))
    adapter = SemanticBenchmarkAdapter(InMemorySemanticMemoryRepository())

    run = await BenchmarkRunner(adapter, git_commit="semantic-projection-test").run_manifest(
        manifest, random_seed=10
    )

    assert len(run.case_results) == 4
    assert all(result.metrics["expected_entities_matched"] == 1 for result in run.case_results)
