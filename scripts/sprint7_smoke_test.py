"""Credential-free Sprint 7 verifier, acceptance, and benchmark smoke test."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from cognitive_os.application.services.acceptance_service import AcceptancePolicyService
from cognitive_os.benchmarks.cases import load_manifest
from cognitive_os.benchmarks.runner import BenchmarkRunner
from cognitive_os.domain.acceptance import (
    AcceptanceDecisionType,
    AcceptancePolicy,
    VerifierRequirement,
)
from cognitive_os.domain.benchmarks import BenchmarkCase, BenchmarkCaseResult, BenchmarkCaseStatus
from cognitive_os.domain.enums import VerifierStatus
from cognitive_os.domain.verifiers import (
    VerificationRequest,
    VerificationSubject,
    VerificationSubjectType,
)
from cognitive_os.verification.coding import FilePolicyVerifier
from cognitive_os.verification.generic import ExactValueVerifier
from cognitive_os.verification.logic import SatisfiabilityVerifier
from cognitive_os.verification.mathematics import NumericVerifier
from cognitive_os.verification.physics import UnitConversionVerifier


def request(
    verifier_id: str, subject_type: VerificationSubjectType, value, configuration
) -> VerificationRequest:
    return VerificationRequest(
        verification_id=uuid4(),
        task_run_id=uuid4(),
        criterion_id=uuid4(),
        verifier_id=verifier_id,
        verifier_version="1",
        subject=VerificationSubject(subject_type=subject_type, inline_value=value),
        configuration=configuration,
        requested_at=datetime.now(UTC),
        correlation_id=uuid4(),
    )


async def replay_case(case: BenchmarkCase) -> BenchmarkCaseResult:
    now = datetime.now(UTC)
    return BenchmarkCaseResult(
        case_id=case.case_id, status=BenchmarkCaseStatus.PASSED, started_at=now, finished_at=now
    )


async def run() -> dict[str, object]:
    checks = (
        await ExactValueVerifier().verify(
            request("generic.exact", VerificationSubjectType.STRUCTURED_VALUE, 42, {"expected": 42})
        ),
        await FilePolicyVerifier().verify(
            request(
                "coding.file_policy",
                VerificationSubjectType.STRUCTURED_VALUE,
                {"files": [{"path": "src/example.py", "size_bytes": 10}]},
                {},
            )
        ),
        await NumericVerifier().verify(
            request(
                "mathematics.numeric",
                VerificationSubjectType.MATHEMATICAL_EXPRESSION,
                "3.14",
                {"expected": "3.14"},
            )
        ),
        await SatisfiabilityVerifier().verify(
            request(
                "logic.satisfiable",
                VerificationSubjectType.LOGICAL_PROBLEM,
                {"operator": "variable", "sort": "bool", "name": "safe"},
                {},
            )
        ),
        await UnitConversionVerifier().verify(
            request(
                "physics.unit_conversion",
                VerificationSubjectType.PHYSICAL_QUANTITY,
                {"magnitude": "1", "unit": "meter"},
                {"target_unit": "centimeter", "expected_magnitude": "100"},
            )
        ),
    )
    requirements = tuple(
        VerifierRequirement(
            requirement_id=uuid4(),
            verifier_id=result.verifier_id,
            minimum_version="1",
            criterion_ids=(uuid4(),),
            allowed_outcomes=(VerifierStatus.PASSED,),
        )
        for result in checks
    )
    policy = AcceptancePolicy(
        policy_id=uuid4(),
        version="1",
        name="Sprint 7 smoke",
        description="Require all smoke verifier results.",
        requirements=requirements,
        created_at=datetime.now(UTC),
    )
    decision = AcceptancePolicyService().evaluate(policy, uuid4(), checks)
    manifest = load_manifest(Path("benchmarks/manifests/sprint7-ci.yaml"))
    benchmark = await BenchmarkRunner(replay_case, git_commit="smoke").run_manifest(
        manifest, random_seed=7
    )
    return {
        "verifiers": {result.verifier_id: result.status.value for result in checks},
        "acceptance": decision.decision.value,
        "benchmark_cases": len(benchmark.case_results),
        "benchmark_pass_rate": benchmark.aggregate_metrics["case_pass_rate"],
        "passed": all(result.status is VerifierStatus.PASSED for result in checks)
        and decision.decision is AcceptanceDecisionType.ACCEPTED
        and benchmark.aggregate_metrics["case_pass_rate"] == 1,
    }


def main() -> int:
    result = asyncio.run(run())
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
