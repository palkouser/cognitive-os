"""Compose the Skill Engine so a domain case executes as a verified skill."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import NAMESPACE_URL, uuid5

from cognitive_os.application.services.context_builder import ContextBuilderService
from cognitive_os.config.context_config import ContextConfiguration
from cognitive_os.config.skill_config import SkillConfiguration
from cognitive_os.context.fixtures import FixtureArtifactStore
from cognitive_os.context.persistence import ContextArtifactService
from cognitive_os.context.registry import ContextRetrieverRegistry
from cognitive_os.context.retrieval import InMemoryContextRetriever
from cognitive_os.domain.context import ContextSourceType, ContextTrustClass, HydrationLevel
from cognitive_os.domain.domains import DomainBenchmarkCase
from cognitive_os.domain.memory import MemorySensitivity
from cognitive_os.domain.skills import (
    SkillApplicabilityInput,
    SkillRegistrySnapshot,
    SkillScope,
    SkillScopeType,
    SkillSelectionDecision,
    SkillSelectionRequest,
    SkillStatus,
)
from cognitive_os.skills.execution import SkillExecutionService
from cognitive_os.skills.fixtures import sprint12_verified_skills
from cognitive_os.skills.preconditions import PreconditionEvaluatorRegistry
from cognitive_os.skills.registry import SkillRegistry
from cognitive_os.skills.repository import InMemorySkillRepository
from cognitive_os.skills.selection import SkillSelectionService

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


#: Repository, registry, and artifact store, shareable across cases so that skill
#: statistics accumulate instead of resetting on every run.
type SkillFixtureBundle = tuple[InMemorySkillRepository, SkillRegistry, FixtureArtifactStore]


async def skill_fixture_bundle() -> SkillFixtureBundle:
    return await sprint12_verified_skills()


def _domain_precondition_evaluators() -> PreconditionEvaluatorRegistry:
    evaluators = PreconditionEvaluatorRegistry()
    evaluators.register_defaults()
    evaluators.freeze()
    return evaluators


async def select_domain_skill(
    case: DomainBenchmarkCase,
    repository: InMemorySkillRepository,
    skill_registry: SkillRegistry,
    *,
    restrict_to: frozenset[str] | None = None,
) -> SkillSelectionDecision:
    """Ask the Skill Engine which skill this case should run.

    `verifier_capabilities` is the case's own `required_verifiers` — the capabilities its
    checker actually emits — and nothing wider. That single choice is what makes the
    decision meaningful: every seed skill declares a `verifier_capability` precondition,
    so a skill whose verifier will not run on this case is excluded here, with a recorded
    reason, instead of failing later during execution.
    """
    applicability = SkillApplicabilityInput(
        problem_domain=case.domain.value,
        task_type=case.problem_type,
        risk_level="low",
        scope=SkillScope(scope_type=SkillScopeType.PROJECT, scope_id="cognitive-os"),
        sensitivity_limit=MemorySensitivity.INTERNAL,
        tool_capabilities=frozenset(case.required_tools),
        verifier_capabilities=frozenset(case.required_verifiers),
    )
    request = SkillSelectionRequest(
        request_id=uuid5(NAMESPACE_URL, f"domain-skill-selection:{case.case_id}"),
        task_run_id=uuid5(NAMESPACE_URL, f"domain-skill-task:{case.case_id}"),
        applicability_input=applicability,
        # The problem-type registry, not the whole skill registry, decides what this task
        # class may run. Several mathematics skills satisfy `mathematics.numeric`, so
        # preconditions alone would let selection reach outside the permitted set — which
        # is exactly what the first run of this code did.
        #
        # `restrict_to` narrows it further for a counterfactual: naming one alternative
        # makes the selector choose that skill through the ordinary path, so the varied run
        # is a real governed selection rather than an execution smuggled past it.
        permitted_canonical_names=frozenset(
            restrict_to if restrict_to is not None else resolve(case.problem_type).skills
        ),
        registry_snapshot=SkillRegistrySnapshot(
            registry_hash=skill_registry.snapshot_hash(),
            precondition_registry_hash=_hash("domain-precondition-registry-v1"),
            context_registry_hash=_hash("domain-context-registry-v1"),
            tool_registry_hash=_hash("domain-tool-registry-v1"),
            verifier_registry_hash=_hash("domain-verifier-registry-v1"),
            provider_registry_hash=_hash("domain-provider-registry-v1"),
        ),
        created_at=FIXTURE_TIME,
    )
    selector = SkillSelectionService(
        repository, _domain_precondition_evaluators(), SkillConfiguration()
    )
    return await selector.select(request)


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
    case: DomainBenchmarkCase,
    *,
    candidate_override: object | None = None,
    bundle: SkillFixtureBundle | None = None,
    restrict_to: frozenset[str] | None = None,
) -> DomainSkillRun:
    """Execute one domain case as the skill the Skill Engine actually selects.

    The Skill Engine refuses anything but a `VERIFIED` revision whose package hash
    and registry snapshot match, and it requires a valid Context Bundle before the
    first step. Those checks are the point of running this way.

    Selection is a real decision here. Until Sprint 21 this function took
    `entry.skills[0]` — the first name in a static table — so the Skill Engine's
    selector never ran on the domain path and the table's *ordering* silently encoded
    the answer. For logic and mathematics the second candidate is not even satisfiable
    (`constraint-solving` needs `logic.satisfiable`, `cross-domain-result-review` needs
    `generic.exact_value`, and neither capability is ever emitted), so position 0
    happened to be right. Being right by luck is not the same as being checked.

    `bundle` lets a caller share one registry across several cases so skill statistics
    accumulate; see `run_corpus_as_skills`. Passing nothing keeps the previous
    behaviour of a fresh registry per case.
    """
    from cognitive_os.domain.skills import SkillExecutionRequest

    resolved = bundle or await skill_fixture_bundle()
    repository, skill_registry, artifacts = resolved
    entry = resolve(case.problem_type)

    decision = await select_domain_skill(case, repository, skill_registry, restrict_to=restrict_to)
    if decision.selected_skill_id is None:
        raise RuntimeError(
            f"the Skill Engine selected no skill for {case.case_id!r}: "
            f"{[item.reason.value for item in decision.exclusions]}"
        )
    match = next(
        (
            (item, revision)
            for item, revision in skill_registry.query()
            if revision.skill_id == decision.selected_skill_id
            and revision.revision == decision.selected_revision
        ),
        None,
    )
    if match is None:
        raise LookupError(f"selected skill {decision.selected_skill_id} is not registered")
    item, revision = match
    # The problem-type registry stays authoritative about which skills a task class may
    # use. Preconditions should already make a cross-domain choice impossible, but
    # "should" is not a check, and a selector reaching outside the permitted set is a
    # governance failure rather than a surprising result.
    if item.identity.canonical_name not in entry.skills:
        raise RuntimeError(
            f"selection chose {item.identity.canonical_name!r}, which is outside the "
            f"permitted set {entry.skills!r} for problem type {case.problem_type!r}"
        )
    if revision.status is not SkillStatus.VERIFIED:
        raise RuntimeError(f"domain skill {item.identity.canonical_name!r} is not verified")

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
        # Keyed by the selected revision as well as the case. Two different skills running
        # the same case are two different executions, and the execution log has an
        # idempotency guard that says so; before selection was real the skill was fixed by
        # a static table, so the case alone happened to be unique.
        execution_id=uuid5(
            NAMESPACE_URL,
            f"domain-skill-execution:{case.case_id}:"
            f"{item.identity.canonical_name}:{revision.revision}",
        ),
        skill_id=item.identity.skill_id,
        skill_revision=revision.revision,
        task_run_id=uuid5(NAMESPACE_URL, f"domain-skill-task:{case.case_id}"),
        problem_reference=case.problem.problem_id,
        plan_reference=uuid5(NAMESPACE_URL, f"domain-skill-plan:{case.case_id}"),
        input_bindings=domain_input_bindings(case, item.identity.canonical_name),
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
        result=result,
        controlled=controlled,
        signature=domain_task_signature(case),
        selection=decision,
    )


async def run_corpus_as_skills(
    cases: Sequence[DomainBenchmarkCase],
) -> tuple[DomainSkillRun, ...]:
    """Run several cases against one shared registry, so statistics accumulate.

    `SkillExecutionService` already rebuilds `SkillStatistics` from the execution log
    after every run, and `SkillSelectionService` already turns those into
    `statistics_score = accepted * 100 // executions` once `executions` reaches
    `minimum_statistics_sample_for_ranking`. Nothing was missing from that arithmetic.

    What was missing is *continuity*: `run_case_as_skill` built a fresh registry per
    case, so every selection saw an empty execution log and the score was always 0,
    leaving ties to be broken by `str(skill_id)`. Sharing the bundle is the whole fix —
    the aggregation is deterministic and already written, and no learned component is
    involved.
    """
    bundle = await skill_fixture_bundle()
    return tuple([await run_case_as_skill(case, bundle=bundle) for case in cases])
