"""Host-governed orchestration for semantic observations, claims, queries, and Wiki."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from hashlib import sha256
from uuid import UUID, uuid4

from cognitive_os.application.ports.semantic_memory_repository import SemanticMemoryRepositoryPort
from cognitive_os.config.semantic_memory_config import SemanticMemoryConfiguration
from cognitive_os.domain.common import JsonValue, utc_now
from cognitive_os.domain.semantic_memory import (
    BeliefStatus,
    Claim,
    ClaimPromotionDecision,
    ClaimPromotionOutcome,
    ClaimRelation,
    ClaimRelationType,
    ClaimRevision,
    ContradictionCandidate,
    ContradictionRecord,
    ContradictionResolution,
    ContradictionRevision,
    ContradictionSeverity,
    ContradictionStatus,
    EvidenceLink,
    EvidenceValidationResult,
    ObservationQuery,
    ObservationQueryResult,
    SemanticAccessRecord,
    SemanticActorType,
    SemanticLiteral,
    SemanticObservation,
    SemanticQueryResult,
    TemporalClaimQuery,
    WikiPage,
    WikiPageRevision,
    semantic_hash,
)
from cognitive_os.events.semantic_memory_event_service import SemanticMemoryEventService
from cognitive_os.events.semantic_memory_events import (
    SemanticClaimBeliefChanged,
    SemanticClaimCreated,
    SemanticContradictionCandidateRecorded,
    SemanticContradictionOpened,
    SemanticContradictionResolved,
    SemanticObservationRecorded,
    SemanticObservationsAccessed,
    SemanticWikiPageRegenerated,
    SemanticWikiPageRendered,
)

from .beliefs import assert_legal_transition
from .canonicalization import canonical_value
from .contradictions import (
    detect_evidence_conflict,
    detect_functional_conflict,
    detect_registered_conflict,
)
from .errors import SemanticPolicyError
from .graph import has_restricted_cycle
from .grounding import TrustedSourceResolver
from .predicates import PredicateRegistry
from .rendering import render_wiki_revision


class SemanticMemoryService:
    def __init__(
        self,
        repository: SemanticMemoryRepositoryPort,
        registry: PredicateRegistry,
        configuration: SemanticMemoryConfiguration,
        *,
        clock: Callable[[], datetime] = utc_now,
        id_factory: Callable[[], UUID] = uuid4,
        event_service: SemanticMemoryEventService | None = None,
        source_resolver: TrustedSourceResolver | None = None,
    ) -> None:
        self._repository = repository
        self._registry = registry
        self._configuration = configuration
        self._clock = clock
        self._id_factory = id_factory
        self._event_service = event_service
        self._source_resolver = source_resolver

    @property
    def configuration(self) -> SemanticMemoryConfiguration:
        return self._configuration

    async def build_promotion_snapshot(
        self,
        revision: ClaimRevision,
        evidence: tuple[EvidenceLink, ...],
    ) -> dict[str, JsonValue]:
        """Derive verifier inputs from authoritative host state."""
        claim = await self._repository.get_claim(revision.claim_id)
        current_revision = (
            await self._repository.get_claim_revision(revision.claim_id, claim.current_revision)
            if claim is not None
            else None
        )
        source_resolver = self._source_resolver
        source_integrity = False
        if evidence and source_resolver is not None and claim is not None:
            source_integrity = True
            try:
                for link in evidence:
                    await source_resolver.validate_span(
                        link.source_span,
                        scope=claim.identity.scope,
                        sensitivity=claim.sensitivity,
                    )
            except Exception:
                source_integrity = False
        evidence_integrity = (
            bool(evidence)
            and len({item.evidence_id for item in evidence}) == len(evidence)
            and all(
                item.claim.claim_id == revision.claim_id
                and item.claim.revision == revision.revision
                for item in evidence
            )
            and revision.evidence_snapshot_hash
            == semantic_hash([item.model_dump(mode="json") for item in evidence])
        )
        predicate_schema = False
        if claim is not None:
            try:
                descriptor = self._registry.require(claim.identity.predicate_id)
                predicate_schema = (
                    not isinstance(revision.object, SemanticLiteral)
                    or revision.object.literal_kind in descriptor.allowed_object_types
                )
            except ValueError:
                pass
        relations = (
            await self._repository.list_claim_relations(revision.claim_id)
            if claim is not None
            else ()
        )
        relation_integrity = True
        for relation in relations:
            if (
                await self._repository.get_claim_revision(
                    relation.source.claim_id, relation.source.revision
                )
                is None
                or await self._repository.get_claim_revision(
                    relation.target.claim_id, relation.target.revision
                )
                is None
            ):
                relation_integrity = False
                break
        has_open_critical = False
        for contradiction in await self._repository.list_contradictions():
            if (
                contradiction.current_status is not ContradictionStatus.OPEN
                or contradiction.severity is not ContradictionSeverity.CRITICAL
            ):
                continue
            current = await self._repository.get_contradiction_revision(
                contradiction.contradiction_id, contradiction.current_revision
            )
            if current is not None and any(
                item.claim_id == revision.claim_id for item in current.claims
            ):
                has_open_critical = True
                break
        contradiction_free = not has_open_critical and not await self.detect_contradictions(
            revision.claim_id
        )
        trusted_actor = revision.created_by.actor_type not in {
            SemanticActorType.PROVIDER,
            SemanticActorType.CONTROLLER,
        }
        return {
            "claim_id": str(revision.claim_id),
            "revision": revision.revision,
            "source_integrity": source_integrity,
            "source_grounding": source_integrity,
            "observation_schema": bool(evidence),
            "predicate_schema": predicate_schema,
            "valid_interval": (
                revision.valid_interval.valid_to is None
                or revision.valid_interval.valid_from < revision.valid_interval.valid_to
            ),
            "revision_continuity": (
                claim is not None
                and current_revision is not None
                and revision.revision == claim.current_revision + 1
                and revision.previous_revision == claim.current_revision
            ),
            "relation_integrity": relation_integrity,
            "supersession_acyclic": not has_restricted_cycle(relations),
            "evidence_minimum": bool(evidence),
            "evidence_integrity": evidence_integrity,
            "critical_contradiction": contradiction_free,
            "belief_policy": (
                revision.belief_status is BeliefStatus.SUPPORTED
                and revision.confidence.complete_for_support()
                and revision.confidence.overall_confidence
                >= self._configuration.supported_confidence_threshold
                and trusted_actor
            ),
        }

    async def get_observation(self, observation_id: UUID) -> SemanticObservation | None:
        return await self._repository.get_observation(observation_id)

    async def query_observations(self, query: ObservationQuery) -> ObservationQueryResult:
        observations = await self._repository.list_observations(
            source_type=query.source_type,
            source_id=query.source_id,
            source_revision=query.source_revision,
            scopes=query.scopes,
            sensitivity_ceiling=query.sensitivity_ceiling,
            limit=query.maximum_results,
        )
        result = ObservationQueryResult(
            query_id=query.query_id,
            observations=observations,
            snapshot_hash=semantic_hash([item.model_dump(mode="json") for item in observations]),
        )
        if self._event_service is None:
            if self._configuration.fail_closed_on_access_audit_error:
                raise SemanticPolicyError("observation query access audit is unavailable")
            return result
        await self._event_service.append(
            aggregate_id=query.query_id,
            payload=SemanticObservationsAccessed(
                query_id=query.query_id,
                observation_ids=tuple(item.observation_id for item in observations),
                query_hash=query.canonical_hash(),
                accessed_at=self._clock(),
            ),
            expected_version=0,
            correlation_id=query.query_id,
        )
        return result

    async def validate_observation(self, observation: SemanticObservation) -> None:
        if observation.created_by.actor_type is SemanticActorType.PROVIDER:
            raise SemanticPolicyError("providers cannot record semantic observations directly")
        if len(observation.source_spans) > self._configuration.maximum_source_spans_per_observation:
            raise SemanticPolicyError("observation source-span limit exceeded")
        if self._source_resolver is None:
            raise SemanticPolicyError("trusted semantic source resolver is not configured")
        for span in observation.source_spans:
            await self._source_resolver.validate_span(
                span, scope=observation.scope, sensitivity=observation.sensitivity
            )

    async def record_observation(self, observation: SemanticObservation) -> SemanticObservation:
        await self.validate_observation(observation)
        existing = await self._repository.get_observation(observation.observation_id)
        recorded = await self._repository.record_observation(observation)
        if existing is None and self._event_service is not None:
            await self._event_service.append(
                aggregate_id=observation.observation_id,
                payload=SemanticObservationRecorded(
                    observation_id=observation.observation_id,
                    content_hash=observation.content_hash,
                    recorded_at=observation.recorded_at,
                ),
                expected_version=0,
                correlation_id=observation.observation_id,
            )
        return recorded

    async def create_claim(
        self,
        claim: Claim,
        revision: ClaimRevision,
        evidence: tuple[EvidenceLink, ...],
    ) -> tuple[Claim, ClaimRevision]:
        if claim.created_by.actor_type is SemanticActorType.PROVIDER:
            raise SemanticPolicyError("providers cannot commit semantic claims directly")
        if len(evidence) > self._configuration.maximum_evidence_links_per_claim:
            raise SemanticPolicyError("claim evidence limit exceeded")
        if len(revision.statement.encode()) > self._configuration.maximum_statement_bytes:
            raise SemanticPolicyError("claim statement byte limit exceeded")
        if (
            len(claim.identity.canonical_subject_key.encode())
            > self._configuration.maximum_subject_bytes
        ):
            raise SemanticPolicyError("claim subject byte limit exceeded")
        if (
            len(canonical_value(revision.object).encode())
            > self._configuration.maximum_object_bytes
        ):
            raise SemanticPolicyError("claim object byte limit exceeded")
        descriptor = self._registry.require(claim.identity.predicate_id)
        if (
            isinstance(revision.object, SemanticLiteral)
            and revision.object.literal_kind not in descriptor.allowed_object_types
        ):
            raise SemanticPolicyError("claim object type is not allowed by the predicate")
        if revision.belief_status not in {BeliefStatus.PROPOSED, BeliefStatus.UNKNOWN}:
            raise SemanticPolicyError("claim creation may only produce proposed or unknown state")
        if not evidence or any(
            item.claim.claim_id != claim.identity.claim_id or item.claim.revision != 1
            for item in evidence
        ):
            raise SemanticPolicyError("claim creation requires revision-specific evidence")
        if self._source_resolver is None:
            raise SemanticPolicyError("trusted semantic source resolver is not configured")
        for link in evidence:
            await self._source_resolver.validate_span(
                link.source_span,
                scope=claim.identity.scope,
                sensitivity=claim.sensitivity,
            )
        if revision.evidence_snapshot_hash != semantic_hash(
            [item.model_dump(mode="json") for item in evidence]
        ):
            raise SemanticPolicyError("claim evidence snapshot hash does not match its links")
        duplicates = await self._repository.query_claims(
            TemporalClaimQuery(
                query_id=self._id_factory(),
                scopes=(claim.identity.scope,),
                subject_key=claim.identity.canonical_subject_key,
                predicate_id=claim.identity.predicate_id,
            )
        )
        for existing_revision in duplicates.claims:
            if canonical_value(existing_revision.object) == canonical_value(
                revision.object
            ) and existing_revision.valid_interval.overlaps(revision.valid_interval):
                existing_claim = await self._repository.get_claim(existing_revision.claim_id)
                if existing_claim is None:
                    raise SemanticPolicyError("duplicate search returned a missing claim")
                return existing_claim, existing_revision
        created = await self._repository.create_claim_with_evidence(claim, revision, evidence)
        if self._event_service is not None:
            await self._event_service.append(
                aggregate_id=claim.identity.claim_id,
                payload=SemanticClaimCreated(
                    claim_id=claim.identity.claim_id,
                    revision=1,
                    content_hash=revision.content_hash,
                ),
                expected_version=0,
                correlation_id=claim.identity.claim_id,
            )
        return created

    async def transition_claim(
        self,
        revision: ClaimRevision,
        *,
        expected_revision: int,
        decision: ClaimPromotionDecision | None = None,
        evidence: tuple[EvidenceLink, ...] = (),
    ) -> ClaimRevision:
        claim = await self._repository.get_claim(revision.claim_id)
        if claim is None:
            raise SemanticPolicyError("claim does not exist")
        if claim.current_revision == revision.revision:
            current_revision = await self._repository.get_claim_revision(
                revision.claim_id, revision.revision
            )
            if current_revision == revision:
                return current_revision
        assert_legal_transition(claim.current_belief_status, revision.belief_status)
        if (
            revision.belief_status is BeliefStatus.DISPUTED
            and not evidence
            and not await self.detect_contradictions(revision.claim_id)
        ):
            raise SemanticPolicyError(
                "disputed transition requires contradictory evidence or a conflict"
            )
        if revision.belief_status is BeliefStatus.SUPERSEDED:
            current_reference = (revision.claim_id, expected_revision)
            relations = await self._repository.list_claim_relations(revision.claim_id)
            if not any(
                item.relation_type is ClaimRelationType.SUPERSEDES
                and (item.target.claim_id, item.target.revision) == current_reference
                for item in relations
            ):
                raise SemanticPolicyError(
                    "superseded transition requires a persisted successor relation"
                )
        if revision.belief_status is BeliefStatus.SUPPORTED:
            if not evidence:
                raise SemanticPolicyError("supported promotion requires exact revision evidence")
            if decision is None or decision.outcome is not ClaimPromotionOutcome.SUPPORTED:
                raise SemanticPolicyError(
                    "supported promotion requires a supported verifier decision"
                )
            if revision.promotion_decision_id != decision.decision_id:
                raise SemanticPolicyError("supported revision does not reference its decision")
            if self._event_service is None or not (
                await self._event_service.promotion_decision_is_persisted(decision)
            ):
                raise SemanticPolicyError("promotion decision was not persisted before transition")
            if (
                decision.claim.claim_id != revision.claim_id
                or decision.claim.revision != expected_revision
            ):
                raise SemanticPolicyError("promotion decision targets the wrong claim revision")
            if decision.decided_by.actor_type in {
                SemanticActorType.PROVIDER,
                SemanticActorType.CONTROLLER,
            }:
                raise SemanticPolicyError("untrusted actors cannot authorize promotion")
            if revision.created_by.actor_type in {
                SemanticActorType.PROVIDER,
                SemanticActorType.CONTROLLER,
            }:
                raise SemanticPolicyError(
                    "provider and controller actors cannot self-authorize support"
                )
            if (
                revision.confidence.overall_confidence
                < self._configuration.supported_confidence_threshold
            ):
                raise SemanticPolicyError("claim confidence is below the supported threshold")
            has_open_critical = False
            for contradiction in await self._repository.list_contradictions():
                if (
                    contradiction.current_status is not ContradictionStatus.OPEN
                    or contradiction.severity is not ContradictionSeverity.CRITICAL
                ):
                    continue
                current_contradiction = await self._repository.get_contradiction_revision(
                    contradiction.contradiction_id, contradiction.current_revision
                )
                if current_contradiction is not None and any(
                    item.claim_id == revision.claim_id for item in current_contradiction.claims
                ):
                    has_open_critical = True
                    break
            if has_open_critical or await self.detect_contradictions(revision.claim_id):
                raise SemanticPolicyError("unresolved deterministic contradiction blocks support")
        if evidence:
            if self._source_resolver is None:
                raise SemanticPolicyError("trusted semantic source resolver is not configured")
            if any(
                item.claim.claim_id != revision.claim_id or item.claim.revision != revision.revision
                for item in evidence
            ):
                raise SemanticPolicyError("transition evidence targets the wrong claim revision")
            for link in evidence:
                await self._source_resolver.validate_span(
                    link.source_span,
                    scope=claim.identity.scope,
                    sensitivity=claim.sensitivity,
                )
            if revision.evidence_snapshot_hash != semantic_hash(
                [item.model_dump(mode="json") for item in evidence]
            ):
                raise SemanticPolicyError("claim evidence snapshot hash does not match its links")
            appended = await self._repository.append_claim_revision_with_evidence(
                revision, evidence, expected_revision=expected_revision
            )
        else:
            appended = await self._repository.append_claim_revision(
                revision, expected_revision=expected_revision
            )
        if self._event_service is not None:
            await self._event_service.append(
                aggregate_id=revision.claim_id,
                payload=SemanticClaimBeliefChanged(
                    claim_id=revision.claim_id,
                    expected_revision=expected_revision,
                    revision=revision.revision,
                    previous_status=claim.current_belief_status,
                    status=revision.belief_status,
                    decision_id=decision.decision_id if decision else None,
                ),
                expected_version=expected_revision,
                correlation_id=decision.decision_id if decision else revision.claim_id,
            )
        return appended

    async def query_claims(
        self, query: TemporalClaimQuery, *, used_in_wiki: bool = False
    ) -> SemanticQueryResult:
        if query.budget.maximum_results > self._configuration.maximum_temporal_query_results:
            raise SemanticPolicyError("semantic query result limit exceeds host policy")
        result = await self._repository.query_claims(query)
        records: list[SemanticAccessRecord] = []
        query_hash = query.canonical_hash()
        for rank, revision in enumerate(result.claims, start=1):
            claim = await self._repository.get_claim(revision.claim_id)
            if claim is None:
                raise SemanticPolicyError("query returned a missing claim projection")
            records.append(
                SemanticAccessRecord(
                    access_id=self._id_factory(),
                    query_id=query.query_id,
                    claim_id=revision.claim_id,
                    claim_revision=revision.revision,
                    query_mode=query.mode,
                    valid_at=query.valid_at,
                    known_at=query.known_at,
                    rank=rank,
                    scope=claim.identity.scope,
                    sensitivity=claim.sensitivity,
                    query_hash=query_hash,
                    accessed_at=self._clock(),
                    used_in_wiki=used_in_wiki,
                )
            )
        try:
            await self._repository.record_semantic_access(tuple(records))
        except Exception:
            if self._configuration.fail_closed_on_access_audit_error:
                raise
        return result

    async def detect_contradictions(self, claim_id: UUID) -> tuple[ContradictionCandidate, ...]:
        claim = await self._repository.get_claim(claim_id)
        if claim is None:
            raise SemanticPolicyError("claim does not exist")
        current = await self._repository.get_claim_revision(claim_id, claim.current_revision)
        if current is None:
            raise SemanticPolicyError("claim current revision does not exist")
        candidates: list[ContradictionCandidate] = []
        query = TemporalClaimQuery(
            query_id=self._id_factory(),
            scopes=(claim.identity.scope,),
            subject_key=claim.identity.canonical_subject_key,
        )
        result = await self._repository.query_claims(query)
        current_evidence = await self._repository.list_evidence(claim_id, revision=current.revision)
        for other_revision in result.claims:
            other = await self._repository.get_claim(other_revision.claim_id)
            if other is None:
                continue
            candidate = detect_functional_conflict(
                claim.identity,
                current,
                other.identity,
                other_revision,
                self._registry,
            )
            if candidate is not None:
                candidates.append(candidate)
            registered = detect_registered_conflict(
                claim.identity,
                current,
                other.identity,
                other_revision,
                self._registry,
            )
            if registered is not None:
                candidates.append(registered)
            evidence = detect_evidence_conflict(
                current,
                current_evidence,
                other_revision,
                await self._repository.list_evidence(
                    other_revision.claim_id, revision=other_revision.revision
                ),
            )
            if evidence is not None:
                candidates.append(evidence)
            if len(candidates) >= self._configuration.maximum_contradiction_candidates:
                break
        return tuple(candidates)

    async def add_claim_relation(self, relation: ClaimRelation) -> ClaimRelation:
        for reference in (relation.source, relation.target):
            if (
                await self._repository.get_claim_revision(reference.claim_id, reference.revision)
                is None
            ):
                raise SemanticPolicyError("claim relation endpoint does not exist")
        existing = {
            item.relation_id: item
            for claim_id in {relation.source.claim_id, relation.target.claim_id}
            for item in await self._repository.list_claim_relations(claim_id)
        }
        if len(existing) >= self._configuration.maximum_relations_per_request:
            raise SemanticPolicyError("claim relation limit exceeded")
        candidate = (*existing.values(), relation)
        if has_restricted_cycle(candidate):
            raise SemanticPolicyError("restricted claim relation cycle")
        return await self._repository.add_claim_relation(relation)

    async def reevaluate_evidence(
        self, claim_id: UUID, *, revision: int | None = None
    ) -> tuple[EvidenceValidationResult, ...]:
        claim = await self._repository.get_claim(claim_id)
        if claim is None:
            raise SemanticPolicyError("claim does not exist")
        target_revision = revision or claim.current_revision
        results = []
        for link in await self._repository.list_evidence(claim_id, revision=target_revision):
            try:
                if self._source_resolver is None:
                    raise SemanticPolicyError("trusted semantic source resolver is not configured")
                await self._source_resolver.validate_span(
                    link.source_span,
                    scope=claim.identity.scope,
                    sensitivity=claim.sensitivity,
                )
                reason_codes = ("valid",)
                valid = True
            except Exception as error:
                reason_codes = (type(error).__name__,)
                valid = False
            results.append(
                EvidenceValidationResult(
                    evidence_id=link.evidence_id,
                    valid=valid,
                    reason_codes=reason_codes,
                    validated_at=self._clock(),
                )
            )
        return tuple(results)

    async def open_contradiction(
        self,
        contradiction: ContradictionRecord,
        revision: ContradictionRevision,
    ) -> tuple[ContradictionRecord, ContradictionRevision]:
        if (
            contradiction.current_status is not ContradictionStatus.OPEN
            or revision.status is not ContradictionStatus.OPEN
            or revision.revision != 1
        ):
            raise SemanticPolicyError("confirmed contradiction creation must open revision one")
        await self._validate_contradiction_references(revision)
        created = await self._repository.create_contradiction(contradiction, revision)
        if self._event_service is not None:
            await self._event_service.append(
                aggregate_id=contradiction.contradiction_id,
                payload=SemanticContradictionOpened(
                    contradiction_id=contradiction.contradiction_id,
                    revision=1,
                    claim_ids=tuple(item.claim_id for item in revision.claims),
                    content_hash=revision.content_hash,
                ),
                expected_version=0,
                correlation_id=contradiction.contradiction_id,
            )
        return created

    async def record_contradiction_candidate(
        self,
        contradiction: ContradictionRecord,
        revision: ContradictionRevision,
    ) -> tuple[ContradictionRecord, ContradictionRevision]:
        if (
            contradiction.current_status is not ContradictionStatus.CANDIDATE
            or revision.status is not ContradictionStatus.CANDIDATE
            or revision.revision != 1
        ):
            raise SemanticPolicyError("provider contradiction proposals must remain candidates")
        await self._validate_contradiction_references(revision)
        existing = await self._repository.get_contradiction(contradiction.contradiction_id)
        if existing == contradiction:
            stored_revision = await self._repository.get_contradiction_revision(
                contradiction.contradiction_id, 1
            )
            if stored_revision == revision:
                return existing, stored_revision
        created = await self._repository.create_contradiction(contradiction, revision)
        if self._event_service is not None:
            await self._event_service.append(
                aggregate_id=contradiction.contradiction_id,
                payload=SemanticContradictionCandidateRecorded(
                    contradiction_id=contradiction.contradiction_id,
                    revision=1,
                    claim_ids=tuple(item.claim_id for item in revision.claims),
                    content_hash=revision.content_hash,
                ),
                expected_version=0,
                correlation_id=contradiction.contradiction_id,
            )
        return created

    async def transition_contradiction(
        self,
        revision: ContradictionRevision,
        *,
        expected_revision: int,
        resolution: ContradictionResolution | None = None,
    ) -> ContradictionRevision:
        current = await self._repository.get_contradiction(revision.contradiction_id)
        if current is None:
            raise SemanticPolicyError("contradiction does not exist")
        if current.current_revision == revision.revision:
            stored = await self._repository.get_contradiction_revision(
                revision.contradiction_id, revision.revision
            )
            if stored == revision:
                return stored
        legal = {
            ContradictionStatus.OPEN: {
                ContradictionStatus.RESOLVED,
                ContradictionStatus.DISMISSED,
            },
            ContradictionStatus.RESOLVED: {ContradictionStatus.OPEN},
            ContradictionStatus.DISMISSED: {ContradictionStatus.OPEN},
            ContradictionStatus.CANDIDATE: {ContradictionStatus.OPEN},
        }
        if revision.status not in legal[current.current_status]:
            raise SemanticPolicyError("illegal contradiction status transition")
        await self._validate_contradiction_references(revision)
        terminal = revision.status in {
            ContradictionStatus.RESOLVED,
            ContradictionStatus.DISMISSED,
        }
        if terminal:
            if (
                resolution is None
                or resolution.contradiction_id != revision.contradiction_id
                or resolution.expected_revision != expected_revision
                or revision.resolver != resolution.decided_by
                or not set(resolution.affected_claims) <= set(revision.claims)
                or not set(resolution.evidence_ids) <= set(revision.evidence_ids)
            ):
                raise SemanticPolicyError("contradiction resolution decision is missing or invalid")
            resolved = resolution
        elif current.current_status is ContradictionStatus.CANDIDATE and (
            revision.resolver is None
            or revision.resolver.actor_type
            in {SemanticActorType.PROVIDER, SemanticActorType.CONTROLLER}
        ):
            raise SemanticPolicyError("candidate confirmation requires a trusted decision actor")
        appended = await self._repository.append_contradiction_revision(
            revision, expected_revision=expected_revision
        )
        if terminal:
            for reference in revision.claims:
                await self.reevaluate_evidence(reference.claim_id, revision=reference.revision)
        if self._event_service is not None:
            payload = (
                SemanticContradictionOpened(
                    contradiction_id=revision.contradiction_id,
                    revision=revision.revision,
                    claim_ids=tuple(item.claim_id for item in revision.claims),
                    content_hash=revision.content_hash,
                )
                if revision.status is ContradictionStatus.OPEN
                else SemanticContradictionResolved(
                    contradiction_id=revision.contradiction_id,
                    expected_revision=expected_revision,
                    revision=revision.revision,
                    status=revision.status,
                    content_hash=revision.content_hash,
                    resolution_id=resolved.resolution_id,
                )
            )
            await self._event_service.append(
                aggregate_id=revision.contradiction_id,
                payload=payload,
                expected_version=expected_revision,
                correlation_id=revision.contradiction_id,
            )
        return appended

    async def _validate_contradiction_references(self, revision: ContradictionRevision) -> None:
        for reference in revision.claims:
            if (
                await self._repository.get_claim_revision(reference.claim_id, reference.revision)
                is None
            ):
                raise SemanticPolicyError("contradiction references a missing claim revision")
        known_evidence = {
            item.evidence_id
            for reference in revision.claims
            for item in await self._repository.list_evidence(
                reference.claim_id, revision=reference.revision
            )
        }
        if not set(revision.evidence_ids) <= known_evidence:
            raise SemanticPolicyError("contradiction references missing evidence")

    async def render_wiki(
        self,
        page: WikiPage,
        query: TemporalClaimQuery,
        *,
        expected_revision: int,
    ) -> WikiPageRevision:
        stored_page = await self._repository.get_wiki_page(page.page_id)
        if stored_page is None:
            if expected_revision != 0:
                raise SemanticPolicyError("Wiki page does not exist at the expected revision")
            stored_page = await self._repository.create_wiki_page(page)
        elif stored_page.current_revision != expected_revision:
            raise SemanticPolicyError("stale expected Wiki revision")
        result = await self.query_claims(query, used_in_wiki=True)
        claims: list[tuple[Claim, ClaimRevision]] = []
        evidence: list[EvidenceLink] = []
        for revision in result.claims:
            claim = await self._repository.get_claim(revision.claim_id)
            if (
                claim is not None
                and claim.identity.canonical_subject_key == page.canonical_subject_key
            ):
                claims.append((claim, revision))
                evidence.extend(
                    await self._repository.list_evidence(
                        revision.claim_id, revision=revision.revision
                    )
                )
        contradictions = []
        claim_references = {(item.claim_id, item.revision) for _, item in claims}
        for contradiction in await self._repository.list_contradictions():
            contradiction_revision = await self._repository.get_contradiction_revision(
                contradiction.contradiction_id, contradiction.current_revision
            )
            if contradiction_revision is not None and any(
                (reference.claim_id, reference.revision) in claim_references
                for reference in contradiction_revision.claims
            ):
                contradictions.append(contradiction_revision)
        if len(claims) > self._configuration.maximum_wiki_claims_per_page:
            raise SemanticPolicyError("Wiki claim limit exceeded")
        rendered = render_wiki_revision(
            page=stored_page,
            claims=tuple(claims),
            evidence=tuple(evidence),
            contradictions=tuple(contradictions),
            revision=expected_revision + 1,
            rendered_at=self._clock(),
            valid_at=query.valid_at,
            known_at=query.known_at,
            maximum_bytes=self._configuration.maximum_wiki_page_bytes,
        )
        if expected_revision:
            previous = await self._repository.get_wiki_revision(page.page_id, expected_revision)
            if (
                previous is not None
                and previous.snapshot_hash == rendered.snapshot_hash
                and previous.content_hash == rendered.content_hash
                and previous.valid_at == rendered.valid_at
                and previous.known_at == rendered.known_at
            ):
                if self._event_service is not None:
                    event_version = await self._event_service.current_version(page.page_id)
                    await self._event_service.append(
                        aggregate_id=page.page_id,
                        payload=SemanticWikiPageRegenerated(
                            page_id=page.page_id,
                            revision=previous.revision,
                            content_hash=previous.content_hash,
                            identical=True,
                        ),
                        expected_version=event_version,
                        correlation_id=query.query_id,
                    )
                return previous
        persisted = await self._repository.append_wiki_revision(
            rendered, expected_revision=expected_revision
        )
        if self._event_service is not None and persisted.revision == rendered.revision:
            event_version = await self._event_service.current_version(page.page_id)
            await self._event_service.append(
                aggregate_id=page.page_id,
                payload=SemanticWikiPageRendered(
                    page_id=page.page_id,
                    revision=persisted.revision,
                    content_hash=persisted.content_hash,
                    snapshot_hash=persisted.snapshot_hash,
                ),
                expected_version=event_version,
                correlation_id=query.query_id,
            )
        return persisted

    async def verify_wiki_revision(self, page_id: UUID, revision: int) -> bool:
        stored = await self._repository.get_wiki_revision(page_id, revision)
        if stored is None:
            return False
        if stored.content_hash != sha256(stored.markdown.encode()).hexdigest():
            return False
        if stored.snapshot_hash != semantic_hash(
            [item.model_dump(mode="json") for item in stored.claim_refs]
        ):
            return False
        for reference in stored.claim_refs:
            if (
                await self._repository.get_claim_revision(
                    reference.claim.claim_id, reference.claim.revision
                )
                is None
            ):
                return False
        return True
