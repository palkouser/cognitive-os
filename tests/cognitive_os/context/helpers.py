"""Deterministic Context Builder test fixtures."""

from datetime import UTC, datetime
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.context.persistence import ContextArtifactService
from cognitive_os.context.query import candidate_id
from cognitive_os.domain.common import ArtifactRef
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
from cognitive_os.domain.memory import MemoryScope, MemoryScopeType, MemorySensitivity, MemoryType

NOW = datetime(2026, 7, 16, tzinfo=UTC)
SCOPE = MemoryScope(scope_type=MemoryScopeType.PROJECT, scope_id="cognitive-os")


class MemoryArtifactStore:
    def __init__(self) -> None:
        self.data: dict[UUID, bytes] = {}
        self.refs: dict[UUID, ArtifactRef] = {}

    async def put_bytes(
        self, data: bytes, *, media_type: str, source_event_id: UUID | None = None
    ) -> ArtifactRef:
        digest = sha256(data).hexdigest()
        artifact_id = uuid5(NAMESPACE_URL, f"test-artifact:{media_type}:{digest}")
        reference = ArtifactRef(
            artifact_id=artifact_id,
            media_type=media_type,
            content_hash=digest,
            size_bytes=len(data),
            storage_key=f"objects/{digest}",
            created_at=NOW,
        )
        self.data[artifact_id] = data
        self.refs[artifact_id] = reference
        return reference

    async def get_bytes(self, artifact_id: UUID) -> bytes:
        return self.data[artifact_id]

    async def verify(self, artifact_id: UUID) -> bool:
        reference = self.refs.get(artifact_id)
        return (
            reference is not None
            and sha256(self.data[artifact_id]).hexdigest() == reference.content_hash
        )


def artifact_service() -> ContextArtifactService:
    return ContextArtifactService(MemoryArtifactStore())  # type: ignore[arg-type]


def provider_profile() -> ProviderContextProfile:
    return ProviderContextProfile(
        profile_id="test",
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


def context_request(
    *source_types: ContextSourceType,
    context_limit: int = 32_768,
) -> ContextRequest:
    request_id = UUID(int=100)
    return ContextRequest(
        context_request_id=request_id,
        task_run_id=UUID(int=101),
        step_id=UUID(int=102),
        context_purpose=ContextPurpose.EXECUTION,
        problem_reference="problem:1",
        plan_reference="plan:1",
        current_step_reference="step:1",
        query="context builder implementation",
        required_scopes=(SCOPE,),
        allowed_source_types=source_types
        or (ContextSourceType.TASK_STATE, ContextSourceType.EXECUTION_PLAN),
        allowed_memory_types=(MemoryType.OBSERVATION, MemoryType.CORRECTION),
        valid_at=NOW,
        known_at=NOW,
        sensitivity_limit=MemorySensitivity.INTERNAL,
        provider_profile="test",
        budget=ContextBudget(
            provider_context_limit=context_limit,
            reserved_output_tokens=4_096 if context_limit > 8_192 else 512,
            system_instruction_tokens=100,
            task_and_plan_tokens=100,
            safety_margin_tokens=1_024 if context_limit > 8_192 else 128,
            maximum_retriever_calls=24,
            maximum_candidates=1_000,
            maximum_items=64,
            maximum_items_per_source=12,
            minimum_recent_items=0,
            minimum_evidence_items=0,
            maximum_elapsed_seconds=30,
        ),
        source_snapshot=ContextSourceSnapshot(
            event_streams=(EventStreamSnapshot(stream_id=UUID(int=101), upper_version=3),),
            captured_at=NOW,
        ),
        created_at=NOW,
    )


def context_candidate(
    source_type: ContextSourceType,
    body: str,
    *,
    trust: ContextTrustClass = ContextTrustClass.UNVERIFIED,
    required: bool = False,
    pinned: bool = False,
    evidence: bool = False,
    recent: bool = False,
    identity: str | None = None,
) -> ContextCandidate:
    identity = identity or f"{source_type.value}:1"
    digest = sha256(body.encode()).hexdigest()
    revision = "1"
    return ContextCandidate(
        candidate_id=candidate_id(source_type, identity, revision, (SCOPE,), digest),
        source_type=source_type,
        source_identity=identity,
        source_revision=revision,
        content_hash=digest,
        summary=body,
        scopes=(SCOPE,),
        sensitivity=MemorySensitivity.INTERNAL,
        trust_class=trust,
        retrieval_routes=(
            RetrieverRank(
                retriever_id=f"fixture.{source_type.value}",
                mode=RetrievalMode.METADATA,
                rank=1,
                raw_score=1,
            ),
        ),
        score_breakdown=ContextScoreBreakdown(salience="0.5"),
        provenance=(
            ContextSourceReference(
                source_type=source_type,
                source_identity=identity,
                source_revision=revision,
                content_hash=digest,
            ),
        ),
        available_hydration_levels=(HydrationLevel.METADATA, HydrationLevel.SUMMARY),
        required=required,
        pinned=pinned,
        evidence=evidence,
        recent=recent,
    )
