"""Validated proposal-to-projection compilation with no provider write authority."""

from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.domain.memory import MemoryScope, MemorySensitivity
from cognitive_os.domain.semantic_memory import (
    BeliefStatus,
    Claim,
    ClaimIdentity,
    ClaimRelation,
    ClaimRevision,
    ClaimRevisionReference,
    ConfidenceDimensions,
    EvidenceLink,
    EvidenceRelation,
    SemanticActor,
    SemanticActorType,
    SemanticEntityRef,
    SemanticExtractionManifest,
    SemanticExtractionProposal,
    SemanticLiteral,
    SemanticObservation,
    SemanticReference,
    claim_revision_hash,
    semantic_hash,
)
from cognitive_os.events.semantic_memory_event_service import SemanticMemoryEventService
from cognitive_os.events.semantic_memory_events import (
    SemanticExtractionCompleted,
    SemanticExtractionRejected,
)

from .canonicalization import canonical_identifier, canonical_text, canonical_value
from .errors import SemanticPolicyError
from .graph import has_restricted_cycle
from .predicates import PredicateRegistry
from .service import SemanticMemoryService


class SemanticExtractionService:
    def __init__(
        self,
        semantic_memory: SemanticMemoryService,
        registry: PredicateRegistry,
        *,
        events: SemanticMemoryEventService | None = None,
    ) -> None:
        self._semantic_memory = semantic_memory
        self._registry = registry
        self._events = events

    async def commit(
        self,
        proposal: SemanticExtractionProposal,
        *,
        scope: MemoryScope,
        sensitivity: MemorySensitivity,
        actor: SemanticActor,
        recorded_at: datetime,
        provider_origin: bool = False,
    ) -> SemanticExtractionManifest:
        try:
            return await self._commit(
                proposal,
                scope=scope,
                sensitivity=sensitivity,
                actor=actor,
                recorded_at=recorded_at,
                provider_origin=provider_origin,
            )
        except Exception as error:
            if self._events is not None:
                await self._events.append(
                    aggregate_id=proposal.extraction_id,
                    payload=SemanticExtractionRejected(
                        extraction_id=proposal.extraction_id,
                        reason_code=type(error).__name__,
                        proposal_hash=proposal.canonical_hash(),
                        rejected_at=recorded_at,
                    ),
                    expected_version=0,
                    correlation_id=proposal.extraction_id,
                )
            raise

    async def _commit(
        self,
        proposal: SemanticExtractionProposal,
        *,
        scope: MemoryScope,
        sensitivity: MemorySensitivity,
        actor: SemanticActor,
        recorded_at: datetime,
        provider_origin: bool,
    ) -> SemanticExtractionManifest:
        if actor.actor_type is SemanticActorType.PROVIDER:
            raise SemanticPolicyError("provider actors cannot commit extraction proposals")
        if proposal.registry_snapshot_hash != self._registry.snapshot_hash():
            raise SemanticPolicyError("extraction predicate registry snapshot is stale")
        configuration = self._semantic_memory.configuration
        if (
            len(proposal.observations) > configuration.maximum_observations_per_request
            or len(proposal.claims) > configuration.maximum_claims_per_request
            or len(proposal.relations) > configuration.maximum_relations_per_request
        ):
            raise SemanticPolicyError("extraction proposal exceeds host count policy")
        observations: dict[UUID, SemanticObservation] = {}
        for observation_proposal in proposal.observations:
            sources = tuple(
                dict.fromkeys(span.source for span in observation_proposal.source_spans)
            )
            normalized = canonical_text(observation_proposal.content)
            payload = {
                "content": observation_proposal.content,
                "normalized_content": normalized,
                "source_refs": [source.model_dump(mode="json") for source in sources],
                "source_spans": [
                    span.model_dump(mode="json") for span in observation_proposal.source_spans
                ],
            }
            observations[observation_proposal.proposal_id] = SemanticObservation(
                observation_id=observation_proposal.proposal_id,
                content=observation_proposal.content,
                normalized_content=normalized,
                source_refs=sources,
                source_spans=observation_proposal.source_spans,
                observed_at=recorded_at,
                recorded_at=recorded_at,
                scope=scope,
                confidence=1.0 if not provider_origin else 0.0,
                sensitivity=sensitivity,
                created_by=actor,
                content_hash=semantic_hash(payload),
                idempotency_key=semantic_hash(
                    {
                        "extraction_id": str(proposal.extraction_id),
                        "observation": str(observation_proposal.proposal_id),
                    }
                ),
            )
        resolved_observations = dict(observations)
        for claim_proposal in proposal.claims:
            for observation_id in claim_proposal.existing_observation_ids:
                existing = await self._semantic_memory.get_observation(observation_id)
                if existing is None:
                    raise SemanticPolicyError(
                        "claim proposal references a missing existing observation"
                    )
                resolved_observations[observation_id] = existing
        for observation in resolved_observations.values():
            await self._semantic_memory.validate_observation(observation)
        for claim_proposal in proposal.claims:
            descriptor = self._registry.require(claim_proposal.predicate_id)
            if (
                isinstance(claim_proposal.subject, SemanticEntityRef)
                and claim_proposal.subject.entity_type not in descriptor.allowed_subject_types
            ):
                raise SemanticPolicyError(
                    "claim subject type is not allowed by the extraction predicate"
                )
            if (
                isinstance(claim_proposal.object, SemanticLiteral)
                and claim_proposal.object.literal_kind not in descriptor.allowed_object_types
            ):
                raise SemanticPolicyError(
                    "claim object type is not allowed by the extraction predicate"
                )
        proposed_relations = []
        claims_by_id = {item.proposal_id: item for item in proposal.claims}
        for item in proposal.relations:
            source_claim = claims_by_id[item.source_claim_proposal_id]
            observation_id = (
                source_claim.observation_proposal_ids[0]
                if source_claim.observation_proposal_ids
                else source_claim.existing_observation_ids[0]
            )
            proposed_relations.append(
                ClaimRelation(
                    relation_id=item.proposal_id,
                    source=ClaimRevisionReference(
                        claim_id=item.source_claim_proposal_id, revision=1
                    ),
                    target=ClaimRevisionReference(
                        claim_id=item.target_claim_proposal_id, revision=1
                    ),
                    relation_type=item.relation_type,
                    valid_interval=item.valid_interval,
                    provenance=resolved_observations[observation_id].source_refs[0],
                    created_at=recorded_at,
                )
            )
        if has_restricted_cycle(tuple(proposed_relations)):
            raise SemanticPolicyError("extraction proposal contains a restricted relation cycle")
        for observation in observations.values():
            await self._semantic_memory.record_observation(observation)
        references: list[ClaimRevisionReference] = []
        references_by_proposal: dict[UUID, ClaimRevisionReference] = {}
        for claim_proposal in proposal.claims:
            descriptor = self._registry.require(claim_proposal.predicate_id)
            observation_id = (
                claim_proposal.observation_proposal_ids[0]
                if claim_proposal.observation_proposal_ids
                else claim_proposal.existing_observation_ids[0]
            )
            observation = resolved_observations[observation_id]
            span = observation.source_spans[0]
            claim_id = claim_proposal.proposal_id
            subject_key = (
                claim_proposal.subject.identifier
                if isinstance(claim_proposal.subject, SemanticReference)
                else claim_proposal.subject.entity_id
            )
            identity = ClaimIdentity(
                claim_id=claim_id,
                scope=scope,
                canonical_subject_key=canonical_identifier(subject_key),
                predicate_id=descriptor.predicate_id,
            )
            proposed_evidence = next(
                (
                    item
                    for item in proposal.evidence
                    if item.claim_proposal_id == claim_proposal.proposal_id
                    and item.observation_id == observation_id
                ),
                None,
            )
            evidence = EvidenceLink(
                evidence_id=(
                    proposed_evidence.proposal_id
                    if proposed_evidence
                    else uuid5(NAMESPACE_URL, f"{proposal.extraction_id}:{claim_id}:evidence")
                ),
                claim=ClaimRevisionReference(claim_id=claim_id, revision=1),
                source=span.source,
                source_span=span,
                relation=(
                    proposed_evidence.relation if proposed_evidence else EvidenceRelation.SUPPORTS
                ),
                strength=proposed_evidence.strength if proposed_evidence else 1.0,
                created_at=recorded_at,
                created_by=actor,
            )
            evidence_hash = semantic_hash([evidence.model_dump(mode="json")])
            extraction_confidence = (
                claim_proposal.provider_confidence
                if claim_proposal.provider_confidence is not None
                else (0.0 if provider_origin else 1.0)
            )
            confidence = ConfidenceDimensions(
                extraction_confidence=extraction_confidence,
                overall_confidence=extraction_confidence,
            )
            statement = f"{descriptor.rendering_label} = {canonical_value(claim_proposal.object)}"
            content_hash = claim_revision_hash(
                claim_id=claim_id,
                revision=1,
                object_value=claim_proposal.object,
                statement=statement,
                belief_status=BeliefStatus.PROPOSED,
                confidence=confidence,
                valid_interval=claim_proposal.valid_interval,
                reason="validated_extraction",
                evidence_snapshot_hash=evidence_hash,
            )
            revision = ClaimRevision(
                claim_id=claim_id,
                revision=1,
                object=claim_proposal.object,
                statement=statement,
                belief_status=BeliefStatus.PROPOSED,
                confidence=confidence,
                valid_interval=claim_proposal.valid_interval,
                reason="validated_extraction",
                recorded_at=recorded_at,
                created_by=actor,
                evidence_snapshot_hash=evidence_hash,
                content_hash=content_hash,
            )
            claim = Claim(
                identity=identity,
                current_revision=1,
                current_belief_status=BeliefStatus.PROPOSED,
                sensitivity=sensitivity,
                created_at=recorded_at,
                created_by=actor,
                idempotency_key=semantic_hash(
                    {
                        "scope": scope.model_dump(mode="json"),
                        "subject": identity.canonical_subject_key,
                        "predicate": identity.predicate_id,
                        "object": claim_proposal.object.model_dump(mode="json"),
                        "valid": claim_proposal.valid_interval.model_dump(mode="json"),
                    }
                ),
            )
            _, stored = await self._semantic_memory.create_claim(claim, revision, (evidence,))
            references.append(
                ClaimRevisionReference(claim_id=stored.claim_id, revision=stored.revision)
            )
            references_by_proposal[claim_proposal.proposal_id] = references[-1]
        for relation_proposal in proposal.relations:
            source_reference = references_by_proposal[relation_proposal.source_claim_proposal_id]
            target_reference = references_by_proposal[relation_proposal.target_claim_proposal_id]
            source_claim_proposal = next(
                item
                for item in proposal.claims
                if item.proposal_id == relation_proposal.source_claim_proposal_id
            )
            source_observation_id = (
                source_claim_proposal.observation_proposal_ids[0]
                if source_claim_proposal.observation_proposal_ids
                else source_claim_proposal.existing_observation_ids[0]
            )
            await self._semantic_memory.add_claim_relation(
                ClaimRelation(
                    relation_id=relation_proposal.proposal_id,
                    source=source_reference,
                    target=target_reference,
                    relation_type=relation_proposal.relation_type,
                    valid_interval=relation_proposal.valid_interval,
                    provenance=resolved_observations[source_observation_id].source_refs[0],
                    created_at=recorded_at,
                )
            )
        manifest_payload = {
            "extraction_id": str(proposal.extraction_id),
            "registry_snapshot_hash": proposal.registry_snapshot_hash,
            "observation_ids": [str(item) for item in sorted(resolved_observations, key=str)],
            "claims": [item.model_dump(mode="json") for item in references],
        }
        manifest = SemanticExtractionManifest(
            extraction_id=proposal.extraction_id,
            registry_snapshot_hash=proposal.registry_snapshot_hash,
            observation_ids=tuple(sorted(resolved_observations, key=str)),
            claims=tuple(references),
            manifest_hash=semantic_hash(manifest_payload),
        )
        if (
            self._events is not None
            and await self._events.current_version(proposal.extraction_id) == 0
        ):
            await self._events.append(
                aggregate_id=proposal.extraction_id,
                payload=SemanticExtractionCompleted(
                    extraction_id=proposal.extraction_id,
                    manifest_hash=manifest.manifest_hash,
                    observation_ids=manifest.observation_ids,
                    claim_ids=tuple(item.claim_id for item in manifest.claims),
                    completed_at=recorded_at,
                ),
                expected_version=0,
                correlation_id=proposal.extraction_id,
            )
        return manifest
