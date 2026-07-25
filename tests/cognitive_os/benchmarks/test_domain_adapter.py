"""Sprint 20 cross-domain benchmark manifests execute offline and deterministically."""

from pathlib import Path

import pytest

from cognitive_os.benchmarks.cases import load_manifest
from cognitive_os.benchmarks.domain_adapter import domain_benchmark_case
from cognitive_os.domain.benchmarks import BenchmarkDomain


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("manifest_path", "expected_cases"),
    (
        ("benchmarks/manifests/sprint20-domain-ci.yaml", 24),
        ("benchmarks/manifests/sprint20-domain-seed.yaml", 120),
    ),
)
async def test_domain_manifests_pass_their_expected_dispositions(
    manifest_path: str, expected_cases: int
) -> None:
    manifest = load_manifest(Path(manifest_path))
    results = [await domain_benchmark_case(case) for case in manifest.cases]
    assert len(results) == expected_cases
    failed = [item.case_id for item in results if item.status.value != "passed"]
    assert not failed, failed
    # The mandatory path stays offline, credential-free, and CPU-only.
    for item in results:
        assert item.metrics["provider_calls"] == 0
        assert item.metrics["network_calls"] == 0
        assert item.metrics["credential_reads"] == 0
        assert item.metrics["gpu_calls"] == 0
        assert item.metrics["optional_extras_required"] == 0
        assert item.metrics["runtime_release_operations"] == 0


@pytest.mark.asyncio
async def test_ci_manifest_is_balanced_across_domains_and_governance() -> None:
    manifest = load_manifest(Path("benchmarks/manifests/sprint20-domain-ci.yaml"))
    counts: dict[BenchmarkDomain, int] = {}
    for case in manifest.cases:
        counts[case.domain] = counts.get(case.domain, 0) + 1
    assert counts[BenchmarkDomain.MATHEMATICS] == 6
    assert counts[BenchmarkDomain.PHYSICS] == 6
    assert counts[BenchmarkDomain.LOGIC] == 6
    assert counts[BenchmarkDomain.GENERIC] == 6


@pytest.mark.asyncio
async def test_seed_manifest_meets_the_minimum_per_group() -> None:
    manifest = load_manifest(Path("benchmarks/manifests/sprint20-domain-seed.yaml"))
    counts: dict[BenchmarkDomain, int] = {}
    for case in manifest.cases:
        counts[case.domain] = counts.get(case.domain, 0) + 1
    for domain in (
        BenchmarkDomain.MATHEMATICS,
        BenchmarkDomain.PHYSICS,
        BenchmarkDomain.LOGIC,
        BenchmarkDomain.GENERIC,
    ):
        assert counts[domain] >= 30, (domain, counts)


@pytest.mark.asyncio
async def test_manifest_results_are_reproducible() -> None:
    manifest = load_manifest(Path("benchmarks/manifests/sprint20-domain-ci.yaml"))
    first = [await domain_benchmark_case(case) for case in manifest.cases]
    second = [await domain_benchmark_case(case) for case in manifest.cases]
    assert [item.case_id for item in first] == [item.case_id for item in second]
    assert [item.status for item in first] == [item.status for item in second]
    for left, right in zip(first, second, strict=True):
        assert left.metrics["expected_outcome_matched"] == right.metrics["expected_outcome_matched"]
