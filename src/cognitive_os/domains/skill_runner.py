"""Compose the Skill Engine so a domain case executes as a verified skill."""

from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from cognitive_os.application.services.context_builder import ContextBuilderService
from cognitive_os.config.context_config import ContextConfiguration
from cognitive_os.context.persistence import ContextArtifactService
from cognitive_os.context.registry import ContextRetrieverRegistry
from cognitive_os.context.retrieval import InMemoryContextRetriever
from cognitive_os.domain.context import ContextSourceType, ContextTrustClass, HydrationLevel
from cognitive_os.domain.domains import DomainBenchmarkCase
from cognitive_os.domain.skills import SkillRegistrySnapshot, SkillStatus
from cognitive_os.skills.execution import SkillExecutionService
from cognitive_os.skills.fixtures import sprint12_verified_skills

from .context import PROFILE_ID, _candidate, domain_profile, required_items
from .fixtures import FIXTURE_TIME
from .registry import resolve
from .skill_execution import (
    DomainSkillRun,
    DomainSkillRunner,
    domain_actor,
    domain_context_request_factory,
    domain_input_bindings,
    domain_task_signature,
)


def _hash(value: str) -> str:
    from hashlib import sha256

    return sha256(value.encode()).hexdigest()


def _context_builder(case: DomainBenchmarkCase) -> ContextBuilderService:
    """Builder wired to this case's required evidence, shared by every step."""
    candidates = tuple(_candidate(item) for item in required_items(case))
    bodies = {
        item.candidate_id: {HydrationLevel.SUMMARY: item.summary or ""} for item in candidates
    }
    registry = ContextRetrieverRegistry()
    registry.register(
        InMemoryContextRetriever(
            retriever_id="domains.context",
            source_types=(
                ContextSourceType.TASK_STATE,
                ContextSourceType.EXECUTION_PLAN,
                ContextSourceType.SEMANTIC_CLAIM,
            ),
            candidates=candidates,
            bodies=bodies,
            trust_class=ContextTrustClass.SYSTEM,
        )
    )
    registry.freeze()
    from cognitive_os.context.fixtures import FixtureArtifactStore

    return ContextBuilderService(
        registry,
        ContextConfiguration(),
        {PROFILE_ID: domain_profile()},
        artifacts=ContextArtifactService(FixtureArtifactStore()),
    )


async def run_case_as_skill(
    case: DomainBenchmarkCase, *, candidate_override: object | None = None
) -> DomainSkillRun:
    """Execute one domain case as an exact verified skill revision.

    The Skill Engine refuses anything but a `VERIFIED` revision whose package hash
    and registry snapshot match, and it requires a valid Context Bundle before the
    first step. Those checks are the point of running this way.
    """
    from cognitive_os.domain.skills import SkillExecutionRequest

    repository, skill_registry, artifacts = await sprint12_verified_skills()
    entry = resolve(case.problem_type)
    wanted = entry.skills[0]
    match = next(
        (
            (item, revision)
            for item, revision in skill_registry.query()
            if item.identity.canonical_name == wanted
        ),
        None,
    )
    if match is None:
        raise LookupError(f"domain skill {wanted!r} is not registered")
    item, revision = match
    if revision.status is not SkillStatus.VERIFIED:
        raise RuntimeError(f"domain skill {wanted!r} is not verified")

    def snapshot() -> SkillRegistrySnapshot:
        return SkillRegistrySnapshot(
            registry_hash=skill_registry.snapshot_hash(),
            precondition_registry_hash=_hash("domain-precondition-registry-v1"),
            context_registry_hash=_hash("domain-context-registry-v1"),
            tool_registry_hash=_hash("domain-tool-registry-v1"),
            verifier_registry_hash=_hash("domain-verifier-registry-v1"),
            provider_registry_hash=_hash("domain-provider-registry-v1"),
        )

    runner = DomainSkillRunner(case, candidate_override=candidate_override)
    service = SkillExecutionService(
        repository,
        artifacts,
        _context_builder(case),
        runner,
        domain_context_request_factory(case),
        snapshot,
    )
    request = SkillExecutionRequest(
        execution_id=uuid5(NAMESPACE_URL, f"domain-skill-execution:{case.case_id}"),
        skill_id=item.identity.skill_id,
        skill_revision=revision.revision,
        task_run_id=uuid5(NAMESPACE_URL, f"domain-skill-task:{case.case_id}"),
        problem_reference=case.problem.problem_id,
        plan_reference=uuid5(NAMESPACE_URL, f"domain-skill-plan:{case.case_id}"),
        input_bindings=domain_input_bindings(case),
        controller_budget=revision.resource_budget,
        expected_registry_snapshots=snapshot(),
        requested_by=domain_actor(),
        package_hash=revision.package_hash,
        created_at=FIXTURE_TIME,
    )
    result = await service.start_execution(request)
    controlled = runner.last_run
    if controlled is None:
        raise RuntimeError("skill execution did not reach the governed controller path")
    return DomainSkillRun(
        result=result, controlled=controlled, signature=domain_task_signature(case)
    )
