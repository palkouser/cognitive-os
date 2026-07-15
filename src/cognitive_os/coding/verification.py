"""Capability-backed full Python Coding Agent verifier bundle."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from cognitive_os.application.services.acceptance_service import AcceptancePolicyService
from cognitive_os.application.services.verification_service import VerificationService
from cognitive_os.domain.acceptance import AcceptanceDecision, AcceptancePolicy, VerifierRequirement
from cognitive_os.domain.coding import CodingLimits, CodingVerificationSummary
from cognitive_os.domain.common import JsonValue, utc_now
from cognitive_os.domain.enums import VerifierStatus
from cognitive_os.domain.verifiers import (
    VerificationBundle,
    VerificationRequest,
    VerificationSubject,
    VerificationSubjectType,
)
from cognitive_os.verification.registry import VerifierRegistry


@dataclass(frozen=True)
class CodingVerificationOutcome:
    summary: CodingVerificationSummary
    decision: AcceptanceDecision


_REQUIRED_VERIFIERS = (
    "coding.pytest",
    "coding.ruff",
    "coding.mypy",
    "coding.import",
    "coding.file_policy",
    "coding.diff_policy",
    "coding.dependency_policy",
    "coding.workspace_integrity",
)


class CodingVerifierBundleFactory:
    def __init__(
        self,
        registry: VerifierRegistry,
        verification: VerificationService,
        acceptance: AcceptancePolicyService,
        limits: CodingLimits,
    ) -> None:
        self.registry = registry
        self.verification = verification
        self.acceptance = acceptance
        self.limits = limits

    def policy(self) -> AcceptancePolicy:
        requirements = tuple(
            VerifierRequirement(
                requirement_id=uuid5(NAMESPACE_URL, f"cognitive-os:sprint8:{verifier_id}"),
                verifier_id=verifier_id,
                minimum_version="1",
                criterion_ids=(uuid5(NAMESPACE_URL, f"criterion:{verifier_id}"),),
                required=True,
                allowed_outcomes=(VerifierStatus.PASSED,),
            )
            for verifier_id in _REQUIRED_VERIFIERS
        )
        return AcceptancePolicy(
            policy_id=uuid5(NAMESPACE_URL, "cognitive-os:sprint8:python-coding-acceptance"),
            version="1",
            name="Python Coding Agent acceptance",
            description=(
                "Require sandboxed Python quality commands and deterministic workspace policies."
            ),
            requirements=requirements,
            created_at=utc_now(),
        )

    async def verify(
        self,
        *,
        task_run_id: UUID,
        approved_workspace: str,
        changed_file_evidence: dict[str, JsonValue],
        diff_evidence: dict[str, JsonValue],
        dependency_evidence: dict[str, JsonValue],
        integrity_evidence: dict[str, JsonValue],
        pytest_arguments: tuple[str, ...] = ("-q",),
        ruff_arguments: tuple[str, ...] = ("check", "."),
        mypy_arguments: tuple[str, ...] = ("src",),
        import_modules: tuple[str, ...] = ("cognitive_os",),
        repair_budget_remaining: bool = False,
    ) -> CodingVerificationOutcome:
        policy = self.policy()
        subjects: dict[str, tuple[VerificationSubject, dict[str, JsonValue]]] = {
            "coding.pytest": (
                VerificationSubject(
                    subject_type=VerificationSubjectType.WORKSPACE, workspace_path="."
                ),
                {"approved_workspace": approved_workspace, "arguments": list(pytest_arguments)},
            ),
            "coding.ruff": (
                VerificationSubject(
                    subject_type=VerificationSubjectType.WORKSPACE, workspace_path="."
                ),
                {"approved_workspace": approved_workspace, "arguments": list(ruff_arguments)},
            ),
            "coding.mypy": (
                VerificationSubject(
                    subject_type=VerificationSubjectType.WORKSPACE, workspace_path="."
                ),
                {"approved_workspace": approved_workspace, "arguments": list(mypy_arguments)},
            ),
            "coding.import": (
                VerificationSubject(
                    subject_type=VerificationSubjectType.WORKSPACE, workspace_path="."
                ),
                {"approved_workspace": approved_workspace, "modules": list(import_modules)},
            ),
            "coding.file_policy": (
                VerificationSubject(
                    subject_type=VerificationSubjectType.STRUCTURED_VALUE,
                    inline_value=changed_file_evidence,
                ),
                {
                    "maximum_file_count": self.limits.maximum_changed_files,
                    "maximum_file_bytes": self.limits.maximum_indexed_file_bytes,
                    "forbidden_paths": [".git/", ".env"],
                },
            ),
            "coding.diff_policy": (
                VerificationSubject(
                    subject_type=VerificationSubjectType.STRUCTURED_VALUE,
                    inline_value=diff_evidence,
                ),
                {
                    "maximum_diff_lines": self.limits.maximum_diff_lines,
                    "maximum_file_count": self.limits.maximum_changed_files,
                },
            ),
            "coding.dependency_policy": (
                VerificationSubject(
                    subject_type=VerificationSubjectType.STRUCTURED_VALUE,
                    inline_value=dependency_evidence,
                ),
                {"approved_additions": []},
            ),
            "coding.workspace_integrity": (
                VerificationSubject(
                    subject_type=VerificationSubjectType.STRUCTURED_VALUE,
                    inline_value=integrity_evidence,
                ),
                {},
            ),
        }
        results = []
        for requirement in policy.requirements:
            self.registry.require(requirement.verifier_id, requirement.minimum_version)
            subject, configuration = subjects[requirement.verifier_id]
            execution = await self.verification.execute(
                VerificationRequest(
                    verification_id=uuid4(),
                    task_run_id=task_run_id,
                    criterion_id=requirement.criterion_ids[0],
                    verifier_id=requirement.verifier_id,
                    verifier_version=requirement.minimum_version,
                    subject=subject,
                    configuration=configuration,
                    requested_at=utc_now(),
                    correlation_id=task_run_id,
                )
            )
            if execution.result is not None:
                results.append(execution.result)
        decision = self.acceptance.evaluate(
            policy,
            task_run_id,
            tuple(results),
            repair_budget_remaining=repair_budget_remaining,
        )
        bundle = VerificationBundle(
            bundle_id=uuid4(),
            task_run_id=task_run_id,
            criterion_results=tuple(item.criterion_id for item in decision.criterion_evaluations),
            verifier_results=tuple(results),
            required_passed=decision.required_passed,
            optional_score=decision.optional_score,
            failed_required_criteria=tuple(
                item.criterion_id
                for item in decision.criterion_evaluations
                if item.required and item.outcome is VerifierStatus.FAILED
            ),
            unverifiable_required_criteria=tuple(
                item.criterion_id
                for item in decision.criterion_evaluations
                if item.required and item.outcome is VerifierStatus.UNVERIFIABLE
            ),
            errored_required_criteria=tuple(
                item.criterion_id
                for item in decision.criterion_evaluations
                if item.required and item.outcome is VerifierStatus.ERROR
            ),
            created_at=utc_now(),
        )
        return CodingVerificationOutcome(
            summary=CodingVerificationSummary(
                full_bundle=bundle,
                registry_snapshot_hash=self.registry.snapshot(),
                required_criteria_resolved=decision.required_passed,
            ),
            decision=decision,
        )
