"""Domain Context profiles built from the existing Context Builder.

The mandatory domain path calls no provider, so there is no model prompt to fit.
What the Context Bundle is used for here is the other half of its job: proving
that the evidence a domain answer depends on — assumptions, required units,
constants, constraints — was actually present and provenance-complete.

Every such item is marked `required`, and the Context Builder already fails
closed when a required item cannot be retrieved, hydrated, or fitted. Omitting a
required unit or assumption therefore raises rather than producing a thinner
bundle. No new retrieval authority is introduced: this registers an in-memory
retriever over items the case already declares.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.application.services.context_builder import ContextBuilderService
from cognitive_os.config.context_config import ContextConfiguration
from cognitive_os.context.fixtures import FixtureArtifactStore
from cognitive_os.context.persistence import ContextArtifactService
from cognitive_os.context.registry import ContextRetrieverRegistry
from cognitive_os.context.retrieval import InMemoryContextRetriever
from cognitive_os.domain.context import (
    ContextBudget,
    ContextCandidate,
    ContextPurpose,
    ContextRequest,
    ContextScoreBreakdown,
    ContextSourceReference,
    ContextSourceSnapshot,
    ContextSourceType,
    ContextTrustClass,
    EventStreamSnapshot,
    HydrationLevel,
    ProviderContextProfile,
    RetrievalMode,
    RetrieverRank,
    TokenEstimatorProfile,
    TokenEstimatorType,
)
from cognitive_os.domain.domains import DomainBenchmarkCase, DomainKind
from cognitive_os.domain.memory import (
    MemoryScope,
    MemoryScopeType,
    MemorySensitivity,
    MemoryType,
)

from .fixtures import FIXTURE_TIME

DOMAIN_SCOPE = MemoryScope(scope_type=MemoryScopeType.PROJECT, scope_id="cognitive-os")
PROFILE_ID = "domain-offline"

#: The bundle supports a registered domain skill's execution step, so every
#: domain uses the skill-execution purpose rather than the coding purpose.
_PURPOSES: dict[DomainKind, ContextPurpose] = dict.fromkeys(
    DomainKind, ContextPurpose.SKILL_EXECUTION
)


@dataclass(frozen=True, slots=True)
class RequiredItem:
    """One piece of evidence the answer depends on; omission must fail closed."""

    source_type: ContextSourceType
    identity: str
    body: str


def required_items(case: DomainBenchmarkCase) -> tuple[RequiredItem, ...]:
    """Everything the case declares as necessary context, in a stable order."""
    problem = case.problem
    items = [
        RequiredItem(
            ContextSourceType.TASK_STATE,
            f"task:{case.case_id}",
            f"{case.problem_type}: {problem.statement}",
        ),
        RequiredItem(
            ContextSourceType.EXECUTION_PLAN,
            f"plan:{case.case_id}",
            "Plan: solve through domains.solve, then verify with domains.checker.",
        ),
    ]
    items.extend(
        RequiredItem(
            ContextSourceType.SEMANTIC_CLAIM,
            f"assumption:{index}:{case.case_id}",
            f"Assumption: {text}",
        )
        for index, text in enumerate(problem.assumptions)
    )
    # Physics answers are meaningless without their units, so each declared unit
    # is a required item in its own right.
    items.extend(
        RequiredItem(
            ContextSourceType.SEMANTIC_CLAIM,
            f"unit:{index}:{case.case_id}",
            f"Required unit: {text}",
        )
        for index, text in enumerate(problem.required_units)
    )
    items.extend(
        RequiredItem(
            ContextSourceType.SEMANTIC_CLAIM,
            f"constraint:{index}:{case.case_id}",
            f"Constraint: {text}",
        )
        for index, text in enumerate(problem.constraints)
    )
    items.extend(
        RequiredItem(
            ContextSourceType.SEMANTIC_CLAIM,
            f"provenance:{index}:{case.case_id}",
            f"Source {item.source} revision {item.revision} under {item.licence}",
        )
        for index, item in enumerate(problem.source_refs)
    )
    return tuple(items)


def _candidate(item: RequiredItem) -> ContextCandidate:
    digest = sha256(item.body.encode()).hexdigest()
    return ContextCandidate(
        candidate_id=uuid5(NAMESPACE_URL, f"domain-context:{item.identity}:{digest}"),
        source_type=item.source_type,
        source_identity=item.identity,
        source_revision="1",
        content_hash=digest,
        summary=item.body,
        scopes=(DOMAIN_SCOPE,),
        sensitivity=MemorySensitivity.INTERNAL,
        trust_class=ContextTrustClass.SYSTEM,
        retrieval_routes=(
            RetrieverRank(
                retriever_id="domains.context",
                mode=RetrievalMode.METADATA,
                rank=1,
                raw_score=Decimal(1),
            ),
        ),
        score_breakdown=ContextScoreBreakdown(salience=Decimal(1)),
        provenance=(
            ContextSourceReference(
                source_type=item.source_type,
                source_identity=item.identity,
                source_revision="1",
                content_hash=digest,
            ),
        ),
        known_at=FIXTURE_TIME,
        available_hydration_levels=(HydrationLevel.METADATA, HydrationLevel.SUMMARY),
        # Every domain evidence item is required: the Context Builder fails closed
        # rather than silently returning a bundle without it.
        required=True,
        # The contract requires pinned evidence for required items: pinning is
        # what stops budget pressure from dropping a unit or an assumption.
        pinned=True,
        evidence=True,
        recent=True,
    )


class RequiredContextMissingError(RuntimeError):
    """Raised when a bundle does not cover every item the case declared."""


def assert_required_context(case: DomainBenchmarkCase, bundle: object) -> tuple[str, ...]:
    """Check the built bundle against the case's *declared* requirements.

    The Context Builder fails closed on a required candidate it cannot fit or
    hydrate, but it cannot notice an item a retriever never offered — no retrieval
    system can. That gap is closed here, where the requirement is declared: the
    identities the case says it needs are compared with the identities the bundle
    actually carries, and a shortfall raises.
    """
    covered = {
        reference.source_identity
        for section in getattr(bundle, "sections", ())
        for reference in getattr(section, "source_references", ())
    }
    declared = tuple(item.identity for item in required_items(case))
    missing = tuple(item for item in declared if item not in covered)
    if missing:
        raise RequiredContextMissingError(
            f"context bundle is missing required evidence: {list(missing)}"
        )
    return declared


def domain_profile() -> ProviderContextProfile:
    return ProviderContextProfile(
        profile_id=PROFILE_ID,
        maximum_context_tokens=32_768,
        maximum_output_tokens=4_096,
        safety_margin_tokens=1_024,
        estimator=TokenEstimatorProfile(
            estimator_type=TokenEstimatorType.CONSERVATIVE_UTF8,
            estimator_id="context.utf8",
            version="1",
        ),
        sensitivity_ceiling=MemorySensitivity.INTERNAL,
    )


def build_domain_context(
    case: DomainBenchmarkCase,
    *,
    task_run_id: UUID,
    step_id: UUID,
    omit: str | None = None,
) -> tuple[ContextBuilderService, ContextRequest]:
    """Compose a Context Builder over the case's required evidence.

    `omit` drops one required item by identity prefix, which is how the
    fail-closed behaviour is demonstrated rather than asserted.
    """
    items = tuple(
        item for item in required_items(case) if omit is None or not item.identity.startswith(omit)
    )
    candidates = tuple(_candidate(item) for item in items)
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
    service = ContextBuilderService(
        registry,
        ContextConfiguration(),
        {PROFILE_ID: domain_profile()},
        artifacts=ContextArtifactService(FixtureArtifactStore()),
    )
    request = ContextRequest(
        context_request_id=uuid5(NAMESPACE_URL, f"domain-context-request:{case.case_id}"),
        task_run_id=task_run_id,
        step_id=step_id,
        context_purpose=_PURPOSES[case.domain],
        problem_reference=f"problem:{case.problem.problem_id}",
        plan_reference=f"plan:{case.case_id}",
        current_step_reference=f"step:{step_id}",
        query=f"{case.problem_type} {' '.join(case.problem.unknowns)}",
        required_scopes=(DOMAIN_SCOPE,),
        allowed_source_types=(
            ContextSourceType.TASK_STATE,
            ContextSourceType.EXECUTION_PLAN,
            ContextSourceType.SEMANTIC_CLAIM,
        ),
        allowed_memory_types=(MemoryType.OBSERVATION,),
        valid_at=FIXTURE_TIME,
        known_at=FIXTURE_TIME,
        sensitivity_limit=MemorySensitivity.INTERNAL,
        provider_profile=PROFILE_ID,
        budget=ContextBudget(
            provider_context_limit=32_768,
            reserved_output_tokens=4_096,
            system_instruction_tokens=256,
            task_and_plan_tokens=512,
            safety_margin_tokens=1_024,
            maximum_retriever_calls=8,
            maximum_candidates=256,
            maximum_items=64,
            maximum_items_per_source=32,
            minimum_recent_items=1,
            minimum_evidence_items=1,
            maximum_elapsed_seconds=30,
        ),
        source_snapshot=ContextSourceSnapshot(
            event_streams=(EventStreamSnapshot(stream_id=task_run_id, upper_version=1),),
            captured_at=FIXTURE_TIME,
        ),
        created_at=FIXTURE_TIME,
    )
    return service, request
