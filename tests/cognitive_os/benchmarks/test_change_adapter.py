from pathlib import Path

import pytest

from cognitive_os.benchmarks.cases import load_manifest
from cognitive_os.benchmarks.change_adapter import change_benchmark_case


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("manifest_path", "expected_cases"),
    (
        ("benchmarks/manifests/sprint19-change-ci.yaml", 18),
        ("benchmarks/manifests/sprint19-change-seed.yaml", 72),
    ),
)
async def test_change_manifests_are_deterministic_and_side_effect_free(
    manifest_path: str, expected_cases: int
) -> None:
    manifest = load_manifest(Path(manifest_path))
    results = [await change_benchmark_case(case) for case in manifest.cases]
    assert len(results) == expected_cases
    assert all(item.status.value == "passed" for item in results)
    assert all(item.metrics["active_checkout_mutations"] == 0 for item in results)
    assert all(item.metrics["active_database_writes"] == 0 for item in results)
    assert all(item.metrics["runtime_release_operations"] == 0 for item in results)
