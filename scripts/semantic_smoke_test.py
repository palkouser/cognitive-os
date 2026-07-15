"""Run the credential-free Sprint 10 PostgreSQL semantic-memory smoke workflow."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import timedelta
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import text

from cognitive_os.application.services.memory_service import MemoryService
from cognitive_os.application.services.verification_service import VerificationService
from cognitive_os.config.semantic_memory_config import SemanticMemoryConfiguration
from cognitive_os.domain.memory import (
    MemoryScopeType,
    MemorySensitivity,
    MemoryType,
    MemoryWritePolicy,
)
from cognitive_os.domain.semantic_memory import (
    BeliefStatus,
    Claim,
    ClaimIdentity,
    ClaimRelation,
    ClaimRelationType,
    ClaimRevision,
    ClaimRevisionReference,
    ClaimTemporalInterval,
    ConfidenceDimensions,
    ContradictionRecord,
    ContradictionRevision,
    ContradictionSeverity,
    ContradictionStatus,
    EvidenceLink,
    SemanticActor,
    SemanticActorType,
    SemanticLiteral,
    SemanticLiteralKind,
    TemporalClaimQuery,
    TemporalQueryMode,
    WikiPage,
    claim_revision_hash,
    semantic_hash,
)
from cognitive_os.events.catalog import build_default_event_catalog
from cognitive_os.events.memory_event_service import MemoryEventService
from cognitive_os.events.semantic_memory_event_service import SemanticMemoryEventService
from cognitive_os.events.verifier_event_service import VerifierEventService
from cognitive_os.infrastructure.memory.postgres.repository import PostgresMemoryRepository
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine
from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore
from cognitive_os.infrastructure.semantic_memory.postgres.repository import (
    PostgresSemanticMemoryRepository,
)
from cognitive_os.memory.fixtures import accepted_coding_trajectory_fixture
from cognitive_os.memory.ingestion import CodingTrajectoryIngestionService
from cognitive_os.semantic_memory.beliefs import aggregate_confidence
from cognitive_os.semantic_memory.compilation import SemanticExtractionService
from cognitive_os.semantic_memory.fixtures import project_version_proposal
from cognitive_os.semantic_memory.grounding import TrustedSourceResolver
from cognitive_os.semantic_memory.predicates import build_default_predicate_registry
from cognitive_os.semantic_memory.promotion import SemanticPromotionGate
from cognitive_os.semantic_memory.service import SemanticMemoryService
from cognitive_os.verification.factory import build_builtin_registry
from cognitive_os.verification.semantic import REQUIRED_SEMANTIC_PROMOTION_CAPABILITIES

ACTOR = SemanticActor(
    actor_type=SemanticActorType.APPROVED_INTERNAL_SERVICE,
    actor_id="sprint-10-smoke",
)


def stable_id(label: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"cognitive-os:sprint-10-smoke:{label}")


def revised_evidence(original: EvidenceLink, claim_id: UUID, revision: int) -> EvidenceLink:
    return original.model_copy(
        update={
            "evidence_id": stable_id(f"evidence:{claim_id}:{revision}"),
            "claim": ClaimRevisionReference(claim_id=claim_id, revision=revision),
            "created_by": ACTOR,
        }
    )


def claim_revision(
    *,
    claim_id: UUID,
    revision: int,
    value: str,
    status: BeliefStatus,
    interval: ClaimTemporalInterval,
    recorded_at,
    evidence: tuple[EvidenceLink, ...],
    confidence: ConfidenceDimensions,
    reason: str,
    decision_id: UUID | None = None,
) -> ClaimRevision:
    semantic_value = SemanticLiteral(literal_kind=SemanticLiteralKind.VERSION, value=value)
    evidence_hash = semantic_hash([item.model_dump(mode="json") for item in evidence])
    return ClaimRevision(
        claim_id=claim_id,
        revision=revision,
        previous_revision=None if revision == 1 else revision - 1,
        object=semantic_value,
        statement=f"The project uses Python {value}.",
        belief_status=status,
        confidence=confidence,
        valid_interval=interval,
        reason=reason,
        recorded_at=recorded_at,
        created_by=ACTOR,
        evidence_snapshot_hash=evidence_hash,
        promotion_decision_id=decision_id,
        content_hash=claim_revision_hash(
            claim_id=claim_id,
            revision=revision,
            object_value=semantic_value,
            statement=f"The project uses Python {value}.",
            belief_status=status,
            confidence=confidence,
            valid_interval=interval,
            reason=reason,
            evidence_snapshot_hash=evidence_hash,
        ),
    )


def contradiction_revision(
    contradiction_id: UUID,
    claims: tuple[ClaimRevisionReference, ClaimRevisionReference],
    recorded_at,
) -> ContradictionRevision:
    values = {
        "contradiction_id": contradiction_id,
        "revision": 1,
        "previous_revision": None,
        "status": ContradictionStatus.OPEN,
        "severity": ContradictionSeverity.CRITICAL,
        "claims": claims,
        "evidence_ids": (),
        "reason": "deterministic overlapping functional values",
        "resolver": None,
        "recorded_at": recorded_at,
    }
    return ContradictionRevision.model_validate(
        {
            **values,
            "content_hash": semantic_hash(
                ContradictionRevision.model_construct(**values).model_dump(mode="json")
            ),
        }
    )


async def run() -> int:
    database_url = os.environ.get("COGOS_DATABASE_URL")
    if not database_url:
        raise RuntimeError("COGOS_DATABASE_URL is required")
    engine = create_postgres_engine(database_url, pool_size=2, max_overflow=0)
    try:
        async with engine.connect() as connection:
            database_name = str(await connection.scalar(text("SELECT current_database()")))
        if not database_name.endswith("_test"):
            raise RuntimeError("semantic smoke requires an isolated _test database")
        catalog = build_default_event_catalog()
        event_store = PostgresEventStore(engine, catalog)
        memory_repository = PostgresMemoryRepository(engine)
        memory_policy = MemoryWritePolicy(
            allowed_types=frozenset(MemoryType),
            allowed_scopes=frozenset(MemoryScopeType),
            maximum_sensitivity=MemorySensitivity.INTERNAL,
        )
        trajectory = accepted_coding_trajectory_fixture()
        manifest = await CodingTrajectoryIngestionService(
            MemoryService(
                memory_repository,
                memory_policy,
                event_service=MemoryEventService(event_store),
            )
        ).ingest(trajectory, trajectory.canonical_hash())
        source = None
        for memory_id in manifest.memory_ids:
            current = await memory_repository.get_current(memory_id)
            if current is not None and current[0].memory_type is MemoryType.CODE_CONTEXT:
                source = current
                break
        if source is None:
            raise RuntimeError("verified code-context memory source is missing")

        repository = PostgresSemanticMemoryRepository(engine)
        registry = build_default_predicate_registry()
        semantic_events = SemanticMemoryEventService(event_store)
        semantic = SemanticMemoryService(
            repository,
            registry,
            SemanticMemoryConfiguration(),
            event_service=semantic_events,
            source_resolver=TrustedSourceResolver(memory_repository),
        )
        extraction = await SemanticExtractionService(
            semantic, registry, events=semantic_events
        ).commit(
            project_version_proposal(source[0], source[1], registry),
            scope=source[0].scope,
            sensitivity=source[1].sensitivity,
            actor=ACTOR,
            recorded_at=source[1].created_at,
        )
        first_ref = extraction.claims[0]
        first_claim = await repository.get_claim(first_ref.claim_id)
        first_revision = await repository.get_claim_revision(first_ref.claim_id, 1)
        first_evidence = await repository.list_evidence(first_ref.claim_id, revision=1)
        if first_claim is None or first_revision is None or not first_evidence:
            raise RuntimeError("proposed project-version claim is incomplete")
        successor_time = source[1].created_at + timedelta(days=180)
        promoted_evidence = (revised_evidence(first_evidence[0], first_ref.claim_id, 2),)
        promoted = claim_revision(
            claim_id=first_ref.claim_id,
            revision=2,
            value=str(first_revision.object.value),
            status=BeliefStatus.SUPPORTED,
            interval=ClaimTemporalInterval(
                valid_from=source[1].created_at, valid_to=successor_time
            ),
            recorded_at=source[1].created_at,
            evidence=promoted_evidence,
            confidence=aggregate_confidence(
                extraction=1,
                source=1,
                grounding=1,
                evidence=1,
                verification=1,
                consistency=1,
            ),
            reason="registered semantic verifier bundle passed",
        )
        verifier_registry = build_builtin_registry()
        gate_ids = iter(stable_id(f"promotion-gate:{index}") for index in range(100))
        decision = await SemanticPromotionGate(
            semantic,
            VerificationService(verifier_registry, VerifierEventService(event_store)),
            verifier_registry,
            semantic_events,
            clock=lambda: source[1].created_at,
            id_factory=lambda: next(gate_ids),
        ).decide(
            promoted,
            promoted_evidence,
            task_run_id=stable_id("task-run"),
            actor=ACTOR,
        )
        promoted = promoted.model_copy(update={"promotion_decision_id": decision.decision_id})
        verifier_count = len(REQUIRED_SEMANTIC_PROMOTION_CAPABILITIES)
        await semantic.transition_claim(
            promoted,
            expected_revision=1,
            decision=decision,
            evidence=promoted_evidence,
        )

        async def create_version(label: str, value: str, valid_from) -> ClaimRevision:
            claim_id = stable_id(f"claim:{label}")
            evidence = (revised_evidence(first_evidence[0], claim_id, 1),)
            revision = claim_revision(
                claim_id=claim_id,
                revision=1,
                value=value,
                status=BeliefStatus.PROPOSED,
                interval=ClaimTemporalInterval(valid_from=valid_from),
                recorded_at=valid_from,
                evidence=evidence,
                confidence=aggregate_confidence(extraction=1),
                reason=f"{label} deterministic fixture",
            )
            claim = Claim(
                identity=ClaimIdentity(
                    claim_id=claim_id,
                    scope=source[0].scope,
                    canonical_subject_key="project:cognitive-os",
                    predicate_id="project.python_version",
                ),
                current_revision=1,
                current_belief_status=BeliefStatus.PROPOSED,
                sensitivity=MemorySensitivity.INTERNAL,
                created_at=valid_from,
                created_by=ACTOR,
                idempotency_key=semantic_hash({"label": label, "source": str(source[0].memory_id)}),
            )
            await semantic.create_claim(claim, revision, evidence)
            return revision

        successor = await create_version("successor", "3.13", successor_time)
        overlapping = await create_version("overlap", "3.14", successor_time + timedelta(days=1))
        await semantic.add_claim_relation(
            ClaimRelation(
                relation_id=stable_id("relation:successor"),
                source=ClaimRevisionReference(
                    claim_id=successor.claim_id, revision=successor.revision
                ),
                target=ClaimRevisionReference(claim_id=promoted.claim_id, revision=2),
                relation_type=ClaimRelationType.SUPERSEDES,
                valid_interval=successor.valid_interval,
                provenance=first_evidence[0].source,
                created_at=successor.recorded_at,
            )
        )
        if await semantic.detect_contradictions(promoted.claim_id):
            raise RuntimeError("non-overlapping temporal successor was marked contradictory")
        candidates = await semantic.detect_contradictions(successor.claim_id)
        if len(candidates) != 1:
            raise RuntimeError("overlapping functional contradiction was not detected exactly")
        contradiction_id = stable_id("contradiction")
        contradiction = contradiction_revision(
            contradiction_id,
            candidates[0].claims,
            overlapping.recorded_at,
        )
        await semantic.open_contradiction(
            ContradictionRecord(
                contradiction_id=contradiction_id,
                current_revision=1,
                current_status=ContradictionStatus.OPEN,
                severity=ContradictionSeverity.CRITICAL,
                created_at=overlapping.recorded_at,
            ),
            contradiction,
        )

        current_query = TemporalClaimQuery(
            query_id=stable_id("query:current"), scopes=(source[0].scope,)
        )
        historical_query = TemporalClaimQuery(
            query_id=stable_id("query:historical"),
            mode=TemporalQueryMode.BITEMPORAL,
            scopes=(source[0].scope,),
            valid_at=source[1].created_at + timedelta(days=1),
            known_at=successor_time - timedelta(days=1),
        )
        current = await semantic.query_claims(current_query)
        historical = await semantic.query_claims(historical_query)
        current_page = await semantic.render_wiki(
            WikiPage(
                page_id=stable_id("wiki:current"),
                scope=source[0].scope,
                canonical_subject_key="project:cognitive-os",
                page_type="subject",
                current_revision=0,
                created_at=source[1].created_at,
            ),
            current_query.model_copy(update={"query_id": stable_id("wiki-query:current")}),
            expected_revision=0,
        )
        historical_page = await semantic.render_wiki(
            WikiPage(
                page_id=stable_id("wiki:historical"),
                scope=source[0].scope,
                canonical_subject_key="project:cognitive-os",
                page_type="subject-history",
                current_revision=0,
                created_at=source[1].created_at,
            ),
            historical_query.model_copy(update={"query_id": stable_id("wiki-query:historical")}),
            expected_revision=0,
        )
        async with engine.connect() as connection:
            access_count = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.semantic_accesses "
                        "WHERE query_id IN (:current, :historical, :wiki_current, :wiki_historical)"
                    ),
                    {
                        "current": current_query.query_id,
                        "historical": historical_query.query_id,
                        "wiki_current": stable_id("wiki-query:current"),
                        "wiki_historical": stable_id("wiki-query:historical"),
                    },
                )
                or 0
            )
            wiki_access_count = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.semantic_accesses "
                        "WHERE used_in_wiki AND query_id IN (:current, :historical)"
                    ),
                    {
                        "current": stable_id("wiki-query:current"),
                        "historical": stable_id("wiki-query:historical"),
                    },
                )
                or 0
            )
        result = {
            "access_records": access_count,
            "claims": len(current.claims),
            "contradictions": len(await repository.list_contradictions()),
            "historical_claims": len(historical.claims),
            "historical_wiki_lineage": len(historical_page.claim_refs),
            "relations": len(await repository.list_claim_relations(successor.claim_id)),
            "verifiers": verifier_count,
            "wiki_access_records": wiki_access_count,
            "wiki_lineage": len(current_page.claim_refs),
        }
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        passed = (
            result["claims"] == 3
            and result["contradictions"] == 1
            and result["historical_claims"] == 1
            and result["historical_wiki_lineage"] == 1
            and result["relations"] == 1
            and result["verifiers"] == len(REQUIRED_SEMANTIC_PROMOTION_CAPABILITIES)
            and result["wiki_access_records"] == 4
            and result["wiki_lineage"] == 1
            and result["access_records"] == 8
        )
        return 0 if passed else 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
