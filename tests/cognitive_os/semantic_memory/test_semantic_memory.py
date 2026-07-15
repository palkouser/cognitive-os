from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

import pytest
from pydantic import ValidationError

from cognitive_os.application.services.verification_service import VerificationService
from cognitive_os.config.semantic_memory_config import SemanticMemoryConfiguration
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.memory import MemoryScope, MemoryScopeType, MemorySensitivity
from cognitive_os.domain.semantic_memory import (
    BeliefStatus,
    Claim,
    ClaimIdentity,
    ClaimPromotionDecision,
    ClaimPromotionOutcome,
    ClaimRevision,
    ClaimRevisionReference,
    ClaimTemporalInterval,
    ConfidenceDimensions,
    ContradictionRecord,
    ContradictionResolution,
    ContradictionResolutionOutcome,
    ContradictionRevision,
    ContradictionSeverity,
    ContradictionStatus,
    EvidenceLink,
    EvidenceRelation,
    GroundedSourceSpan,
    GroundingMode,
    ObservationQuery,
    SemanticActor,
    SemanticActorType,
    SemanticLiteral,
    SemanticLiteralKind,
    SemanticObservation,
    SemanticSourceRef,
    SemanticSourceType,
    TemporalClaimQuery,
    TemporalQueryMode,
    WikiPage,
    claim_revision_hash,
    semantic_hash,
)
from cognitive_os.events.semantic_memory_event_service import SemanticMemoryEventService
from cognitive_os.events.storage import AppendResult, StoredEvent
from cognitive_os.events.verifier_event_service import VerifierEventService
from cognitive_os.semantic_memory.beliefs import aggregate_confidence
from cognitive_os.semantic_memory.canonicalization import canonical_identifier
from cognitive_os.semantic_memory.errors import SemanticIntegrityError, SemanticPolicyError
from cognitive_os.semantic_memory.predicates import build_default_predicate_registry
from cognitive_os.semantic_memory.promotion import SemanticPromotionGate
from cognitive_os.semantic_memory.rendering import escape_markdown
from cognitive_os.semantic_memory.repository import InMemorySemanticMemoryRepository
from cognitive_os.semantic_memory.service import SemanticMemoryService
from cognitive_os.verification.errors import VerifierNotFoundError
from cognitive_os.verification.factory import build_builtin_registry
from cognitive_os.verification.registry import VerifierRegistry
from cognitive_os.verification.semantic import (
    REQUIRED_SEMANTIC_PROMOTION_CAPABILITIES,
    SemanticInvariantVerifier,
)

NOW = datetime(2026, 7, 15, tzinfo=UTC)
FUTURE = datetime(2027, 1, 10, tzinfo=UTC)
KNOWN_FUTURE = datetime(2027, 1, 11, tzinfo=UTC)
SCOPE = MemoryScope(scope_type=MemoryScopeType.PROJECT, scope_id="cognitive-os")
ACTOR = SemanticActor(actor_type=SemanticActorType.OPERATOR, actor_id="operator")
SOURCE = SemanticSourceRef(
    source_type=SemanticSourceType.MEMORY_REVISION,
    source_id=UUID(int=10),
    revision=1,
    content_hash="a" * 64,
)
SPAN = GroundedSourceSpan(
    source=SOURCE,
    mode=GroundingMode.MEMORY_FIELD,
    path="content.repository_profile",
    excerpt_hash="b" * 64,
)


class MemoryEventStore:
    def __init__(self) -> None:
        self.events: list[StoredEvent] = []

    async def append(self, events, *, expected_version):
        event = events[0]
        current = len([item for item in self.events if item.envelope.stream_id == event.stream_id])
        if current != expected_version:
            raise RuntimeError("expected-version conflict")
        stored = StoredEvent(
            global_position=len(self.events) + 1,
            stored_at=utc_now(),
            envelope=event,
        )
        self.events.append(stored)
        return AppendResult(
            stream_id=event.stream_id,
            previous_stream_version=current,
            current_stream_version=event.stream_version,
            event_ids=(event.event_id,),
            global_positions=(stored.global_position,),
            stored_at=stored.stored_at,
        )

    async def read_stream(self, stream_id, *, from_version=1, to_version=None, limit=None):
        values = [
            item
            for item in self.events
            if item.envelope.stream_id == stream_id and item.envelope.stream_version >= from_version
        ]
        if to_version is not None:
            values = [item for item in values if item.envelope.stream_version <= to_version]
        return tuple(values[:limit] if limit else values)

    async def get_stream_version(self, stream_id):
        values = [item for item in self.events if item.envelope.stream_id == stream_id]
        return values[-1].envelope.stream_version if values else None


def confidence(*, complete: bool = False) -> ConfidenceDimensions:
    if complete:
        return aggregate_confidence(
            extraction=0.9,
            source=0.9,
            grounding=0.9,
            evidence=0.9,
            verification=0.9,
            consistency=0.9,
        )
    return aggregate_confidence(extraction=0.9)


def revision(
    claim_id: UUID,
    number: int,
    value: str,
    *,
    status: BeliefStatus = BeliefStatus.PROPOSED,
    valid_from: datetime = NOW,
    recorded_at: datetime = NOW,
    complete_confidence: bool = False,
) -> ClaimRevision:
    object_value = SemanticLiteral(
        literal_kind=SemanticLiteralKind.VERSION,
        value=value,
    )
    dimensions = confidence(complete=complete_confidence)
    interval = ClaimTemporalInterval(valid_from=valid_from)
    evidence_hash = semantic_hash([evidence(claim_id, number).model_dump(mode="json")])
    content_hash = claim_revision_hash(
        claim_id=claim_id,
        revision=number,
        object_value=object_value,
        statement=f"The project uses Python {value}.",
        belief_status=status,
        confidence=dimensions,
        valid_interval=interval,
        reason="test",
        evidence_snapshot_hash=evidence_hash,
    )
    return ClaimRevision(
        claim_id=claim_id,
        revision=number,
        previous_revision=None if number == 1 else number - 1,
        object=object_value,
        statement=f"The project uses Python {value}.",
        belief_status=status,
        confidence=dimensions,
        valid_interval=interval,
        reason="test",
        recorded_at=recorded_at,
        created_by=ACTOR,
        evidence_snapshot_hash=evidence_hash,
        content_hash=content_hash,
    )


def claim(claim_id: UUID) -> Claim:
    return Claim(
        identity=ClaimIdentity(
            claim_id=claim_id,
            scope=SCOPE,
            canonical_subject_key="project:cognitive-os",
            predicate_id="project.python_version",
        ),
        current_revision=1,
        current_belief_status=BeliefStatus.PROPOSED,
        sensitivity=MemorySensitivity.INTERNAL,
        created_at=NOW,
        created_by=ACTOR,
        idempotency_key=sha256(str(claim_id).encode()).hexdigest(),
    )


def evidence(claim_id: UUID, claim_revision: int = 1) -> EvidenceLink:
    return EvidenceLink(
        evidence_id=UUID(int=claim_id.int + 100 + claim_revision),
        claim={"claim_id": claim_id, "revision": claim_revision},
        source=SOURCE,
        source_span=SPAN,
        relation=EvidenceRelation.SUPPORTS,
        strength=1,
        created_at=NOW,
        created_by=ACTOR,
    )


def service() -> tuple[SemanticMemoryService, InMemorySemanticMemoryRepository]:
    class Resolver:
        async def validate_span(self, _span, **_policy) -> None:
            return None

    repository = InMemorySemanticMemoryRepository()
    return (
        SemanticMemoryService(
            repository,
            build_default_predicate_registry(),
            SemanticMemoryConfiguration(),
            clock=lambda: NOW,
            id_factory=lambda: UUID(int=999),
            source_resolver=Resolver(),  # type: ignore[arg-type]
        ),
        repository,
    )


def eventful_service() -> tuple[
    SemanticMemoryService,
    InMemorySemanticMemoryRepository,
    SemanticMemoryEventService,
    MemoryEventStore,
]:
    class Resolver:
        async def validate_span(self, _span, **_policy) -> None:
            return None

    store = MemoryEventStore()
    events = SemanticMemoryEventService(store)  # type: ignore[arg-type]
    repository = InMemorySemanticMemoryRepository()
    return (
        SemanticMemoryService(
            repository,
            build_default_predicate_registry(),
            SemanticMemoryConfiguration(),
            clock=lambda: NOW,
            id_factory=lambda: UUID(int=999),
            event_service=events,
            source_resolver=Resolver(),  # type: ignore[arg-type]
        ),
        repository,
        events,
        store,
    )


def test_configuration_registry_and_canonicalization_fail_closed() -> None:
    with pytest.raises(ValidationError):
        SemanticMemoryConfiguration(allow_provider_direct_commit=True)
    registry = build_default_predicate_registry()
    with pytest.raises(ValueError, match="frozen"):
        registry.register(registry.list_all()[0])
    assert len(registry.list_all()) == 13
    assert len(registry.snapshot_hash()) == 64
    assert canonical_identifier(" Project.Python_Version ") == "project.python_version"
    with pytest.raises(ValueError, match="ASCII"):
        canonical_identifier("pr\u043eject.python_version")


@pytest.mark.asyncio
async def test_observation_is_exactly_grounded_immutable_and_provider_denied() -> None:
    semantic_service, repository = service()
    payload = {
        "content": "Python 3.12",
        "normalized_content": "Python 3.12",
        "source_refs": [SOURCE.model_dump(mode="json")],
        "source_spans": [SPAN.model_dump(mode="json")],
    }
    observation = SemanticObservation(
        observation_id=UUID(int=20),
        content="Python 3.12",
        normalized_content="Python 3.12",
        source_refs=(SOURCE,),
        source_spans=(SPAN,),
        observed_at=NOW,
        recorded_at=NOW,
        scope=SCOPE,
        confidence=1,
        sensitivity=MemorySensitivity.INTERNAL,
        created_by=ACTOR,
        content_hash=semantic_hash(payload),
        idempotency_key="c" * 64,
    )
    assert await semantic_service.record_observation(observation) == observation
    assert await semantic_service.record_observation(observation) == observation
    assert len(repository.observations) == 1
    provider = observation.model_copy(
        update={
            "observation_id": UUID(int=21),
            "idempotency_key": "d" * 64,
            "created_by": SemanticActor(actor_type=SemanticActorType.PROVIDER, actor_id="model"),
        }
    )
    with pytest.raises(SemanticPolicyError, match="providers"):
        await semantic_service.record_observation(provider)


@pytest.mark.asyncio
async def test_observation_query_filters_exact_source_scope_and_audits() -> None:
    semantic_service, _, _, store = eventful_service()
    payload = {
        "content": "Python 3.12",
        "normalized_content": "Python 3.12",
        "source_refs": [SOURCE.model_dump(mode="json")],
        "source_spans": [SPAN.model_dump(mode="json")],
    }
    observation = SemanticObservation(
        observation_id=UUID(int=22),
        content="Python 3.12",
        normalized_content="Python 3.12",
        source_refs=(SOURCE,),
        source_spans=(SPAN,),
        observed_at=NOW,
        recorded_at=NOW,
        scope=SCOPE,
        confidence=1,
        sensitivity=MemorySensitivity.INTERNAL,
        created_by=ACTOR,
        content_hash=semantic_hash(payload),
        idempotency_key="e" * 64,
    )
    await semantic_service.record_observation(observation)
    query = ObservationQuery(
        query_id=UUID(int=23),
        source_type=SemanticSourceType.MEMORY_REVISION,
        source_id=SOURCE.source_id,
        source_revision=1,
        scopes=(SCOPE,),
        sensitivity_ceiling=MemorySensitivity.INTERNAL,
        requested_at=NOW,
        requested_by=ACTOR,
    )
    result = await semantic_service.query_observations(query)
    assert result.observations == (observation,)
    assert any(
        item.envelope.event_type == "semantic.observations_accessed"
        and item.envelope.stream_id == query.query_id
        for item in store.events
    )


@pytest.mark.asyncio
async def test_claim_promotion_requires_complete_verified_host_decision() -> None:
    semantic_service, repository, events, _ = eventful_service()
    claim_id = UUID(int=30)
    await semantic_service.create_claim(
        claim(claim_id), revision(claim_id, 1, "3.12"), (evidence(claim_id),)
    )
    promoted = revision(
        claim_id,
        2,
        "3.12",
        status=BeliefStatus.SUPPORTED,
        complete_confidence=True,
    )
    decision = ClaimPromotionDecision(
        decision_id=UUID(int=31),
        claim={"claim_id": claim_id, "revision": 1},
        outcome=ClaimPromotionOutcome.SUPPORTED,
        verifier_bundle_hash="d" * 64,
        registry_snapshot_hash="e" * 64,
        reason_codes=("verified",),
        decided_at=NOW,
        decided_by=ACTOR,
    )
    promoted = promoted.model_copy(update={"promotion_decision_id": decision.decision_id})
    with pytest.raises(SemanticPolicyError, match="decision"):
        await semantic_service.transition_claim(
            promoted, expected_revision=1, evidence=(evidence(claim_id, 2),)
        )
    with pytest.raises(SemanticPolicyError, match="not persisted"):
        await semantic_service.transition_claim(
            promoted,
            expected_revision=1,
            decision=decision,
            evidence=(evidence(claim_id, 2),),
        )
    await events.record_promotion_decision(decision)
    assert (
        await semantic_service.transition_claim(
            promoted,
            expected_revision=1,
            decision=decision,
            evidence=(evidence(claim_id, 2),),
        )
        == promoted
    )
    assert repository.claims[claim_id].current_belief_status is BeliefStatus.SUPPORTED
    assert len(repository.claim_revisions[claim_id]) == 2


@pytest.mark.asyncio
async def test_initial_claim_and_evidence_reject_atomically() -> None:
    repository = InMemorySemanticMemoryRepository()
    claim_id = UUID(int=35)
    duplicate = evidence(claim_id)
    with pytest.raises(SemanticIntegrityError, match="duplicated"):
        await repository.create_claim_with_evidence(
            claim(claim_id),
            revision(claim_id, 1, "3.12"),
            (duplicate, duplicate),
        )
    assert not repository.claims
    assert not repository.claim_revisions
    assert not repository.evidence


@pytest.mark.asyncio
async def test_evidence_reevaluation_is_typed_and_audited() -> None:
    semantic_service, _, _, store = eventful_service()
    claim_id = UUID(int=36)
    await semantic_service.create_claim(
        claim(claim_id), revision(claim_id, 1, "3.12"), (evidence(claim_id),)
    )

    results = await semantic_service.reevaluate_evidence(claim_id)

    assert len(results) == 1
    assert results[0].valid
    audit = next(
        item for item in store.events if item.envelope.event_type == "semantic.evidence_reevaluated"
    )
    assert audit.envelope.payload["claim_id"] == str(claim_id)
    assert audit.envelope.payload["revision"] == 1
    assert audit.envelope.payload["results"][0]["reason_codes"] == ["valid"]


@pytest.mark.asyncio
async def test_bitemporal_queries_do_not_leak_future_revisions_and_are_audited() -> None:
    semantic_service, repository = service()
    claim_id = UUID(int=40)
    await semantic_service.create_claim(
        claim(claim_id), revision(claim_id, 1, "3.12"), (evidence(claim_id),)
    )
    await repository.append_claim_revision(
        revision(
            claim_id,
            2,
            "3.13",
            valid_from=FUTURE,
            recorded_at=KNOWN_FUTURE,
        ),
        expected_revision=1,
    )
    historical = await semantic_service.query_claims(
        TemporalClaimQuery(
            query_id=UUID(int=41),
            mode=TemporalQueryMode.BITEMPORAL,
            scopes=(SCOPE,),
            valid_at=datetime(2026, 8, 1, tzinfo=UTC),
            known_at=datetime(2027, 1, 5, tzinfo=UTC),
        )
    )
    future = await semantic_service.query_claims(
        TemporalClaimQuery(
            query_id=UUID(int=42),
            mode=TemporalQueryMode.BITEMPORAL,
            scopes=(SCOPE,),
            valid_at=datetime(2027, 2, 1, tzinfo=UTC),
            known_at=datetime(2027, 2, 1, tzinfo=UTC),
        )
    )
    assert [item.revision for item in historical.claims] == [1]
    assert [item.revision for item in future.claims] == [2]
    assert len(repository.accesses) == 2


@pytest.mark.asyncio
async def test_functional_conflicts_require_scope_and_temporal_overlap() -> None:
    semantic_service, _ = service()
    first, second = UUID(int=50), UUID(int=51)
    await semantic_service.create_claim(
        claim(first), revision(first, 1, "3.12"), (evidence(first),)
    )
    await semantic_service.create_claim(
        claim(second), revision(second, 1, "3.13"), (evidence(second),)
    )
    conflicts = await semantic_service.detect_contradictions(first)
    assert len(conflicts) == 1
    assert conflicts[0].rule_id == "functional_overlap.v1"


def contradiction_revision(
    contradiction_id: UUID,
    number: int,
    status: ContradictionStatus,
    claim_ids: tuple[UUID, UUID],
) -> ContradictionRevision:
    values = {
        "contradiction_id": contradiction_id,
        "revision": number,
        "previous_revision": None if number == 1 else number - 1,
        "status": status,
        "severity": ContradictionSeverity.HIGH,
        "claims": tuple(
            ClaimRevisionReference(claim_id=claim_id, revision=1) for claim_id in claim_ids
        ),
        "evidence_ids": (),
        "reason": "deterministic overlap",
        "resolver": (
            ACTOR
            if status is ContradictionStatus.RESOLVED
            or (number > 1 and status is ContradictionStatus.OPEN)
            else None
        ),
        "recorded_at": NOW,
    }
    return ContradictionRevision.model_validate(
        {
            **values,
            "content_hash": semantic_hash(
                ContradictionRevision.model_construct(**values).model_dump(mode="json")
            ),
        }
    )


@pytest.mark.asyncio
async def test_contradiction_resolution_is_append_only_and_reopenable() -> None:
    semantic_service, repository = service()
    claim_ids = (UUID(int=70), UUID(int=71))
    for claim_id, value in zip(claim_ids, ("3.12", "3.13"), strict=True):
        await semantic_service.create_claim(
            claim(claim_id), revision(claim_id, 1, value), (evidence(claim_id),)
        )
    contradiction_id = UUID(int=72)
    opened = contradiction_revision(contradiction_id, 1, ContradictionStatus.OPEN, claim_ids)
    await semantic_service.open_contradiction(
        ContradictionRecord(
            contradiction_id=contradiction_id,
            current_revision=1,
            current_status=ContradictionStatus.OPEN,
            severity=ContradictionSeverity.HIGH,
            created_at=NOW,
        ),
        opened,
    )
    resolved = contradiction_revision(contradiction_id, 2, ContradictionStatus.RESOLVED, claim_ids)
    resolution = ContradictionResolution(
        resolution_id=UUID(int=73),
        contradiction_id=contradiction_id,
        expected_revision=1,
        outcome=ContradictionResolutionOutcome.UNRESOLVED_PLURALITY,
        affected_claims=tuple(
            ClaimRevisionReference(claim_id=claim_id, revision=1) for claim_id in claim_ids
        ),
        reason="operator retained both grounded claims",
        decided_at=NOW,
        decided_by=ACTOR,
    )
    await semantic_service.transition_contradiction(
        resolved, expected_revision=1, resolution=resolution
    )
    assert (
        await semantic_service.transition_contradiction(
            resolved, expected_revision=1, resolution=resolution
        )
        == resolved
    )
    reopened = contradiction_revision(contradiction_id, 3, ContradictionStatus.OPEN, claim_ids)
    await semantic_service.transition_contradiction(reopened, expected_revision=2)
    assert [item.status for item in repository.contradiction_revisions[contradiction_id]] == [
        ContradictionStatus.OPEN,
        ContradictionStatus.RESOLVED,
        ContradictionStatus.OPEN,
    ]


@pytest.mark.asyncio
async def test_provider_contradiction_candidate_requires_trusted_confirmation() -> None:
    semantic_service, repository = service()
    claim_ids = (UUID(int=74), UUID(int=75))
    for claim_id, value in zip(claim_ids, ("3.12", "3.13"), strict=True):
        await semantic_service.create_claim(
            claim(claim_id), revision(claim_id, 1, value), (evidence(claim_id),)
        )
    contradiction_id = UUID(int=76)
    candidate = contradiction_revision(
        contradiction_id, 1, ContradictionStatus.CANDIDATE, claim_ids
    )
    await semantic_service.record_contradiction_candidate(
        ContradictionRecord(
            contradiction_id=contradiction_id,
            current_revision=1,
            current_status=ContradictionStatus.CANDIDATE,
            severity=ContradictionSeverity.HIGH,
            created_at=NOW,
        ),
        candidate,
    )
    unconfirmed = contradiction_revision(
        contradiction_id, 2, ContradictionStatus.OPEN, claim_ids
    ).model_copy(update={"resolver": None})
    with pytest.raises(SemanticPolicyError, match="trusted decision actor"):
        await semantic_service.transition_contradiction(unconfirmed, expected_revision=1)
    confirmed = contradiction_revision(contradiction_id, 2, ContradictionStatus.OPEN, claim_ids)
    await semantic_service.transition_contradiction(confirmed, expected_revision=1)
    assert repository.contradictions[contradiction_id].current_status is ContradictionStatus.OPEN


@pytest.mark.asyncio
async def test_wiki_is_deterministic_escaped_and_has_exact_lineage() -> None:
    semantic_service, repository = service()
    claim_id = UUID(int=60)
    item = claim(claim_id)
    await semantic_service.create_claim(
        item,
        revision(claim_id, 1, "3.12"),
        (evidence(claim_id),),
    )
    page = WikiPage(
        page_id=UUID(int=61),
        scope=SCOPE,
        canonical_subject_key="project:cognitive-os",
        page_type="subject",
        current_revision=0,
        created_at=NOW,
    )
    rendered = await semantic_service.render_wiki(
        page,
        TemporalClaimQuery(query_id=UUID(int=62), scopes=(SCOPE,)),
        expected_revision=0,
    )
    assert escape_markdown("<script>") == "\\<script\\>"
    assert (
        len(rendered.claim_refs) == 0
    )  # Proposed claims are intentionally not authoritative Wiki facts.
    assert repository.wiki_pages[page.page_id].current_revision == 1


@pytest.mark.asyncio
async def test_supported_wiki_lineage_and_identical_regeneration_are_idempotent() -> None:
    semantic_service, repository, events, store = eventful_service()
    claim_id = UUID(int=80)
    await semantic_service.create_claim(
        claim(claim_id), revision(claim_id, 1, "3.12"), (evidence(claim_id),)
    )
    promoted = revision(
        claim_id,
        2,
        "3.12",
        status=BeliefStatus.SUPPORTED,
        complete_confidence=True,
    )
    decision = ClaimPromotionDecision(
        decision_id=UUID(int=81),
        claim=ClaimRevisionReference(claim_id=claim_id, revision=1),
        outcome=ClaimPromotionOutcome.SUPPORTED,
        verifier_bundle_hash="d" * 64,
        registry_snapshot_hash="e" * 64,
        reason_codes=("verified",),
        decided_at=NOW,
        decided_by=ACTOR,
    )
    await events.record_promotion_decision(decision)
    promoted = promoted.model_copy(update={"promotion_decision_id": decision.decision_id})
    await semantic_service.transition_claim(
        promoted,
        expected_revision=1,
        decision=decision,
        evidence=(evidence(claim_id, 2),),
    )
    page = WikiPage(
        page_id=UUID(int=82),
        scope=SCOPE,
        canonical_subject_key="project:cognitive-os",
        page_type="subject",
        current_revision=0,
        created_at=NOW,
    )
    query = TemporalClaimQuery(query_id=UUID(int=83), scopes=(SCOPE,))
    first = await semantic_service.render_wiki(page, query, expected_revision=0)
    second = await semantic_service.render_wiki(page, query, expected_revision=1)
    assert first == second
    assert first.claim_refs[0].claim == ClaimRevisionReference(claim_id=claim_id, revision=2)
    assert len(repository.wiki_revisions[page.page_id]) == 1
    assert await semantic_service.verify_wiki_revision(page.page_id, 1)
    assert any(
        item.envelope.event_type == "semantic.wiki_page_regenerated" for item in store.events
    )


@pytest.mark.asyncio
async def test_promotion_gate_derives_snapshot_and_persists_before_transition() -> None:
    semantic_service, repository, events, store = eventful_service()
    claim_id = UUID(int=90)
    await semantic_service.create_claim(
        claim(claim_id), revision(claim_id, 1, "3.12"), (evidence(claim_id),)
    )
    promoted = revision(
        claim_id,
        2,
        "3.12",
        status=BeliefStatus.SUPPORTED,
        complete_confidence=True,
    )
    promoted_evidence = (evidence(claim_id, 2),)
    verifier_registry = build_builtin_registry()
    identifiers = iter(UUID(int=value) for value in range(1000, 1100))
    gate = SemanticPromotionGate(
        semantic_service,
        VerificationService(
            verifier_registry,
            VerifierEventService(store),  # type: ignore[arg-type]
        ),
        verifier_registry,
        events,
        clock=lambda: NOW,
        id_factory=lambda: next(identifiers),
    )
    decision = await gate.decide(
        promoted,
        promoted_evidence,
        task_run_id=UUID(int=91),
        actor=ACTOR,
    )
    assert decision.outcome is ClaimPromotionOutcome.SUPPORTED
    assert await events.promotion_decision_is_persisted(decision)
    promoted = promoted.model_copy(update={"promotion_decision_id": decision.decision_id})
    await semantic_service.transition_claim(
        promoted,
        expected_revision=1,
        decision=decision,
        evidence=promoted_evidence,
    )
    decision_position = next(
        item.global_position
        for item in store.events
        if item.envelope.event_type == "semantic.claim_promotion_decided"
    )
    transition_position = next(
        item.global_position
        for item in store.events
        if item.envelope.event_type == "semantic.claim_belief_changed"
    )
    assert decision_position < transition_position
    assert repository.claims[claim_id].current_belief_status is BeliefStatus.SUPPORTED


@pytest.mark.asyncio
async def test_promotion_gate_rejects_failed_or_missing_required_verifiers() -> None:
    semantic_service, _, events, store = eventful_service()
    claim_id = UUID(int=92)
    await semantic_service.create_claim(
        claim(claim_id), revision(claim_id, 1, "3.12"), (evidence(claim_id),)
    )
    promoted = revision(
        claim_id,
        2,
        "3.12",
        status=BeliefStatus.SUPPORTED,
        complete_confidence=True,
    )
    registry = build_builtin_registry()
    identifiers = iter(UUID(int=value) for value in range(1200, 1300))
    gate = SemanticPromotionGate(
        semantic_service,
        VerificationService(
            registry,
            VerifierEventService(store),  # type: ignore[arg-type]
        ),
        registry,
        events,
        clock=lambda: NOW,
        id_factory=lambda: next(identifiers),
    )
    rejected = await gate.decide(
        promoted,
        (),
        task_run_id=UUID(int=93),
        actor=ACTOR,
    )
    assert rejected.outcome is ClaimPromotionOutcome.REJECTED
    assert "semantic.evidence_minimum" in rejected.reason_codes

    incomplete_registry = VerifierRegistry()
    incomplete_registry.register_many(
        tuple(
            SemanticInvariantVerifier(capability)
            for capability in REQUIRED_SEMANTIC_PROMOTION_CAPABILITIES[:-1]
        )
    )
    identifiers = iter(UUID(int=value) for value in range(1300, 1400))
    incomplete_gate = SemanticPromotionGate(
        semantic_service,
        VerificationService(
            incomplete_registry,
            VerifierEventService(store),  # type: ignore[arg-type]
        ),
        incomplete_registry,
        events,
        clock=lambda: NOW,
        id_factory=lambda: next(identifiers),
    )
    with pytest.raises(VerifierNotFoundError, match="not registered"):
        await incomplete_gate.decide(
            promoted,
            (evidence(claim_id, 2),),
            task_run_id=UUID(int=94),
            actor=ACTOR,
        )
    assert not any(
        item.envelope.event_type == "semantic.claim_promotion_decided"
        and item.envelope.correlation_id == UUID(int=1300)
        for item in store.events
    )
