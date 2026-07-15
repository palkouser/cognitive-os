"""Temporal semantic-memory contracts and deterministic identities."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from .base import ImmutableContractModel
from .common import JsonValue, NonEmptyStr, Sha256Hex, UtcDatetime
from .memory import MemoryScope, MemorySensitivity


class SemanticContract(ImmutableContractModel):
    """Immutable public contract with canonical serialization."""

    def canonical_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))

    def canonical_hash(self) -> str:
        return sha256(self.canonical_json().encode()).hexdigest()


class BeliefStatus(StrEnum):
    PROPOSED = "proposed"
    SUPPORTED = "supported"
    DISPUTED = "disputed"
    SUPERSEDED = "superseded"
    RETRACTED = "retracted"
    UNKNOWN = "unknown"


class EvidenceRelation(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    QUALIFIES = "qualifies"
    SUPERSEDES = "supersedes"
    DERIVED_FROM = "derived_from"


class ClaimRelationType(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    QUALIFIES = "qualifies"
    SUPERSEDES = "supersedes"
    DERIVED_FROM = "derived_from"
    SPECIALIZES = "specializes"
    GENERALIZES = "generalizes"
    RELATED_TO = "related_to"


class ContradictionStatus(StrEnum):
    CANDIDATE = "candidate"
    OPEN = "open"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class ContradictionSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ContradictionResolutionOutcome(StrEnum):
    CLAIM_SUPERSEDED = "claim_superseded"
    CLAIM_RETRACTED = "claim_retracted"
    NON_OVERLAPPING_INTERVALS = "non_overlapping_intervals"
    DISTINCT_SCOPES = "distinct_scopes"
    EVIDENCE_INVALIDATED = "evidence_invalidated"
    UNRESOLVED_PLURALITY = "unresolved_plurality"


class SemanticValueType(StrEnum):
    ENTITY = "entity"
    LITERAL = "literal"
    REFERENCE = "reference"


class SemanticLiteralKind(StrEnum):
    STRING = "string"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    DECIMAL = "decimal"
    DATE = "date"
    DATETIME = "datetime"
    VERSION = "version"
    URI = "uri"
    QUANTITY = "quantity"


class SemanticSourceType(StrEnum):
    EVENT = "event"
    ARTIFACT = "artifact"
    MEMORY_REVISION = "memory_revision"
    TASK_RUN = "task_run"
    TRAJECTORY = "trajectory"


class SemanticActorType(StrEnum):
    USER = "user"
    OPERATOR = "operator"
    CONTROLLER = "controller"
    SEMANTIC_SERVICE = "semantic_service"
    APPROVED_INTERNAL_SERVICE = "approved_internal_service"
    PROVIDER = "provider"


class TemporalQueryMode(StrEnum):
    CURRENT = "current"
    VALID_AT = "valid_at"
    KNOWN_AT = "known_at"
    BITEMPORAL = "bitemporal"


class ExtractionDecisionOutcome(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REQUIRES_REVIEW = "requires_review"


class WikiSectionType(StrEnum):
    CURRENT_SUPPORTED = "current_supported"
    DISPUTED = "disputed"
    OPEN_CONTRADICTIONS = "open_contradictions"
    SUPERSEDED_HISTORY = "superseded_history"
    EVIDENCE_INDEX = "evidence_index"
    REVISION_METADATA = "revision_metadata"


class SemanticActor(SemanticContract):
    actor_type: SemanticActorType
    actor_id: Annotated[str, Field(min_length=1, max_length=256)]


class SemanticEntityRef(SemanticContract):
    value_type: Literal[SemanticValueType.ENTITY] = SemanticValueType.ENTITY
    entity_id: Annotated[str, Field(min_length=1, max_length=1024)]
    entity_type: Annotated[str, Field(min_length=1, max_length=128)]
    display_label: Annotated[str | None, Field(default=None, max_length=1024)]


LiteralValue = str | bool | int | Decimal


class SemanticLiteral(SemanticContract):
    value_type: Literal[SemanticValueType.LITERAL] = SemanticValueType.LITERAL
    literal_kind: SemanticLiteralKind
    value: LiteralValue
    unit: Annotated[str | None, Field(default=None, max_length=128)]

    @model_validator(mode="after")
    def value_matches_kind(self) -> SemanticLiteral:
        kind, value = self.literal_kind, self.value
        valid = {
            SemanticLiteralKind.BOOLEAN: isinstance(value, bool),
            SemanticLiteralKind.INTEGER: isinstance(value, int) and not isinstance(value, bool),
            SemanticLiteralKind.DECIMAL: isinstance(value, Decimal),
        }
        if kind in valid and not valid[kind]:
            raise ValueError("literal value does not match its declared kind")
        if kind not in valid and not isinstance(value, str):
            raise ValueError("textual literal kinds require a string value")
        if kind is SemanticLiteralKind.DATE:
            date.fromisoformat(str(value))
        elif kind is SemanticLiteralKind.DATETIME:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError("datetime literal must include a UTC offset")
        elif kind is SemanticLiteralKind.VERSION and not re.fullmatch(
            r"[0-9]+(?:\.[0-9]+)*(?:[-+][0-9A-Za-z.-]+)?", str(value)
        ):
            raise ValueError("version literal is malformed")
        elif kind is SemanticLiteralKind.QUANTITY and not self.unit:
            raise ValueError("quantity literal requires a unit")
        elif kind is not SemanticLiteralKind.QUANTITY and self.unit is not None:
            raise ValueError("only quantity literals may declare a unit")
        return self


class SemanticReference(SemanticContract):
    value_type: Literal[SemanticValueType.REFERENCE] = SemanticValueType.REFERENCE
    namespace: Annotated[str, Field(min_length=1, max_length=128)]
    identifier: Annotated[str, Field(min_length=1, max_length=1024)]
    display_label: Annotated[str | None, Field(default=None, max_length=1024)]


SemanticValue = Annotated[
    SemanticEntityRef | SemanticLiteral | SemanticReference,
    Field(discriminator="value_type"),
]
SemanticSubject = SemanticEntityRef | SemanticReference
SemanticObject = SemanticValue


class SemanticSourceRef(SemanticContract):
    source_type: SemanticSourceType
    source_id: UUID
    revision: int | None = Field(default=None, ge=1)
    content_hash: Sha256Hex

    @model_validator(mode="after")
    def revision_shape(self) -> SemanticSourceRef:
        if self.source_type is SemanticSourceType.MEMORY_REVISION and self.revision is None:
            raise ValueError("memory sources require an exact revision")
        if self.source_type is not SemanticSourceType.MEMORY_REVISION and self.revision is not None:
            raise ValueError("only memory sources have revisions")
        return self


class GroundingMode(StrEnum):
    TYPED_FIELD = "typed_field"
    ARTIFACT_BYTES = "artifact_bytes"
    LINE_RANGE = "line_range"
    EVENT_FIELD = "event_field"
    MEMORY_FIELD = "memory_field"


class GroundedSourceSpan(SemanticContract):
    source: SemanticSourceRef
    mode: GroundingMode
    path: Annotated[str | None, Field(default=None, max_length=1024)]
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, ge=1)
    excerpt_hash: Sha256Hex

    @model_validator(mode="after")
    def valid_range(self) -> GroundedSourceSpan:
        ranged = self.mode in {GroundingMode.ARTIFACT_BYTES, GroundingMode.LINE_RANGE}
        if ranged and (self.start is None or self.end is None or self.end <= self.start):
            raise ValueError("range grounding requires a non-empty half-open range")
        if not ranged and not self.path:
            raise ValueError("field grounding requires an exact field path")
        return self


class SemanticObservation(SemanticContract):
    observation_id: UUID
    content: Annotated[str, Field(min_length=1, max_length=16_384)]
    normalized_content: Annotated[str, Field(min_length=1, max_length=16_384)]
    source_refs: Annotated[tuple[SemanticSourceRef, ...], Field(min_length=1, max_length=16)]
    source_spans: Annotated[tuple[GroundedSourceSpan, ...], Field(min_length=1, max_length=16)]
    observed_at: UtcDatetime
    recorded_at: UtcDatetime
    scope: MemoryScope
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    sensitivity: MemorySensitivity
    created_by: SemanticActor
    content_hash: Sha256Hex
    idempotency_key: Sha256Hex

    @model_validator(mode="after")
    def validate_grounding_and_hash(self) -> SemanticObservation:
        identities = {
            (item.source_type, item.source_id, item.revision) for item in self.source_refs
        }
        if any(
            (span.source.source_type, span.source.source_id, span.source.revision) not in identities
            for span in self.source_spans
        ):
            raise ValueError("every source span must reference a declared source")
        if self.recorded_at < self.observed_at:
            raise ValueError("recorded_at cannot precede observed_at")
        expected = semantic_hash(
            {
                "content": self.content,
                "normalized_content": self.normalized_content,
                "source_refs": [item.model_dump(mode="json") for item in self.source_refs],
                "source_spans": [item.model_dump(mode="json") for item in self.source_spans],
            }
        )
        if self.content_hash != expected:
            raise ValueError("semantic observation content hash mismatch")
        return self


class ClaimTemporalInterval(SemanticContract):
    valid_from: UtcDatetime
    valid_to: UtcDatetime | None = None

    @model_validator(mode="after")
    def half_open(self) -> ClaimTemporalInterval:
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise ValueError("valid interval must be non-empty and half-open")
        return self

    def contains(self, value: datetime) -> bool:
        return self.valid_from <= value and (self.valid_to is None or value < self.valid_to)

    def overlaps(self, other: ClaimTemporalInterval) -> bool:
        return (self.valid_to is None or other.valid_from < self.valid_to) and (
            other.valid_to is None or self.valid_from < other.valid_to
        )


class ConfidenceDimensions(SemanticContract):
    extraction_confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    source_reliability: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    grounding_confidence: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    evidence_confidence: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    verification_confidence: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    consistency_confidence: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    overall_confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    aggregation_policy_version: Literal["1"] = "1"

    @model_validator(mode="after")
    def conservative_aggregate(self) -> ConfidenceDimensions:
        supplied = [
            value
            for value in (
                self.extraction_confidence,
                self.source_reliability,
                self.grounding_confidence,
                self.evidence_confidence,
                self.verification_confidence,
                self.consistency_confidence,
            )
            if value is not None
        ]
        if self.overall_confidence > min(supplied):
            raise ValueError("overall confidence cannot exceed its weakest dimension")
        return self

    def complete_for_support(self) -> bool:
        return all(
            value is not None
            for value in (
                self.source_reliability,
                self.grounding_confidence,
                self.evidence_confidence,
                self.verification_confidence,
                self.consistency_confidence,
            )
        )


class ClaimIdentity(SemanticContract):
    claim_id: UUID
    scope: MemoryScope
    canonical_subject_key: Annotated[str, Field(min_length=1, max_length=1024)]
    predicate_id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")]


class ClaimReference(SemanticContract):
    claim_id: UUID


class ClaimRevisionReference(SemanticContract):
    claim_id: UUID
    revision: int = Field(ge=1)


class Claim(SemanticContract):
    identity: ClaimIdentity
    current_revision: int = Field(ge=1)
    current_belief_status: BeliefStatus
    sensitivity: MemorySensitivity
    created_at: UtcDatetime
    created_by: SemanticActor
    idempotency_key: Sha256Hex


def semantic_hash(value: object) -> str:
    return sha256(
        json.dumps(value, default=str, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def claim_revision_hash(
    *,
    claim_id: UUID,
    revision: int,
    object_value: SemanticObject,
    statement: str,
    belief_status: BeliefStatus,
    confidence: ConfidenceDimensions,
    valid_interval: ClaimTemporalInterval,
    reason: str,
    evidence_snapshot_hash: str,
) -> str:
    return semantic_hash(
        {
            "belief_status": belief_status.value,
            "claim_id": str(claim_id),
            "confidence": confidence.model_dump(mode="json"),
            "evidence_snapshot_hash": evidence_snapshot_hash,
            "object": object_value.model_dump(mode="json"),
            "reason": reason,
            "revision": revision,
            "statement": statement,
            "valid_interval": valid_interval.model_dump(mode="json"),
        }
    )


class ClaimRevision(SemanticContract):
    claim_id: UUID
    revision: int = Field(ge=1, le=10_000)
    previous_revision: int | None = Field(default=None, ge=1)
    object: SemanticObject
    statement: Annotated[str, Field(min_length=1, max_length=8_192)]
    belief_status: BeliefStatus
    confidence: ConfidenceDimensions
    valid_interval: ClaimTemporalInterval
    reason: Annotated[str, Field(min_length=1, max_length=2048)]
    recorded_at: UtcDatetime
    created_by: SemanticActor
    evidence_snapshot_hash: Sha256Hex
    promotion_decision_id: UUID | None = None
    content_hash: Sha256Hex

    @model_validator(mode="after")
    def valid_chain_and_hash(self) -> ClaimRevision:
        expected_previous = None if self.revision == 1 else self.revision - 1
        if self.previous_revision != expected_previous:
            raise ValueError("claim revision must reference its immediate predecessor")
        expected = claim_revision_hash(
            claim_id=self.claim_id,
            revision=self.revision,
            object_value=self.object,
            statement=self.statement,
            belief_status=self.belief_status,
            confidence=self.confidence,
            valid_interval=self.valid_interval,
            reason=self.reason,
            evidence_snapshot_hash=self.evidence_snapshot_hash,
        )
        if self.content_hash != expected:
            raise ValueError("claim revision content hash mismatch")
        if (
            self.belief_status is BeliefStatus.SUPPORTED
            and not self.confidence.complete_for_support()
        ):
            raise ValueError("supported claims require every confidence dimension")
        return self


class EvidenceLink(SemanticContract):
    evidence_id: UUID
    claim: ClaimRevisionReference
    source: SemanticSourceRef
    source_span: GroundedSourceSpan
    relation: EvidenceRelation
    strength: float = Field(ge=0, le=1, allow_inf_nan=False)
    created_at: UtcDatetime
    created_by: SemanticActor

    @model_validator(mode="after")
    def exact_source_matches(self) -> EvidenceLink:
        if self.source != self.source_span.source:
            raise ValueError("evidence span source does not match evidence source")
        return self


class EvidenceValidationResult(SemanticContract):
    evidence_id: UUID
    valid: bool
    reason_codes: tuple[NonEmptyStr, ...]
    validated_at: UtcDatetime


class EvidenceBundle(SemanticContract):
    claim: ClaimRevisionReference
    links: Annotated[tuple[EvidenceLink, ...], Field(min_length=1, max_length=32)]
    snapshot_hash: Sha256Hex

    @model_validator(mode="after")
    def unique_and_hashed(self) -> EvidenceBundle:
        ids = [item.evidence_id for item in self.links]
        if len(ids) != len(set(ids)) or any(item.claim != self.claim for item in self.links):
            raise ValueError("evidence links must be unique and target one exact claim revision")
        expected = semantic_hash([item.model_dump(mode="json") for item in self.links])
        if self.snapshot_hash != expected:
            raise ValueError("evidence bundle snapshot hash mismatch")
        return self


class ClaimRelation(SemanticContract):
    relation_id: UUID
    source: ClaimRevisionReference
    target: ClaimRevisionReference
    relation_type: ClaimRelationType
    valid_interval: ClaimTemporalInterval
    provenance: SemanticSourceRef
    created_at: UtcDatetime

    @model_validator(mode="after")
    def no_restricted_self_edge(self) -> ClaimRelation:
        if self.source == self.target and self.relation_type is not ClaimRelationType.RELATED_TO:
            raise ValueError("restricted claim relations cannot be self edges")
        return self


class ContradictionCandidate(SemanticContract):
    claims: Annotated[tuple[ClaimRevisionReference, ClaimRevisionReference], Field(min_length=2)]
    overlap: ClaimTemporalInterval
    rule_id: NonEmptyStr
    deterministic: bool


class ContradictionRecord(SemanticContract):
    contradiction_id: UUID
    current_revision: int = Field(ge=1)
    current_status: ContradictionStatus
    severity: ContradictionSeverity
    created_at: UtcDatetime


class ContradictionRevision(SemanticContract):
    contradiction_id: UUID
    revision: int = Field(ge=1)
    previous_revision: int | None = Field(default=None, ge=1)
    status: ContradictionStatus
    severity: ContradictionSeverity
    claims: Annotated[tuple[ClaimRevisionReference, ...], Field(min_length=2, max_length=32)]
    evidence_ids: tuple[UUID, ...]
    reason: NonEmptyStr
    resolver: SemanticActor | None = None
    recorded_at: UtcDatetime
    content_hash: Sha256Hex

    @model_validator(mode="after")
    def chain_and_resolution(self) -> ContradictionRevision:
        expected = None if self.revision == 1 else self.revision - 1
        if self.previous_revision != expected:
            raise ValueError("contradiction revision must reference its immediate predecessor")
        if (
            self.status in {ContradictionStatus.RESOLVED, ContradictionStatus.DISMISSED}
            and not self.resolver
        ):
            raise ValueError("resolved contradictions require a resolver")
        payload = self.model_dump(mode="json", exclude={"content_hash"})
        if self.content_hash != semantic_hash(payload):
            raise ValueError("contradiction revision content hash mismatch")
        return self


class ContradictionResolution(SemanticContract):
    resolution_id: UUID
    contradiction_id: UUID
    expected_revision: int = Field(ge=1)
    outcome: ContradictionResolutionOutcome
    affected_claims: Annotated[
        tuple[ClaimRevisionReference, ...], Field(min_length=1, max_length=32)
    ]
    evidence_ids: tuple[UUID, ...] = ()
    reason: NonEmptyStr
    decided_at: UtcDatetime
    decided_by: SemanticActor

    @model_validator(mode="after")
    def trusted_decision(self) -> ContradictionResolution:
        if self.decided_by.actor_type in {
            SemanticActorType.PROVIDER,
            SemanticActorType.CONTROLLER,
        }:
            raise ValueError("provider and controller actors cannot resolve contradictions")
        return self


class ClaimPromotionOutcome(StrEnum):
    SUPPORTED = "supported"
    DISPUTED = "disputed"
    REMAIN_PROPOSED = "remain_proposed"
    REQUIRES_REVIEW = "requires_review"
    REJECTED = "rejected"
    VERIFICATION_ERROR = "verification_error"


class ClaimPromotionDecision(SemanticContract):
    decision_id: UUID
    claim: ClaimRevisionReference
    outcome: ClaimPromotionOutcome
    verifier_bundle_hash: Sha256Hex
    registry_snapshot_hash: Sha256Hex
    reason_codes: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    decided_at: UtcDatetime
    decided_by: SemanticActor


class Cardinality(StrEnum):
    FUNCTIONAL = "functional"
    MULTI = "multi"


class PredicateDescriptor(SemanticContract):
    predicate_id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")]
    version: Annotated[str, Field(min_length=1, max_length=32)]
    display_name: NonEmptyStr
    description: NonEmptyStr
    allowed_subject_types: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    allowed_object_types: Annotated[
        tuple[SemanticLiteralKind | SemanticValueType, ...], Field(min_length=1)
    ]
    cardinality: Cardinality
    temporal_behavior: NonEmptyStr
    negatable: bool = False
    exclusive_value_group: str | None = None
    default_sensitivity: MemorySensitivity = MemorySensitivity.INTERNAL
    rendering_label: NonEmptyStr
    contradiction_rule: str | None = None


class ExtractionBudget(SemanticContract):
    maximum_observations: int = Field(ge=1, le=100)
    maximum_claims: int = Field(ge=1, le=100)
    maximum_evidence_links: int = Field(ge=1, le=3_200)
    maximum_relations: int = Field(ge=0, le=200)


class SemanticExtractionRequest(SemanticContract):
    request_id: UUID
    source_spans: Annotated[tuple[GroundedSourceSpan, ...], Field(min_length=1, max_length=16)]
    registry_snapshot_hash: Sha256Hex
    scope: MemoryScope
    sensitivity_ceiling: MemorySensitivity
    budget: ExtractionBudget
    required_output_schema: dict[str, JsonValue]
    requested_at: UtcDatetime


class ObservationProposal(SemanticContract):
    proposal_id: UUID
    content: Annotated[str, Field(min_length=1, max_length=16_384)]
    source_spans: Annotated[tuple[GroundedSourceSpan, ...], Field(min_length=1, max_length=16)]


class ClaimProposal(SemanticContract):
    proposal_id: UUID
    subject: SemanticSubject
    predicate_id: NonEmptyStr
    object: SemanticObject
    valid_interval: ClaimTemporalInterval
    observation_proposal_ids: tuple[UUID, ...] = ()
    existing_observation_ids: tuple[UUID, ...] = ()
    provider_confidence: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def has_grounding_observation(self) -> ClaimProposal:
        references = self.observation_proposal_ids + self.existing_observation_ids
        if not references or len(references) != len(set(references)):
            raise ValueError("claim proposal requires unique observation references")
        return self


class EvidenceProposal(SemanticContract):
    proposal_id: UUID
    claim_proposal_id: UUID
    observation_id: UUID
    relation: EvidenceRelation
    strength: float = Field(ge=0, le=1, allow_inf_nan=False)


class RelationProposal(SemanticContract):
    proposal_id: UUID
    source_claim_proposal_id: UUID
    target_claim_proposal_id: UUID
    relation_type: ClaimRelationType
    valid_interval: ClaimTemporalInterval


class ContradictionProposal(SemanticContract):
    proposal_id: UUID
    claim_proposal_ids: Annotated[tuple[UUID, UUID], Field(min_length=2, max_length=2)]
    rule_id: NonEmptyStr
    severity: ContradictionSeverity
    provider_confidence: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def distinct_claims(self) -> ContradictionProposal:
        if self.claim_proposal_ids[0] == self.claim_proposal_ids[1]:
            raise ValueError("contradiction proposal requires two distinct claims")
        return self


class SemanticExtractionProposal(SemanticContract):
    extraction_id: UUID
    registry_snapshot_hash: Sha256Hex
    observations: tuple[ObservationProposal, ...]
    claims: tuple[ClaimProposal, ...]
    evidence: tuple[EvidenceProposal, ...] = ()
    relations: tuple[RelationProposal, ...] = ()
    contradictions: tuple[ContradictionProposal, ...] = ()
    budget: ExtractionBudget

    @model_validator(mode="after")
    def within_budget_and_grounded(self) -> SemanticExtractionProposal:
        if (
            len(self.observations) > self.budget.maximum_observations
            or len(self.claims) > self.budget.maximum_claims
            or len(self.evidence) > self.budget.maximum_evidence_links
            or len(self.relations) > self.budget.maximum_relations
        ):
            raise ValueError("extraction proposal exceeds its budget")
        observations = {item.proposal_id for item in self.observations}
        if any(not set(item.observation_proposal_ids) <= observations for item in self.claims):
            raise ValueError("claim proposal references an unknown observation proposal")
        claims = {item.proposal_id for item in self.claims}
        observation_refs = observations | {
            value for item in self.claims for value in item.existing_observation_ids
        }
        if any(
            item.claim_proposal_id not in claims or item.observation_id not in observation_refs
            for item in self.evidence
        ):
            raise ValueError("evidence proposal references an unknown proposal")
        if any(
            item.source_claim_proposal_id not in claims
            or item.target_claim_proposal_id not in claims
            for item in self.relations
        ):
            raise ValueError("relation proposal references an unknown claim proposal")
        if any(not set(item.claim_proposal_ids) <= claims for item in self.contradictions):
            raise ValueError("contradiction proposal references an unknown claim proposal")
        return self


class ExtractionDecision(SemanticContract):
    extraction_id: UUID
    outcome: ExtractionDecisionOutcome
    proposal_hash: Sha256Hex
    reason_codes: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    decided_at: UtcDatetime
    decided_by: SemanticActor


class SemanticExtractionManifest(SemanticContract):
    extraction_id: UUID
    registry_snapshot_hash: Sha256Hex
    observation_ids: tuple[UUID, ...]
    claims: tuple[ClaimRevisionReference, ...]
    manifest_hash: Sha256Hex

    @model_validator(mode="after")
    def validate_manifest_hash(self) -> SemanticExtractionManifest:
        if self.manifest_hash != semantic_hash(
            self.model_dump(mode="json", exclude={"manifest_hash"})
        ):
            raise ValueError("semantic extraction manifest hash mismatch")
        return self


class SemanticQueryBudget(SemanticContract):
    maximum_results: int = Field(default=100, ge=1, le=500)


class TemporalClaimQuery(SemanticContract):
    query_id: UUID
    mode: TemporalQueryMode = TemporalQueryMode.CURRENT
    scopes: Annotated[tuple[MemoryScope, ...], Field(min_length=1, max_length=16)]
    subject_key: str | None = None
    predicate_id: str | None = None
    belief_statuses: tuple[BeliefStatus, ...] = (
        BeliefStatus.PROPOSED,
        BeliefStatus.SUPPORTED,
        BeliefStatus.DISPUTED,
        BeliefStatus.UNKNOWN,
    )
    sensitivity_ceiling: MemorySensitivity = MemorySensitivity.INTERNAL
    valid_at: UtcDatetime | None = None
    known_at: UtcDatetime | None = None
    budget: SemanticQueryBudget = SemanticQueryBudget()

    @model_validator(mode="after")
    def mode_matches_times(self) -> TemporalClaimQuery:
        expected = {
            TemporalQueryMode.CURRENT: (False, False),
            TemporalQueryMode.VALID_AT: (True, False),
            TemporalQueryMode.KNOWN_AT: (False, True),
            TemporalQueryMode.BITEMPORAL: (True, True),
        }[self.mode]
        if (self.valid_at is not None, self.known_at is not None) != expected:
            raise ValueError("temporal query mode does not match valid_at and known_at")
        return self


class SemanticQueryResult(SemanticContract):
    query_id: UUID
    claims: tuple[ClaimRevision, ...]
    snapshot_hash: Sha256Hex


class SemanticAccessRecord(SemanticContract):
    access_id: UUID
    query_id: UUID
    task_run_id: UUID | None = None
    claim_id: UUID
    claim_revision: int = Field(ge=1)
    query_mode: TemporalQueryMode
    valid_at: UtcDatetime | None = None
    known_at: UtcDatetime | None = None
    rank: int = Field(ge=1)
    scope: MemoryScope
    sensitivity: MemorySensitivity
    query_hash: Sha256Hex
    accessed_at: UtcDatetime
    used_in_wiki: bool = False


class WikiPage(SemanticContract):
    page_id: UUID
    scope: MemoryScope
    canonical_subject_key: NonEmptyStr
    page_type: NonEmptyStr
    domain: str | None = None
    current_revision: int = Field(ge=0)
    created_at: UtcDatetime


class WikiClaimReference(SemanticContract):
    claim: ClaimRevisionReference
    section: WikiSectionType
    display_order: int = Field(ge=0)


class WikiPageRevision(SemanticContract):
    page_id: UUID
    revision: int = Field(ge=1)
    previous_revision: int | None = Field(default=None, ge=1)
    renderer_version: Literal["3"] = "3"
    markdown: Annotated[str, Field(max_length=262_144)]
    claim_refs: tuple[WikiClaimReference, ...]
    valid_at: UtcDatetime | None = None
    known_at: UtcDatetime | None = None
    rendered_at: UtcDatetime
    content_hash: Sha256Hex
    snapshot_hash: Sha256Hex

    @model_validator(mode="after")
    def chain_and_hashes(self) -> WikiPageRevision:
        expected = None if self.revision == 1 else self.revision - 1
        if self.previous_revision != expected:
            raise ValueError("Wiki revision must reference its immediate predecessor")
        if self.content_hash != sha256(self.markdown.encode()).hexdigest():
            raise ValueError("Wiki content hash mismatch")
        lineage = [item.model_dump(mode="json") for item in self.claim_refs]
        if self.snapshot_hash != semantic_hash(lineage):
            raise ValueError("Wiki lineage snapshot hash mismatch")
        return self


PUBLIC_SEMANTIC_CONTRACTS: tuple[type[ImmutableContractModel], ...] = (
    SemanticActor,
    SemanticEntityRef,
    SemanticLiteral,
    SemanticReference,
    SemanticSourceRef,
    GroundedSourceSpan,
    SemanticObservation,
    ClaimTemporalInterval,
    ConfidenceDimensions,
    ClaimIdentity,
    ClaimReference,
    ClaimRevisionReference,
    Claim,
    ClaimRevision,
    EvidenceLink,
    EvidenceValidationResult,
    EvidenceBundle,
    ClaimRelation,
    ContradictionCandidate,
    ContradictionRecord,
    ContradictionRevision,
    ContradictionResolution,
    ClaimPromotionDecision,
    PredicateDescriptor,
    ExtractionBudget,
    SemanticExtractionRequest,
    ObservationProposal,
    ClaimProposal,
    EvidenceProposal,
    RelationProposal,
    ContradictionProposal,
    SemanticExtractionProposal,
    ExtractionDecision,
    SemanticExtractionManifest,
    SemanticQueryBudget,
    TemporalClaimQuery,
    SemanticQueryResult,
    SemanticAccessRecord,
    WikiPage,
    WikiClaimReference,
    WikiPageRevision,
)
