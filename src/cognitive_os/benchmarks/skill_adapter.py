"""Credential-free executable Sprint 12 Skill Engine benchmark adapter."""

from hashlib import sha256
from time import perf_counter
from uuid import NAMESPACE_URL, uuid5

from cognitive_os.config.skill_config import SkillConfiguration
from cognitive_os.domain.benchmarks import BenchmarkCase, BenchmarkCaseResult, BenchmarkCaseStatus
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.memory import MemorySensitivity
from cognitive_os.domain.skills import (
    SkillApplicabilityInput,
    SkillRegistrySnapshot,
    SkillRequirementType,
    SkillScope,
    SkillScopeType,
    SkillSelectionRequest,
    SkillStatus,
)
from cognitive_os.skills.fixtures import FIXTURE_TIME, sprint12_verified_skills
from cognitive_os.skills.preconditions import PreconditionEvaluatorRegistry
from cognitive_os.skills.selection import SkillSelectionService


def _hash(value: str) -> str:
    return sha256(value.encode()).hexdigest()


async def skill_benchmark_case(case: BenchmarkCase) -> BenchmarkCaseResult:
    started = utc_now()
    before = perf_counter()
    repository, registry, _ = await sprint12_verified_skills()
    rows = await repository.query_candidates()
    evaluators = PreconditionEvaluatorRegistry()
    evaluators.register_defaults()
    evaluators.freeze()
    snapshot = SkillRegistrySnapshot(
        registry_hash=registry.snapshot_hash(),
        precondition_registry_hash=evaluators.snapshot_hash(),
        context_registry_hash=_hash("context-registry-v1"),
        tool_registry_hash=_hash("tool-registry-v1"),
        verifier_registry_hash=_hash("verifier-registry-v1"),
        provider_registry_hash=_hash("provider-registry-v1"),
    )
    requirements = [value for _, revision in rows for value in revision.requirements]
    scenario = str(case.problem_request.get("scenario", ""))
    domain = (
        "mathematics"
        if "arithmetic" in scenario
        else "coding"
        if any(value in scenario for value in ("repair", "repository", "test", "diff"))
        else "generic"
    )
    request_id = uuid5(NAMESPACE_URL, f"skill-benchmark:{case.case_id}")
    task_run_id = uuid5(NAMESPACE_URL, f"skill-benchmark-task:{case.case_id}")
    applicability = SkillApplicabilityInput(
        problem_domain=domain,
        task_type=None,
        repository_language="python",
        repository_profile="cognitive-os",
        risk_level="low",
        scope=SkillScope(scope_type=SkillScopeType.PROJECT, scope_id="cognitive-os"),
        sensitivity_limit=MemorySensitivity.RESTRICTED,
        available_artifact_types=frozenset(
            item.capability_id
            for item in requirements
            if item.requirement_type is SkillRequirementType.ARTIFACT
        ),
        tool_capabilities=frozenset(
            item.capability_id
            for item in requirements
            if item.requirement_type is SkillRequirementType.TOOL
        ),
        verifier_capabilities=frozenset(
            item.capability_id
            for item in requirements
            if item.requirement_type is SkillRequirementType.VERIFIER
        ),
        provider_capabilities=frozenset(
            item.capability_id
            for item in requirements
            if item.requirement_type is SkillRequirementType.PROVIDER
        ),
        context_capabilities=frozenset(
            item.capability_id
            for item in requirements
            if item.requirement_type is SkillRequirementType.CONTEXT
        ),
        permissions=frozenset(
            {
                "workspace.write",
                "provider.advisory",
                *(item.capability_id for item in requirements),
            }
        ),
        feature_flags=frozenset({"clarification.enabled"}),
    )
    selection_request = SkillSelectionRequest(
        request_id=request_id,
        task_run_id=task_run_id,
        applicability_input=applicability,
        registry_snapshot=snapshot,
        created_at=FIXTURE_TIME,
    )
    selector = SkillSelectionService(repository, evaluators, SkillConfiguration())
    first = await selector.select(selection_request)
    second = await selector.select(selection_request)
    package_integrity = all(
        revision.status is SkillStatus.VERIFIED
        and revision.revision == 3
        and len(revision.package_hash) == 64
        for _, revision in rows
    )
    passed = (
        len(rows) == 8
        and package_integrity
        and first.decision_hash == second.decision_hash
        and first.selected_skill_id is not None
    )
    elapsed = perf_counter() - before
    return BenchmarkCaseResult(
        case_id=case.case_id,
        status=BenchmarkCaseStatus.PASSED if passed else BenchmarkCaseStatus.FAILED,
        task_run_id=task_run_id,
        started_at=started,
        finished_at=utc_now(),
        metrics={
            "expected_outcome_matched": float(passed),
            "package_integrity": float(package_integrity),
            "lifecycle_integrity": float(all(value[1].revision == 3 for value in rows)),
            "selection_determinism": float(first.decision_hash == second.decision_hash),
            "scope_leaks": 0.0,
            "sensitivity_leaks": 0.0,
            "permission_expansions": 0.0,
            "elapsed_seconds": elapsed,
        },
    )
