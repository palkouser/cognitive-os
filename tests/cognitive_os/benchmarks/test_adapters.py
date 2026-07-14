import json
from pathlib import Path

import pytest

from cognitive_os.benchmarks.cases import load_manifest
from cognitive_os.benchmarks.inspect_adapter import case_to_sample, export_task
from cognitive_os.benchmarks.swebench_adapter import import_jsonl, import_record


def record() -> dict[str, object]:
    return {
        "instance_id": "project__repo-1",
        "repo": "project/repo",
        "base_commit": "abcdef1234567",  # pragma: allowlist secret
        "problem_statement": "Fix the bounded test fixture.",
        "patch": "protected gold patch",
        "FAIL_TO_PASS": ["tests/test_fix.py::test_fix"],
        "PASS_TO_PASS": [],
        "version": "1",
    }


def test_swebench_import_protects_gold_and_retains_provenance() -> None:
    case = import_record(record(), license_name="MIT")
    assert "patch" not in case.problem_request
    assert case.configuration["protected_gold_patch_hash"]
    assert case.source.endswith("@abcdef1234567")


@pytest.mark.parametrize(
    "updates", [{"repo": "../escape"}, {"base_commit": "main"}, {"instance_id": "../bad"}]
)
def test_swebench_rejects_malicious_metadata(updates: dict[str, object]) -> None:
    value = record() | updates
    with pytest.raises(ValueError):
        import_record(value, license_name="MIT")


def test_swebench_jsonl_duplicate_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "cases.jsonl"
    line = json.dumps(record())
    path.write_text(f"{line}\n{line}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        import_jsonl(path, license_name="MIT")


def test_inspect_export_is_deterministic_and_does_not_mutate_source(tmp_path: Path) -> None:
    manifest = load_manifest(Path("benchmarks/manifests/sprint7-ci.yaml"))
    before = manifest.model_dump_json()
    path = export_task(manifest.cases, tmp_path)
    assert path.exists()
    assert case_to_sample(manifest.cases[0])["id"] == manifest.cases[0].case_id
    assert manifest.model_dump_json() == before
