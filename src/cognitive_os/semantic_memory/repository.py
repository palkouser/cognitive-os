"""Deterministic in-memory semantic repository for core and credential-free tests."""

from __future__ import annotations

from hashlib import sha256
from uuid import UUID

from cognitive_os.domain.memory import MemoryScope, MemorySensitivity
from cognitive_os.domain.semantic_memory import (
    Claim,
    ClaimRelation,
    ClaimRevision,
    ContradictionRecord,
    ContradictionRevision,
    EvidenceLink,
    SemanticAccessRecord,
    SemanticObservation,
    SemanticQueryResult,
    SemanticSourceType,
    TemporalClaimQuery,
    WikiPage,
    WikiPageRevision,
)

from .errors import SemanticConcurrencyError, SemanticIntegrityError

_SENSITIVITY_ORDER = {
    MemorySensitivity.PUBLIC: 0,
    MemorySensitivity.INTERNAL: 1,
    MemorySensitivity.CONFIDENTIAL: 2,
    MemorySensitivity.RESTRICTED: 3,
}


class InMemorySemanticMemoryRepository:
    def __init__(self) -> None:
        self.observations: dict[UUID, SemanticObservation] = {}
        self.observation_idempotency: dict[str, UUID] = {}
        self.claims: dict[UUID, Claim] = {}
        self.claim_revisions: dict[UUID, list[ClaimRevision]] = {}
        self.claim_idempotency: dict[str, UUID] = {}
        self.evidence: dict[UUID, EvidenceLink] = {}
        self.relations: dict[UUID, ClaimRelation] = {}
        self.contradictions: dict[UUID, ContradictionRecord] = {}
        self.contradiction_revisions: dict[UUID, list[ContradictionRevision]] = {}
        self.accesses: list[SemanticAccessRecord] = []
        self.wiki_pages: dict[UUID, WikiPage] = {}
        self.wiki_revisions: dict[UUID, list[WikiPageRevision]] = {}

    async def record_observation(self, observation: SemanticObservation) -> SemanticObservation:
        existing_id = self.observation_idempotency.get(observation.idempotency_key)
        if existing_id is not None:
            existing = self.observations[existing_id]
            if existing.content_hash != observation.content_hash:
                raise SemanticConcurrencyError("observation idempotency key has different content")
            return existing
        if observation.observation_id in self.observations:
            raise SemanticConcurrencyError("semantic observation identity already exists")
        self.observations[observation.observation_id] = observation
        self.observation_idempotency[observation.idempotency_key] = observation.observation_id
        return observation

    async def get_observation(self, observation_id: UUID) -> SemanticObservation | None:
        return self.observations.get(observation_id)

    async def list_observations(
        self,
        *,
        source_type: SemanticSourceType | None = None,
        source_id: UUID | None = None,
        source_revision: int | None = None,
        scopes: tuple[MemoryScope, ...] = (),
        sensitivity_ceiling: MemorySensitivity = MemorySensitivity.INTERNAL,
        limit: int = 100,
    ) -> tuple[SemanticObservation, ...]:
        if limit < 1 or limit > 500:
            raise ValueError("observation limit must be between 1 and 500")
        matches = [
            item
            for item in self.observations.values()
            if (not scopes or item.scope in scopes)
            and _SENSITIVITY_ORDER[item.sensitivity] <= _SENSITIVITY_ORDER[sensitivity_ceiling]
            and any(
                (source_type is None or source.source_type is source_type)
                and (source_id is None or source.source_id == source_id)
                and (source_revision is None or source.revision == source_revision)
                for source in item.source_refs
            )
        ]
        return tuple(
            sorted(matches, key=lambda item: (item.recorded_at, str(item.observation_id)))
        )[:limit]

    async def create_claim(
        self, claim: Claim, revision: ClaimRevision
    ) -> tuple[Claim, ClaimRevision]:
        return await self.create_claim_with_evidence(claim, revision, ())

    async def create_claim_with_evidence(
        self, claim: Claim, revision: ClaimRevision, evidence: tuple[EvidenceLink, ...]
    ) -> tuple[Claim, ClaimRevision]:
        existing_id = self.claim_idempotency.get(claim.idempotency_key)
        if existing_id is not None:
            existing = self.claims[existing_id]
            first = self.claim_revisions[existing_id][0]
            if existing.identity != claim.identity or first.content_hash != revision.content_hash:
                raise SemanticConcurrencyError("claim idempotency key has different content")
            return existing, first
        if claim.identity.claim_id in self.claims or revision.claim_id != claim.identity.claim_id:
            raise SemanticConcurrencyError("semantic claim identity already exists or mismatches")
        if claim.current_revision != 1 or revision.revision != 1:
            raise SemanticIntegrityError("semantic claim creation requires revision one")
        if claim.current_belief_status is not revision.belief_status:
            raise SemanticIntegrityError("claim projection belief status mismatch")
        if (
            len({item.evidence_id for item in evidence}) != len(evidence)
            or any(item.evidence_id in self.evidence for item in evidence)
            or any(
                item.claim.claim_id != claim.identity.claim_id or item.claim.revision != 1
                for item in evidence
            )
        ):
            raise SemanticIntegrityError("claim creation evidence is invalid or duplicated")
        self.claims[claim.identity.claim_id] = claim
        self.claim_revisions[claim.identity.claim_id] = [revision]
        self.claim_idempotency[claim.idempotency_key] = claim.identity.claim_id
        self.evidence.update((item.evidence_id, item) for item in evidence)
        return claim, revision

    async def append_claim_revision(
        self, revision: ClaimRevision, *, expected_revision: int
    ) -> ClaimRevision:
        claim = self.claims.get(revision.claim_id)
        if claim is None or claim.current_revision != expected_revision:
            raise SemanticConcurrencyError("stale expected claim revision")
        if revision.revision != expected_revision + 1:
            raise SemanticConcurrencyError("next claim revision must increment exactly once")
        self.claim_revisions[revision.claim_id].append(revision)
        self.claims[revision.claim_id] = claim.model_copy(
            update={
                "current_revision": revision.revision,
                "current_belief_status": revision.belief_status,
            }
        )
        return revision

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
        appended = await self.append_claim_revision(revision, expected_revision=expected_revision)
        for item in evidence:
            await self.attach_evidence(item)
        return appended

    async def get_claim(self, claim_id: UUID) -> Claim | None:
        return self.claims.get(claim_id)

    async def get_claim_revision(self, claim_id: UUID, revision: int) -> ClaimRevision | None:
        return next(
            (item for item in self.claim_revisions.get(claim_id, ()) if item.revision == revision),
            None,
        )

    async def list_claim_history(
        self, claim_id: UUID, *, limit: int = 100
    ) -> tuple[ClaimRevision, ...]:
        if limit < 1 or limit > 500:
            raise ValueError("claim history limit must be between 1 and 500")
        return tuple(self.claim_revisions.get(claim_id, ()))[:limit]

    async def attach_evidence(self, evidence: EvidenceLink) -> EvidenceLink:
        revision = await self.get_claim_revision(evidence.claim.claim_id, evidence.claim.revision)
        if revision is None:
            raise SemanticIntegrityError("evidence targets a missing claim revision")
        existing = self.evidence.setdefault(evidence.evidence_id, evidence)
        if existing != evidence:
            raise SemanticConcurrencyError("evidence identity already has different content")
        return existing

    async def list_evidence(
        self, claim_id: UUID, *, revision: int | None = None
    ) -> tuple[EvidenceLink, ...]:
        return tuple(
            sorted(
                (
                    item
                    for item in self.evidence.values()
                    if item.claim.claim_id == claim_id
                    and (revision is None or item.claim.revision == revision)
                ),
                key=lambda item: (item.claim.revision, str(item.evidence_id)),
            )
        )

    async def add_claim_relation(self, relation: ClaimRelation) -> ClaimRelation:
        for reference in (relation.source, relation.target):
            if await self.get_claim_revision(reference.claim_id, reference.revision) is None:
                raise SemanticIntegrityError("claim relation endpoint does not exist")
        existing = self.relations.setdefault(relation.relation_id, relation)
        if existing != relation:
            raise SemanticConcurrencyError("claim relation identity conflict")
        return existing

    async def list_claim_relations(self, claim_id: UUID) -> tuple[ClaimRelation, ...]:
        return tuple(
            sorted(
                (
                    item
                    for item in self.relations.values()
                    if claim_id in {item.source.claim_id, item.target.claim_id}
                ),
                key=lambda item: str(item.relation_id),
            )
        )

    async def create_contradiction(
        self, contradiction: ContradictionRecord, revision: ContradictionRevision
    ) -> tuple[ContradictionRecord, ContradictionRevision]:
        if contradiction.contradiction_id in self.contradictions:
            current = self.contradictions[contradiction.contradiction_id]
            return current, self.contradiction_revisions[contradiction.contradiction_id][0]
        if contradiction.current_revision != 1 or revision.revision != 1:
            raise SemanticIntegrityError("contradiction creation requires revision one")
        self.contradictions[contradiction.contradiction_id] = contradiction
        self.contradiction_revisions[contradiction.contradiction_id] = [revision]
        return contradiction, revision

    async def append_contradiction_revision(
        self, revision: ContradictionRevision, *, expected_revision: int
    ) -> ContradictionRevision:
        current = self.contradictions.get(revision.contradiction_id)
        if current is None or current.current_revision != expected_revision:
            raise SemanticConcurrencyError("stale expected contradiction revision")
        if revision.revision != expected_revision + 1:
            raise SemanticConcurrencyError("contradiction revision must increment exactly once")
        self.contradiction_revisions[revision.contradiction_id].append(revision)
        self.contradictions[revision.contradiction_id] = current.model_copy(
            update={
                "current_revision": revision.revision,
                "current_status": revision.status,
                "severity": revision.severity,
            }
        )
        return revision

    async def get_contradiction(self, contradiction_id: UUID) -> ContradictionRecord | None:
        return self.contradictions.get(contradiction_id)

    async def get_contradiction_revision(
        self, contradiction_id: UUID, revision: int
    ) -> ContradictionRevision | None:
        return next(
            (
                item
                for item in self.contradiction_revisions.get(contradiction_id, ())
                if item.revision == revision
            ),
            None,
        )

    async def list_contradictions(self) -> tuple[ContradictionRecord, ...]:
        return tuple(self.contradictions[key] for key in sorted(self.contradictions, key=str))

    async def list_contradiction_history(
        self, contradiction_id: UUID
    ) -> tuple[ContradictionRevision, ...]:
        return tuple(self.contradiction_revisions.get(contradiction_id, ()))

    async def query_claims(self, query: TemporalClaimQuery) -> SemanticQueryResult:
        scope_keys = {(item.scope_type, item.scope_id) for item in query.scopes}
        selected: list[ClaimRevision] = []
        for claim_id in sorted(self.claims, key=str):
            claim = self.claims[claim_id]
            identity = claim.identity
            if (identity.scope.scope_type, identity.scope.scope_id) not in scope_keys:
                continue
            if query.subject_key and identity.canonical_subject_key != query.subject_key:
                continue
            if query.predicate_id and identity.predicate_id != query.predicate_id:
                continue
            revisions = self.claim_revisions[claim_id]
            known = [
                item
                for item in revisions
                if query.known_at is None or item.recorded_at <= query.known_at
            ]
            if query.valid_at is not None:
                known = [item for item in known if item.valid_interval.contains(query.valid_at)]
            if not known:
                continue
            revision = max(known, key=lambda item: item.revision)
            if revision.belief_status not in query.belief_statuses:
                continue
            selected.append(revision)
        selected.sort(key=lambda item: (str(item.claim_id), item.revision))
        selected = selected[: query.budget.maximum_results]
        snapshot = sha256(
            "|".join(
                f"{item.claim_id}:{item.revision}:{item.content_hash}" for item in selected
            ).encode()
        ).hexdigest()
        return SemanticQueryResult(
            query_id=query.query_id, claims=tuple(selected), snapshot_hash=snapshot
        )

    async def record_semantic_access(self, records: tuple[SemanticAccessRecord, ...]) -> None:
        self.accesses.extend(records)

    async def create_wiki_page(self, page: WikiPage) -> WikiPage:
        existing = self.wiki_pages.setdefault(page.page_id, page)
        if existing != page:
            raise SemanticConcurrencyError("Wiki page identity conflict")
        self.wiki_revisions.setdefault(page.page_id, [])
        return existing

    async def get_wiki_page(self, page_id: UUID) -> WikiPage | None:
        return self.wiki_pages.get(page_id)

    async def get_wiki_revision(self, page_id: UUID, revision: int) -> WikiPageRevision | None:
        return next(
            (item for item in self.wiki_revisions.get(page_id, ()) if item.revision == revision),
            None,
        )

    async def list_wiki_history(self, page_id: UUID) -> tuple[WikiPageRevision, ...]:
        return tuple(self.wiki_revisions.get(page_id, ()))

    async def append_wiki_revision(
        self, revision: WikiPageRevision, *, expected_revision: int
    ) -> WikiPageRevision:
        page = self.wiki_pages.get(revision.page_id)
        if page is None or page.current_revision != expected_revision:
            raise SemanticConcurrencyError("stale expected Wiki revision")
        if revision.revision != expected_revision + 1:
            raise SemanticConcurrencyError("Wiki revision must increment exactly once")
        for reference in revision.claim_refs:
            if (
                await self.get_claim_revision(reference.claim.claim_id, reference.claim.revision)
                is None
            ):
                raise SemanticIntegrityError("Wiki lineage references a missing claim revision")
        revisions = self.wiki_revisions[revision.page_id]
        if (
            revisions
            and revisions[-1].content_hash == revision.content_hash
            and revisions[-1].snapshot_hash == revision.snapshot_hash
        ):
            return revisions[-1]
        revisions.append(revision)
        self.wiki_pages[revision.page_id] = page.model_copy(
            update={"current_revision": revision.revision}
        )
        return revision
