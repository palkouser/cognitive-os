from datetime import UTC, datetime
from uuid import UUID

import pytest

from cognitive_os.config.semantic_memory_config import SemanticMemoryConfiguration
from cognitive_os.domain.memory import (
    CodeContextMemoryContent,
    CorrectionMemoryContent,
    EpisodeMemoryContent,
    MemoryContent,
    MemoryCreator,
    MemoryCreatorType,
    MemoryProvenanceBundle,
    MemoryScope,
    MemoryScopeType,
    MemorySensitivity,
    MemorySourceIdentity,
    MemorySourceRef,
    MemorySourceType,
    MemoryType,
    MemoryWriteRequest,
    TaskSummaryMemoryContent,
    UserInstructionMemoryContent,
    VerificationSummaryMemoryContent,
)
from cognitive_os.domain.semantic_memory import SemanticActor, SemanticActorType
from cognitive_os.memory.repository import InMemoryMemoryRepository
from cognitive_os.semantic_memory.compilation import SemanticExtractionService
from cognitive_os.semantic_memory.errors import SemanticIntegrityError
from cognitive_os.semantic_memory.extraction import extract_typed_memory
from cognitive_os.semantic_memory.grounding import TrustedSourceResolver
from cognitive_os.semantic_memory.predicates import build_default_predicate_registry
from cognitive_os.semantic_memory.repository import InMemorySemanticMemoryRepository
from cognitive_os.semantic_memory.service import SemanticMemoryService

NOW = datetime(2026, 7, 15, tzinfo=UTC)

TYPED_EXTRACTION_CASES = (
    (
        CodeContextMemoryContent(
            repository_identity="1" * 64,
            base_commit="2" * 40,
            repository_profile="Python 3.12; pytest=True; ruff=True; mypy=True",
            context_hash="3" * 64,
        ),
        {"repository.base_commit", "repository.supported_profile"},
    ),
    (
        EpisodeMemoryContent(
            task_run_id=UUID(int=401),
            title="Accepted trajectory",
            problem_summary="Implement Sprint 10.",
            repository_identity="4" * 64,
            base_commit="5" * 40,
            outcome="accepted",
            patch_attempt_count=1,
            repair_count=0,
            verifier_summary="All required checks passed.",
            trajectory_hash="6" * 64,
        ),
        {"task.outcome", "repository.base_commit"},
    ),
    (
        TaskSummaryMemoryContent(
            task_run_id=UUID(int=402),
            goal="Implement Sprint 10.",
            result="Accepted.",
            review_status="accepted",
        ),
        {"task.outcome", "task.acceptance_status"},
    ),
    (
        VerificationSummaryMemoryContent(
            task_run_id=UUID(int=403),
            required_passed=("pytest",),
            required_failed=("mypy",),
            acceptance_decision_id=UUID(int=404),
            registry_snapshot_hash="7" * 64,
        ),
        {"verification.result"},
    ),
    (
        CorrectionMemoryContent(
            correction="Use the verified base commit.",
            corrected_memory_id=UUID(int=405),
            corrected_revision=1,
        ),
        {"memory.correction"},
    ),
    (
        UserInstructionMemoryContent(
            instruction="Keep repository content in English.",
            instruction_scope="repository",
        ),
        {"user.instruction"},
    ),
)


@pytest.mark.asyncio
@pytest.mark.parametrize(("content", "expected_predicates"), TYPED_EXTRACTION_CASES)
async def test_all_registered_typed_extractors_have_exact_field_grounding(
    content: MemoryContent, expected_predicates: set[str]
) -> None:
    memory = InMemoryMemoryRepository()
    record, revision = await memory.create_memory(
        MemoryWriteRequest(
            request_id=UUID(int=410),
            idempotency_key="d" * 64,
            memory_id=UUID(int=411),
            memory_type=content.memory_type,
            scope=MemoryScope(scope_type=MemoryScopeType.PROJECT, scope_id="cognitive-os"),
            title="Typed source",
            content=content,
            confidence=1,
            salience=1,
            sensitivity=MemorySensitivity.INTERNAL,
            provenance=MemoryProvenanceBundle(
                sources=(
                    MemorySourceRef(
                        identity=MemorySourceIdentity(
                            source_type=MemorySourceType.EVENT,
                            source_id=UUID(int=412),
                            content_hash="e" * 64,
                        ),
                        source_hash="e" * 64,
                    ),
                )
            ),
            actor=MemoryCreator(
                creator_type=MemoryCreatorType.INGESTION_SERVICE,
                creator_id="fixture",
            ),
        )
    )
    proposal = extract_typed_memory(record, revision, build_default_predicate_registry())
    assert {claim.predicate_id for claim in proposal.claims} == expected_predicates
    assert len(proposal.observations) == len(proposal.claims)
    resolver = TrustedSourceResolver(memory)
    for observation in proposal.observations:
        assert len(observation.source_spans) == 1
        await resolver.validate_span(observation.source_spans[0])


@pytest.mark.asyncio
async def test_typed_extraction_commit_is_grounded_proposed_and_idempotent() -> None:
    memory = InMemoryMemoryRepository()
    memory_id = UUID(int=301)
    record, revision = await memory.create_memory(
        MemoryWriteRequest(
            request_id=UUID(int=302),
            idempotency_key="a" * 64,
            memory_id=memory_id,
            memory_type=MemoryType.USER_INSTRUCTION,
            scope=MemoryScope(scope_type=MemoryScopeType.PROJECT, scope_id="cognitive-os"),
            title="User instruction",
            content=UserInstructionMemoryContent(
                instruction="Keep repository content in English.",
                instruction_scope="repository",
            ),
            confidence=1,
            salience=1,
            sensitivity=MemorySensitivity.INTERNAL,
            provenance=MemoryProvenanceBundle(
                sources=(
                    MemorySourceRef(
                        identity=MemorySourceIdentity(
                            source_type=MemorySourceType.EVENT,
                            source_id=UUID(int=303),
                            content_hash="b" * 64,
                        ),
                        source_hash="b" * 64,
                    ),
                )
            ),
            actor=MemoryCreator(
                creator_type=MemoryCreatorType.INGESTION_SERVICE,
                creator_id="fixture",
            ),
        )
    )
    registry = build_default_predicate_registry()
    repository = InMemorySemanticMemoryRepository()
    semantic = SemanticMemoryService(
        repository,
        registry,
        SemanticMemoryConfiguration(),
        source_resolver=TrustedSourceResolver(memory),
    )
    compiler = SemanticExtractionService(semantic, registry)
    proposal = extract_typed_memory(record, revision, registry)
    actor = SemanticActor(
        actor_type=SemanticActorType.APPROVED_INTERNAL_SERVICE,
        actor_id="deterministic-extractor",
    )
    original_observation = proposal.observations[0]
    original_span = original_observation.source_spans[0]
    invalid_span = original_span.model_copy(
        update={"source": original_span.source.model_copy(update={"source_id": UUID(int=999)})}
    )
    rejected = proposal.model_copy(
        update={
            "extraction_id": UUID(int=998),
            "observations": (
                original_observation,
                original_observation.model_copy(
                    update={"proposal_id": UUID(int=997), "source_spans": (invalid_span,)}
                ),
            ),
            "budget": proposal.budget.model_copy(update={"maximum_observations": 2}),
        }
    )
    with pytest.raises(SemanticIntegrityError):
        await compiler.commit(
            rejected,
            scope=record.scope,
            sensitivity=MemorySensitivity.INTERNAL,
            actor=actor,
            recorded_at=NOW,
        )
    assert not repository.observations
    assert not repository.claims

    first = await compiler.commit(
        proposal,
        scope=record.scope,
        sensitivity=MemorySensitivity.INTERNAL,
        actor=actor,
        recorded_at=NOW,
    )
    second = await compiler.commit(
        proposal,
        scope=record.scope,
        sensitivity=MemorySensitivity.INTERNAL,
        actor=actor,
        recorded_at=NOW,
    )
    assert first == second
    assert len(repository.observations) == 1
    assert len(repository.claims) == 1
    assert next(iter(repository.claim_revisions.values()))[0].belief_status.value == "proposed"
