"""Offline SWE-bench-compatible manifest adapter without clone or execution."""

from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

from cognitive_os.domain.acceptance import AcceptancePolicy, VerifierRequirement
from cognitive_os.domain.benchmarks import BenchmarkCase, BenchmarkDomain, BenchmarkResourceBudget
from cognitive_os.domain.common import JsonValue, utc_now
from cognitive_os.domain.enums import VerifierStatus

SAFE_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SAFE_COMMIT = re.compile(r"^[0-9a-fA-F]{7,64}$")


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = [item for item in value.splitlines() if item]
        if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
            return parsed
    raise ValueError("SWE-bench test list is invalid")


def default_swebench_policy() -> AcceptancePolicy:
    criterion_id, requirement_id = uuid4(), uuid4()
    return AcceptancePolicy(
        policy_id=uuid4(),
        version="1",
        name="SWE-bench expected tests",
        description="Require the bounded sandbox pytest verifier.",
        requirements=(
            VerifierRequirement(
                requirement_id=requirement_id,
                verifier_id="coding.pytest",
                minimum_version="1",
                criterion_ids=(criterion_id,),
                allowed_outcomes=(VerifierStatus.PASSED,),
            ),
        ),
        created_at=utc_now(),
    )


def import_record(
    record: dict[str, Any], *, license_name: str, policy: AcceptancePolicy | None = None
) -> BenchmarkCase:
    instance_id = record.get("instance_id") or record.get("instanceid")
    repository = record.get("repo") or record.get("repository")
    commit = record.get("base_commit") or record.get("basecommit")
    if (
        not isinstance(instance_id, str)
        or not instance_id
        or "/" in instance_id
        or ".." in instance_id
    ):
        raise ValueError("SWE-bench instance ID is invalid")
    if (
        not isinstance(repository, str)
        or not SAFE_REPOSITORY.fullmatch(repository)
        or ".." in repository
        or any(part.startswith(".") for part in repository.split("/"))
    ):
        raise ValueError("SWE-bench repository identifier is invalid")
    if not isinstance(commit, str) or not SAFE_COMMIT.fullmatch(commit):
        raise ValueError("SWE-bench base commit is invalid")
    problem = record.get("problem_statement") or record.get("problemstatement")
    if not isinstance(problem, str) or not problem.strip():
        raise ValueError("SWE-bench problem statement is missing")
    fail_to_pass = _string_list(record.get("FAIL_TO_PASS", record.get("fail_to_pass", [])))
    pass_to_pass = _string_list(record.get("PASS_TO_PASS", record.get("pass_to_pass", [])))
    gold_patch = str(record.get("patch", ""))
    protected_hash = sha256(gold_patch.encode()).hexdigest() if gold_patch else None
    return BenchmarkCase(
        case_id=f"swebench.{instance_id}",
        version=str(record.get("version", "1")),
        domain=BenchmarkDomain.CODING,
        title=instance_id,
        description="Imported SWE-bench-compatible coding case metadata.",
        problem_request={
            "repository": repository,
            "base_commit": commit,
            "issue_statement": problem,
            "hints_text": str(record.get("hints_text", "")),
        },
        expected_outputs={
            "fail_to_pass": list[JsonValue](fail_to_pass),
            "pass_to_pass": list[JsonValue](pass_to_pass),
        },
        acceptance_policy=policy or default_swebench_policy(),
        resource_budget=BenchmarkResourceBudget(
            maximum_elapsed_seconds=1800,
            maximum_provider_calls=0,
            maximum_tool_calls=20,
            maximum_artifact_bytes=50_000_000,
        ),
        configuration={"workspace_deferred": True, "protected_gold_patch_hash": protected_hash},
        tags=("swe-bench", "imported"),
        source=f"https://github.com/{repository}@{commit}",
        license=license_name,
    )


def import_jsonl(
    path: Path, *, license_name: str, limit: int | None = None
) -> tuple[BenchmarkCase, ...]:
    cases: list[BenchmarkCase] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            cases.append(import_record(json.loads(line), license_name=license_name))
        if limit is not None and len(cases) >= limit:
            break
    ids = [item.case_id for item in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("SWE-bench import contains duplicate cases")
    return tuple(sorted(cases, key=lambda item: item.case_id))
