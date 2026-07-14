from pathlib import Path

import pytest

from cognitive_os.benchmarks.cases import load_manifest


@pytest.mark.contract
def test_benchmark_contracts_and_ci_manifest_are_stable() -> None:
    root = Path("schemas/v1/domain")
    assert (root / "benchmark-case.schema.json").is_file()
    assert (root / "benchmark-manifest.schema.json").is_file()
    manifest = load_manifest(Path("benchmarks/manifests/sprint7-ci.yaml"))
    assert len(manifest.cases) == 4
    assert len(manifest.manifest_hash) == 64
