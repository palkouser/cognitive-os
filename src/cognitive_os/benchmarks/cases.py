"""Safe tracked YAML benchmark case and manifest loading."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import yaml

from cognitive_os.domain.acceptance import AcceptancePolicy, VerifierRequirement
from cognitive_os.domain.benchmarks import (
    BenchmarkCase,
    BenchmarkDomain,
    BenchmarkManifest,
    BenchmarkResourceBudget,
)
from cognitive_os.domain.enums import VerifierStatus


def load_case(path: Path) -> BenchmarkCase:
    return BenchmarkCase.model_validate(_load_yaml(path))


def load_manifest(path: Path) -> BenchmarkManifest:
    value = _load_yaml(path)
    if "case_matrix" in value:
        value = _expand_case_matrix(value)
    return BenchmarkManifest.model_validate(value)


def _expand_case_matrix(value: dict[str, Any]) -> dict[str, Any]:
    matrix = value.pop("case_matrix")
    if not isinstance(matrix, dict):
        raise ValueError("benchmark case_matrix must be an object")
    cases = []
    for domain_name, entries in sorted(matrix.items()):
        if not isinstance(entries, list):
            raise ValueError("benchmark case matrix entries must be lists")
        domain = BenchmarkDomain(domain_name)
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
                raise ValueError("benchmark matrix case requires an ID")
            case_id = entry["id"]
            criterion_id = uuid5(NAMESPACE_URL, f"{case_id}:criterion")
            policy = AcceptancePolicy(
                policy_id=uuid5(NAMESPACE_URL, f"{case_id}:policy"),
                version="1",
                name=f"{case_id} expected outcome policy",
                description="Deterministic local seed benchmark expectation.",
                requirements=(
                    VerifierRequirement(
                        requirement_id=uuid5(NAMESPACE_URL, f"{case_id}:requirement"),
                        verifier_id=str(entry.get("verifier", "generic.exact")),
                        minimum_version="1",
                        criterion_ids=(criterion_id,),
                        allowed_outcomes=(VerifierStatus.PASSED,),
                    ),
                ),
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
            cases.append(
                BenchmarkCase(
                    case_id=case_id,
                    version="1",
                    domain=domain,
                    title=case_id.replace(".", " ").title(),
                    description=f"Bounded deterministic {value.get('benchmark_id')} case.",
                    problem_request={"scenario": str(entry.get("scenario", case_id))},
                    expected_outputs={"status": str(entry.get("expected", "passed"))},
                    acceptance_policy=policy,
                    resource_budget=BenchmarkResourceBudget(
                        maximum_elapsed_seconds=30,
                        maximum_tool_calls=1 if domain is BenchmarkDomain.CODING else 0,
                        maximum_artifact_bytes=1_048_576,
                    ),
                    configuration={"fixture": str(entry.get("fixture", "local"))},
                    tags=(str(value.get("benchmark_id")), domain.value),
                    source=str(value.get("source", "Cognitive OS local benchmark suite")),
                    license="Apache-2.0",
                ).model_dump(mode="json")
            )
    value["cases"] = sorted(cases, key=lambda item: item["case_id"])
    return value


def _load_yaml(path: Path) -> dict[str, Any]:
    if path.is_symlink() or path.suffix not in {".yaml", ".yml"}:
        raise ValueError("benchmark definition must be a regular YAML file")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("benchmark YAML root must be an object")
    return value
