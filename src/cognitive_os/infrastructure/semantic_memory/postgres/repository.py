"""Transactional PostgreSQL repository for temporal semantic memory."""

from __future__ import annotations

from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import and_, insert, or_, select, text
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from cognitive_os.domain.memory import MemoryScope
from cognitive_os.domain.semantic_memory import (
    Claim,
    ClaimIdentity,
    ClaimRelation,
    ClaimRevision,
    ContradictionRecord,
    ContradictionRevision,
    EvidenceLink,
    SemanticAccessRecord,
    SemanticActor,
    SemanticObservation,
    SemanticQueryResult,
    SemanticSourceRef,
    SemanticValue,
    TemporalClaimQuery,
    WikiPage,
    WikiPageRevision,
    semantic_hash,
)
from cognitive_os.infrastructure.postgres.engine import postgres_transaction
from cognitive_os.semantic_memory.errors import SemanticConcurrencyError, SemanticIntegrityError

from .tables import (
    semantic_accesses,
    semantic_claim_evidence,
    semantic_claim_relations,
    semantic_claim_revisions,
    semantic_claims,
    semantic_contradiction_claims,
    semantic_contradiction_revisions,
    semantic_contradictions,
    semantic_observations,
    wiki_page_claims,
    wiki_page_revisions,
    wiki_pages,
)

_SEMANTIC_VALUE: TypeAdapter[SemanticValue] = TypeAdapter(SemanticValue)


def _claim_from_row(row: RowMapping) -> Claim:
    return Claim(
        identity=ClaimIdentity(
            claim_id=row["claim_id"],
            scope=MemoryScope(scope_type=row["scope_type"], scope_id=row["scope_id"]),
            canonical_subject_key=row["canonical_subject_key"],
            predicate_id=row["predicate_id"],
        ),
        current_revision=row["current_revision"],
        current_belief_status=row["current_belief_status"],
        sensitivity=row["sensitivity"],
        created_at=row["created_at"],
        created_by=SemanticActor(actor_type=row["created_by_type"], actor_id=row["created_by_id"]),
        idempotency_key=row["idempotency_key"],
    )


def _revision_from_row(row: RowMapping) -> ClaimRevision:
    return ClaimRevision.model_validate(
        {
            "claim_id": row["claim_id"],
            "revision": row["revision"],
            "previous_revision": row["previous_revision"],
            "object": _SEMANTIC_VALUE.validate_python(row["object_json"]),
            "statement": row["statement"],
            "belief_status": row["belief_status"],
            "confidence": row["confidence_json"],
            "valid_interval": {
                "valid_from": row["valid_from"],
                "valid_to": row["valid_to"],
            },
            "reason": row["reason"],
            "recorded_at": row["recorded_at"],
            "created_by": {
                "actor_type": row["created_by_type"],
                "actor_id": row["created_by_id"],
            },
            "evidence_snapshot_hash": row["evidence_snapshot_hash"],
            "promotion_decision_id": row["promotion_decision_id"],
            "content_hash": row["content_hash"],
        }
    )


def _revision_values(revision: ClaimRevision) -> dict[str, object]:
    return {
        "claim_id": revision.claim_id,
        "revision": revision.revision,
        "previous_revision": revision.previous_revision,
        "object_json": revision.object.model_dump(mode="json"),
        "statement": revision.statement,
        "belief_status": revision.belief_status.value,
        "confidence_json": revision.confidence.model_dump(mode="json"),
        "overall_confidence": revision.confidence.overall_confidence,
        "valid_from": revision.valid_interval.valid_from,
        "valid_to": revision.valid_interval.valid_to,
        "reason": revision.reason,
        "recorded_at": revision.recorded_at,
        "created_by_type": revision.created_by.actor_type.value,
        "created_by_id": revision.created_by.actor_id,
        "evidence_snapshot_hash": revision.evidence_snapshot_hash,
        "promotion_decision_id": revision.promotion_decision_id,
        "content_hash": revision.content_hash,
    }


def _evidence_values(evidence: EvidenceLink) -> dict[str, object]:
    return {
        "evidence_id": evidence.evidence_id,
        "claim_id": evidence.claim.claim_id,
        "claim_revision": evidence.claim.revision,
        "source_type": evidence.source.source_type.value,
        "source_id": evidence.source.source_id,
        "source_revision": evidence.source.revision,
        "source_hash": evidence.source.content_hash,
        "source_span_json": evidence.source_span.model_dump(mode="json"),
        "relation": evidence.relation.value,
        "strength": evidence.strength,
        "created_at": evidence.created_at,
        "created_by_type": evidence.created_by.actor_type.value,
        "created_by_id": evidence.created_by.actor_id,
    }


def _observation_from_row(row: RowMapping) -> SemanticObservation:
    return SemanticObservation.model_validate(
        {
            "observation_id": row["observation_id"],
            "content": row["content"],
            "normalized_content": row["normalized_content"],
            "source_refs": row["source_refs_json"],
            "source_spans": row["source_spans_json"],
            "observed_at": row["observed_at"],
            "recorded_at": row["recorded_at"],
            "scope": {"scope_type": row["scope_type"], "scope_id": row["scope_id"]},
            "confidence": row["confidence"],
            "sensitivity": row["sensitivity"],
            "created_by": {
                "actor_type": row["created_by_type"],
                "actor_id": row["created_by_id"],
            },
            "content_hash": row["content_hash"],
            "idempotency_key": row["idempotency_key"],
        }
    )


def _evidence_from_row(row: RowMapping) -> EvidenceLink:
    return EvidenceLink.model_validate(
        {
            "evidence_id": row["evidence_id"],
            "claim": {"claim_id": row["claim_id"], "revision": row["claim_revision"]},
            "source": {
                "source_type": row["source_type"],
                "source_id": row["source_id"],
                "revision": row["source_revision"],
                "content_hash": row["source_hash"],
            },
            "source_span": row["source_span_json"],
            "relation": row["relation"],
            "strength": row["strength"],
            "created_at": row["created_at"],
            "created_by": {
                "actor_type": row["created_by_type"],
                "actor_id": row["created_by_id"],
            },
        }
    )


def _relation_from_row(row: RowMapping) -> ClaimRelation:
    return ClaimRelation.model_validate(
        {
            "relation_id": row["relation_id"],
            "source": {
                "claim_id": row["source_claim_id"],
                "revision": row["source_revision"],
            },
            "target": {
                "claim_id": row["target_claim_id"],
                "revision": row["target_revision"],
            },
            "relation_type": row["relation_type"],
            "valid_interval": {
                "valid_from": row["valid_from"],
                "valid_to": row["valid_to"],
            },
            "provenance": SemanticSourceRef.model_validate(row["provenance_json"]),
            "created_at": row["created_at"],
        }
    )


class PostgresSemanticMemoryRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def record_observation(self, observation: SemanticObservation) -> SemanticObservation:
        values = {
            "observation_id": observation.observation_id,
            "idempotency_key": observation.idempotency_key,
            "content": observation.content,
            "normalized_content": observation.normalized_content,
            "source_refs_json": [item.model_dump(mode="json") for item in observation.source_refs],
            "source_spans_json": [
                item.model_dump(mode="json") for item in observation.source_spans
            ],
            "observed_at": observation.observed_at,
            "recorded_at": observation.recorded_at,
            "scope_type": observation.scope.scope_type.value,
            "scope_id": observation.scope.scope_id,
            "confidence": observation.confidence,
            "sensitivity": observation.sensitivity.value,
            "created_by_type": observation.created_by.actor_type.value,
            "created_by_id": observation.created_by.actor_id,
            "content_hash": observation.content_hash,
        }
        try:
            async with postgres_transaction(self._engine) as connection:
                await connection.execute(insert(semantic_observations).values(**values))
            return observation
        except IntegrityError:
            async with self._engine.connect() as connection:
                row = (
                    (
                        await connection.execute(
                            select(semantic_observations).where(
                                semantic_observations.c.idempotency_key
                                == observation.idempotency_key
                            )
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
            if row is None or row["content_hash"] != observation.content_hash:
                raise SemanticConcurrencyError("semantic observation identity conflict") from None
            return observation

    async def get_observation(self, observation_id: UUID) -> SemanticObservation | None:
        async with self._engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        select(semantic_observations).where(
                            semantic_observations.c.observation_id == observation_id
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            return None
        return _observation_from_row(row)

    async def list_observations(
        self, *, source_id: UUID | None = None, limit: int = 100
    ) -> tuple[SemanticObservation, ...]:
        if limit < 1 or limit > 500:
            raise ValueError("observation limit must be between 1 and 500")
        statement = select(semantic_observations).order_by(
            semantic_observations.c.recorded_at, semantic_observations.c.observation_id
        )
        if source_id is not None:
            statement = statement.where(
                semantic_observations.c.source_refs_json.contains([{"source_id": str(source_id)}])
            )
        async with self._engine.connect() as connection:
            rows = (await connection.execute(statement.limit(limit))).mappings().all()
        return tuple(_observation_from_row(row) for row in rows)

    async def create_claim(
        self, claim: Claim, revision: ClaimRevision
    ) -> tuple[Claim, ClaimRevision]:
        return await self.create_claim_with_evidence(claim, revision, ())

    async def create_claim_with_evidence(
        self, claim: Claim, revision: ClaimRevision, evidence: tuple[EvidenceLink, ...]
    ) -> tuple[Claim, ClaimRevision]:
        if len({item.evidence_id for item in evidence}) != len(evidence) or any(
            item.claim.claim_id != claim.identity.claim_id or item.claim.revision != 1
            for item in evidence
        ):
            raise SemanticIntegrityError("claim creation evidence is invalid or duplicated")
        async with self._engine.connect() as connection:
            existing_id = await connection.scalar(
                select(semantic_claims.c.claim_id).where(
                    semantic_claims.c.idempotency_key == claim.idempotency_key
                )
            )
        if existing_id is not None:
            existing_claim = await self.get_claim(existing_id)
            existing_revision = await self.get_claim_revision(existing_id, 1)
            if existing_claim is None or existing_revision is None:
                raise SemanticIntegrityError("claim idempotency identity is incomplete")
            if (
                existing_claim.identity != claim.identity
                or existing_revision.content_hash != revision.content_hash
            ):
                raise SemanticConcurrencyError("claim idempotency key has different content")
            return existing_claim, existing_revision
        try:
            async with postgres_transaction(self._engine) as connection:
                await connection.execute(
                    insert(semantic_claims).values(
                        claim_id=claim.identity.claim_id,
                        idempotency_key=claim.idempotency_key,
                        scope_type=claim.identity.scope.scope_type.value,
                        scope_id=claim.identity.scope.scope_id,
                        canonical_subject_key=claim.identity.canonical_subject_key,
                        predicate_id=claim.identity.predicate_id,
                        current_revision=claim.current_revision,
                        current_belief_status=claim.current_belief_status.value,
                        sensitivity=claim.sensitivity.value,
                        created_at=claim.created_at,
                        created_by_type=claim.created_by.actor_type.value,
                        created_by_id=claim.created_by.actor_id,
                    )
                )
                await connection.execute(
                    insert(semantic_claim_revisions).values(**_revision_values(revision))
                )
                if evidence:
                    await connection.execute(
                        insert(semantic_claim_evidence),
                        [_evidence_values(item) for item in evidence],
                    )
            return claim, revision
        except IntegrityError as error:
            raise SemanticConcurrencyError("semantic claim identity conflict") from error
        except SQLAlchemyError as error:
            raise SemanticIntegrityError("PostgreSQL semantic claim creation failed") from error

    async def append_claim_revision(
        self, revision: ClaimRevision, *, expected_revision: int
    ) -> ClaimRevision:
        try:
            async with postgres_transaction(self._engine) as connection:
                await connection.execute(
                    insert(semantic_claim_revisions).values(**_revision_values(revision))
                )
                advanced = await connection.scalar(
                    text(
                        "SELECT cognitive_os.advance_semantic_claim("
                        ":claim_id, :expected_revision, :next_revision, :next_status)"
                    ),
                    {
                        "claim_id": revision.claim_id,
                        "expected_revision": expected_revision,
                        "next_revision": revision.revision,
                        "next_status": revision.belief_status.value,
                    },
                )
                if not advanced:
                    raise SemanticConcurrencyError("stale expected claim revision")
            return revision
        except SemanticConcurrencyError:
            raise
        except IntegrityError as error:
            raise SemanticConcurrencyError("semantic claim revision conflict") from error

    async def append_claim_revision_with_evidence(
        self,
        revision: ClaimRevision,
        evidence: tuple[EvidenceLink, ...],
        *,
        expected_revision: int,
    ) -> ClaimRevision:
        if any(
            item.claim.claim_id != revision.claim_id or item.claim.revision != revision.revision
            for item in evidence
        ):
            raise SemanticIntegrityError("evidence must target the appended claim revision")
        try:
            async with postgres_transaction(self._engine) as connection:
                await connection.execute(
                    insert(semantic_claim_revisions).values(**_revision_values(revision))
                )
                if evidence:
                    await connection.execute(
                        insert(semantic_claim_evidence),
                        [_evidence_values(item) for item in evidence],
                    )
                advanced = await connection.scalar(
                    text(
                        "SELECT cognitive_os.advance_semantic_claim("
                        ":claim_id, :expected_revision, :next_revision, :next_status)"
                    ),
                    {
                        "claim_id": revision.claim_id,
                        "expected_revision": expected_revision,
                        "next_revision": revision.revision,
                        "next_status": revision.belief_status.value,
                    },
                )
                if not advanced:
                    raise SemanticConcurrencyError("stale expected claim revision")
            return revision
        except SemanticConcurrencyError:
            raise
        except IntegrityError as error:
            raise SemanticConcurrencyError("semantic claim revision conflict") from error

    async def get_claim(self, claim_id: UUID) -> Claim | None:
        async with self._engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        select(semantic_claims).where(semantic_claims.c.claim_id == claim_id)
                    )
                )
                .mappings()
                .one_or_none()
            )
        return _claim_from_row(row) if row is not None else None

    async def get_claim_revision(self, claim_id: UUID, revision: int) -> ClaimRevision | None:
        async with self._engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        select(semantic_claim_revisions).where(
                            and_(
                                semantic_claim_revisions.c.claim_id == claim_id,
                                semantic_claim_revisions.c.revision == revision,
                            )
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
        return _revision_from_row(row) if row is not None else None

    async def list_claim_history(
        self, claim_id: UUID, *, limit: int = 100
    ) -> tuple[ClaimRevision, ...]:
        if limit < 1 or limit > 500:
            raise ValueError("claim history limit must be between 1 and 500")
        async with self._engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        select(semantic_claim_revisions)
                        .where(semantic_claim_revisions.c.claim_id == claim_id)
                        .order_by(semantic_claim_revisions.c.revision)
                        .limit(limit)
                    )
                )
                .mappings()
                .all()
            )
        return tuple(_revision_from_row(row) for row in rows)

    async def attach_evidence(self, evidence: EvidenceLink) -> EvidenceLink:
        try:
            async with postgres_transaction(self._engine) as connection:
                await connection.execute(
                    insert(semantic_claim_evidence).values(**_evidence_values(evidence))
                )
            return evidence
        except IntegrityError as error:
            raise SemanticIntegrityError("semantic evidence is invalid or duplicated") from error

    async def list_evidence(
        self, claim_id: UUID, *, revision: int | None = None
    ) -> tuple[EvidenceLink, ...]:
        statement = (
            select(semantic_claim_evidence)
            .where(semantic_claim_evidence.c.claim_id == claim_id)
            .order_by(
                semantic_claim_evidence.c.claim_revision,
                semantic_claim_evidence.c.evidence_id,
            )
        )
        if revision is not None:
            statement = statement.where(semantic_claim_evidence.c.claim_revision == revision)
        async with self._engine.connect() as connection:
            rows = (await connection.execute(statement)).mappings().all()
        return tuple(_evidence_from_row(row) for row in rows)

    async def add_claim_relation(self, relation: ClaimRelation) -> ClaimRelation:
        try:
            async with postgres_transaction(self._engine) as connection:
                await connection.execute(
                    insert(semantic_claim_relations).values(
                        relation_id=relation.relation_id,
                        source_claim_id=relation.source.claim_id,
                        source_revision=relation.source.revision,
                        target_claim_id=relation.target.claim_id,
                        target_revision=relation.target.revision,
                        relation_type=relation.relation_type.value,
                        valid_from=relation.valid_interval.valid_from,
                        valid_to=relation.valid_interval.valid_to,
                        provenance_json=relation.provenance.model_dump(mode="json"),
                        created_at=relation.created_at,
                    )
                )
            return relation
        except IntegrityError as error:
            raise SemanticIntegrityError("semantic claim relation is invalid") from error

    async def list_claim_relations(self, claim_id: UUID) -> tuple[ClaimRelation, ...]:
        statement = (
            select(semantic_claim_relations)
            .where(
                or_(
                    semantic_claim_relations.c.source_claim_id == claim_id,
                    semantic_claim_relations.c.target_claim_id == claim_id,
                )
            )
            .order_by(semantic_claim_relations.c.relation_id)
        )
        async with self._engine.connect() as connection:
            rows = (await connection.execute(statement)).mappings().all()
        return tuple(_relation_from_row(row) for row in rows)

    async def create_contradiction(
        self, contradiction: ContradictionRecord, revision: ContradictionRevision
    ) -> tuple[ContradictionRecord, ContradictionRevision]:
        existing = await self.get_contradiction(contradiction.contradiction_id)
        if existing is not None:
            first = await self.get_contradiction_revision(contradiction.contradiction_id, 1)
            if first is None:
                raise SemanticIntegrityError("contradiction identity has no first revision")
            return existing, first
        try:
            async with postgres_transaction(self._engine) as connection:
                await connection.execute(
                    insert(semantic_contradictions).values(
                        contradiction_id=contradiction.contradiction_id,
                        current_revision=contradiction.current_revision,
                        current_status=contradiction.current_status.value,
                        severity=contradiction.severity.value,
                        created_at=contradiction.created_at,
                    )
                )
                await self._insert_contradiction_revision(connection, revision)
            return contradiction, revision
        except IntegrityError as error:
            raise SemanticConcurrencyError("semantic contradiction identity conflict") from error

    async def _insert_contradiction_revision(
        self, connection: AsyncConnection, revision: ContradictionRevision
    ) -> None:
        await connection.execute(
            insert(semantic_contradiction_revisions).values(
                contradiction_id=revision.contradiction_id,
                revision=revision.revision,
                previous_revision=revision.previous_revision,
                status=revision.status.value,
                severity=revision.severity.value,
                evidence_ids_json=[str(item) for item in revision.evidence_ids],
                reason=revision.reason,
                resolver_json=revision.resolver.model_dump(mode="json")
                if revision.resolver
                else None,
                recorded_at=revision.recorded_at,
                content_hash=revision.content_hash,
            )
        )
        await connection.execute(
            insert(semantic_contradiction_claims),
            [
                {
                    "contradiction_id": revision.contradiction_id,
                    "contradiction_revision": revision.revision,
                    "claim_id": item.claim_id,
                    "claim_revision": item.revision,
                }
                for item in revision.claims
            ],
        )

    async def append_contradiction_revision(
        self, revision: ContradictionRevision, *, expected_revision: int
    ) -> ContradictionRevision:
        async with postgres_transaction(self._engine) as connection:
            await self._insert_contradiction_revision(connection, revision)
            advanced = await connection.scalar(
                text(
                    "SELECT cognitive_os.advance_semantic_contradiction("
                    ":id, :expected, :next, :status)"
                ),
                {
                    "id": revision.contradiction_id,
                    "expected": expected_revision,
                    "next": revision.revision,
                    "status": revision.status.value,
                },
            )
            if not advanced:
                raise SemanticConcurrencyError("stale expected contradiction revision")
        return revision

    async def get_contradiction(self, contradiction_id: UUID) -> ContradictionRecord | None:
        async with self._engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        select(semantic_contradictions).where(
                            semantic_contradictions.c.contradiction_id == contradiction_id
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
        return (
            ContradictionRecord(
                contradiction_id=row["contradiction_id"],
                current_revision=row["current_revision"],
                current_status=row["current_status"],
                severity=row["severity"],
                created_at=row["created_at"],
            )
            if row is not None
            else None
        )

    async def get_contradiction_revision(
        self, contradiction_id: UUID, revision: int
    ) -> ContradictionRevision | None:
        async with self._engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        select(semantic_contradiction_revisions).where(
                            and_(
                                semantic_contradiction_revisions.c.contradiction_id
                                == contradiction_id,
                                semantic_contradiction_revisions.c.revision == revision,
                            )
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                return None
            claims = (
                (
                    await connection.execute(
                        select(semantic_contradiction_claims).where(
                            and_(
                                semantic_contradiction_claims.c.contradiction_id
                                == contradiction_id,
                                semantic_contradiction_claims.c.contradiction_revision == revision,
                            )
                        )
                    )
                )
                .mappings()
                .all()
            )
        return ContradictionRevision.model_validate(
            {
                "contradiction_id": contradiction_id,
                "revision": revision,
                "previous_revision": row["previous_revision"],
                "status": row["status"],
                "severity": row["severity"],
                "claims": [
                    {"claim_id": item["claim_id"], "revision": item["claim_revision"]}
                    for item in claims
                ],
                "evidence_ids": row["evidence_ids_json"],
                "reason": row["reason"],
                "resolver": row["resolver_json"],
                "recorded_at": row["recorded_at"],
                "content_hash": row["content_hash"],
            }
        )

    async def list_contradictions(self) -> tuple[ContradictionRecord, ...]:
        async with self._engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        select(semantic_contradictions).order_by(
                            semantic_contradictions.c.contradiction_id
                        )
                    )
                )
                .mappings()
                .all()
            )
        return tuple(
            ContradictionRecord(
                contradiction_id=row["contradiction_id"],
                current_revision=row["current_revision"],
                current_status=row["current_status"],
                severity=row["severity"],
                created_at=row["created_at"],
            )
            for row in rows
        )

    async def list_contradiction_history(
        self, contradiction_id: UUID
    ) -> tuple[ContradictionRevision, ...]:
        current = await self.get_contradiction(contradiction_id)
        if current is None:
            return ()
        revisions = []
        for number in range(1, current.current_revision + 1):
            revision = await self.get_contradiction_revision(contradiction_id, number)
            if revision is None:
                raise SemanticIntegrityError("contradiction revision continuity gap")
            revisions.append(revision)
        return tuple(revisions)

    async def query_claims(self, query: TemporalClaimQuery) -> SemanticQueryResult:
        scopes = tuple(
            and_(
                semantic_claims.c.scope_type == scope.scope_type.value,
                semantic_claims.c.scope_id == scope.scope_id,
            )
            for scope in query.scopes
        )
        statement = (
            select(semantic_claim_revisions)
            .join(
                semantic_claims,
                semantic_claims.c.claim_id == semantic_claim_revisions.c.claim_id,
            )
            .where(or_(*scopes))
            .where(
                semantic_claim_revisions.c.belief_status.in_(
                    [item.value for item in query.belief_statuses]
                )
            )
        )
        if query.subject_key:
            statement = statement.where(
                semantic_claims.c.canonical_subject_key == query.subject_key
            )
        if query.predicate_id:
            statement = statement.where(semantic_claims.c.predicate_id == query.predicate_id)
        if query.known_at:
            statement = statement.where(semantic_claim_revisions.c.recorded_at <= query.known_at)
        if query.valid_at:
            statement = statement.where(
                and_(
                    semantic_claim_revisions.c.valid_from <= query.valid_at,
                    or_(
                        semantic_claim_revisions.c.valid_to.is_(None),
                        semantic_claim_revisions.c.valid_to > query.valid_at,
                    ),
                )
            )
        statement = (
            statement.distinct(semantic_claim_revisions.c.claim_id)
            .order_by(
                semantic_claim_revisions.c.claim_id,
                semantic_claim_revisions.c.revision.desc(),
            )
            .limit(query.budget.maximum_results)
        )
        async with self._engine.connect() as connection:
            rows = (await connection.execute(statement)).mappings().all()
        revisions = tuple(_revision_from_row(row) for row in rows)
        snapshot = semantic_hash(
            [f"{item.claim_id}:{item.revision}:{item.content_hash}" for item in revisions]
        )
        return SemanticQueryResult(
            query_id=query.query_id, claims=revisions, snapshot_hash=snapshot
        )

    async def record_semantic_access(self, records: tuple[SemanticAccessRecord, ...]) -> None:
        if not records:
            return
        values = [
            {
                "access_id": item.access_id,
                "query_id": item.query_id,
                "task_run_id": item.task_run_id,
                "claim_id": item.claim_id,
                "claim_revision": item.claim_revision,
                "query_mode": item.query_mode.value,
                "valid_at": item.valid_at,
                "known_at": item.known_at,
                "rank": item.rank,
                "scope_type": item.scope.scope_type.value,
                "scope_id": item.scope.scope_id,
                "sensitivity": item.sensitivity.value,
                "query_hash": item.query_hash,
                "accessed_at": item.accessed_at,
                "used_in_wiki": item.used_in_wiki,
            }
            for item in records
        ]
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(insert(semantic_accesses), values)

    async def create_wiki_page(self, page: WikiPage) -> WikiPage:
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(
                insert(wiki_pages).values(
                    page_id=page.page_id,
                    scope_type=page.scope.scope_type.value,
                    scope_id=page.scope.scope_id,
                    canonical_subject_key=page.canonical_subject_key,
                    page_type=page.page_type,
                    domain=page.domain,
                    current_revision=page.current_revision,
                    created_at=page.created_at,
                )
            )
        return page

    async def get_wiki_page(self, page_id: UUID) -> WikiPage | None:
        async with self._engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        select(wiki_pages).where(wiki_pages.c.page_id == page_id)
                    )
                )
                .mappings()
                .one_or_none()
            )
        return (
            WikiPage(
                page_id=row["page_id"],
                scope=MemoryScope(scope_type=row["scope_type"], scope_id=row["scope_id"]),
                canonical_subject_key=row["canonical_subject_key"],
                page_type=row["page_type"],
                domain=row["domain"],
                current_revision=row["current_revision"],
                created_at=row["created_at"],
            )
            if row is not None
            else None
        )

    async def get_wiki_revision(self, page_id: UUID, revision: int) -> WikiPageRevision | None:
        async with self._engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        select(wiki_page_revisions).where(
                            and_(
                                wiki_page_revisions.c.page_id == page_id,
                                wiki_page_revisions.c.revision == revision,
                            )
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                return None
            refs = (
                (
                    await connection.execute(
                        select(wiki_page_claims)
                        .where(
                            and_(
                                wiki_page_claims.c.page_id == page_id,
                                wiki_page_claims.c.page_revision == revision,
                            )
                        )
                        .order_by(
                            wiki_page_claims.c.section,
                            wiki_page_claims.c.display_order,
                        )
                    )
                )
                .mappings()
                .all()
            )
        return WikiPageRevision.model_validate(
            {
                "page_id": page_id,
                "revision": revision,
                "previous_revision": row["previous_revision"],
                "renderer_version": row["renderer_version"],
                "markdown": row["markdown"],
                "claim_refs": [
                    {
                        "claim": {
                            "claim_id": item["claim_id"],
                            "revision": item["claim_revision"],
                        },
                        "section": item["section"],
                        "display_order": item["display_order"],
                    }
                    for item in refs
                ],
                "valid_at": row["valid_at"],
                "known_at": row["known_at"],
                "rendered_at": row["rendered_at"],
                "content_hash": row["content_hash"],
                "snapshot_hash": row["snapshot_hash"],
            }
        )

    async def list_wiki_history(self, page_id: UUID) -> tuple[WikiPageRevision, ...]:
        page = await self.get_wiki_page(page_id)
        if page is None:
            return ()
        revisions = []
        for number in range(1, page.current_revision + 1):
            revision = await self.get_wiki_revision(page_id, number)
            if revision is None:
                raise SemanticIntegrityError("Wiki revision continuity gap")
            revisions.append(revision)
        return tuple(revisions)

    async def append_wiki_revision(
        self, revision: WikiPageRevision, *, expected_revision: int
    ) -> WikiPageRevision:
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(
                insert(wiki_page_revisions).values(
                    page_id=revision.page_id,
                    revision=revision.revision,
                    previous_revision=revision.previous_revision,
                    renderer_version=revision.renderer_version,
                    markdown=revision.markdown,
                    valid_at=revision.valid_at,
                    known_at=revision.known_at,
                    rendered_at=revision.rendered_at,
                    content_hash=revision.content_hash,
                    snapshot_hash=revision.snapshot_hash,
                )
            )
            if revision.claim_refs:
                await connection.execute(
                    insert(wiki_page_claims),
                    [
                        {
                            "page_id": revision.page_id,
                            "page_revision": revision.revision,
                            "claim_id": item.claim.claim_id,
                            "claim_revision": item.claim.revision,
                            "section": item.section.value,
                            "display_order": item.display_order,
                        }
                        for item in revision.claim_refs
                    ],
                )
            advanced = await connection.scalar(
                text(
                    "SELECT cognitive_os.advance_wiki_page(:id, :expected_revision, :next_revision)"
                ),
                {
                    "id": revision.page_id,
                    "expected_revision": expected_revision,
                    "next_revision": revision.revision,
                },
            )
            if not advanced:
                raise SemanticConcurrencyError("stale expected Wiki revision")
        return revision
