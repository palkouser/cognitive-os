"""Immutable contracts for governed corpus transformation and routing."""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from .common import ArtifactRef, NonEmptyStr, Sha256Hex, UtcDatetime
from .experience import HashedExperienceContract
from .memory import MemorySensitivity


class CorpusSourceType(StrEnum):
    EXPERIENCE_CANDIDATE = "experience_candidate"
    VERIFIED_TRAJECTORY = "verified_trajectory"
    MEMORY_EXPORT = "memory_export"
    SEMANTIC_EXPORT = "semantic_export"
    SKILL_PACKAGE = "skill_package"
    STRATEGY_PACKAGE = "strategy_package"
    REPOSITORY_SNAPSHOT = "repository_snapshot"
    DOCUMENT = "document"
    BENCHMARK_DATASET = "benchmark_dataset"
    OPERATOR_ANNOTATION = "operator_annotation"
    PROVIDER_GENERATED_DATASET = "provider_generated_dataset"
    EXTERNAL_LOCAL_ARCHIVE = "external_local_archive"
    COGNITIVE_OS_EXPORT = "cognitive_os_export"


class CorpusItemStatus(StrEnum):
    RECEIVED = "received"
    NORMALIZED = "normalized"
    CLASSIFIED = "classified"
    STAGED = "staged"
    ROUTED = "routed"
    QUARANTINED = "quarantined"
    REJECTED = "rejected"
    EXPORTED = "exported"
    SUPERSEDED = "superseded"


class CorpusContentType(StrEnum):
    TRAJECTORY = "trajectory"
    MEMORY = "memory"
    SEMANTIC_OBSERVATION = "semantic_observation"
    SKILL = "skill"
    STRATEGY = "strategy"
    FAILURE_PATTERN = "failure_pattern"
    ROUTING_OBSERVATION = "routing_observation"
    BENCHMARK_CASE = "benchmark_case"
    NEGATIVE_EXAMPLE = "negative_example"
    SOURCE_CODE = "source_code"
    DIFF = "diff"
    DOCUMENTATION = "documentation"
    ANNOTATION = "annotation"
    DATASET = "dataset"
    UNKNOWN = "unknown"


class CorpusKnowledgeType(StrEnum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    STRATEGIC = "strategic"
    ROUTING_EVIDENCE = "routing_evidence"
    FAILURE_EVIDENCE = "failure_evidence"
    BENCHMARK_EVIDENCE = "benchmark_evidence"
    NEGATIVE_EXAMPLE = "negative_example"
    REFERENCE_MATERIAL = "reference_material"
    TRAINING_MATERIAL = "training_material"
    UNKNOWN = "unknown"


class CorpusDestinationType(StrEnum):
    GOVERNED_MEMORY_CANDIDATE = "governed_memory_candidate"
    SEMANTIC_OBSERVATION_CANDIDATE = "semantic_observation_candidate"
    SKILL_CANDIDATE = "skill_candidate"
    STRATEGY_CANDIDATE = "strategy_candidate"
    ROUTING_OBSERVATION = "routing_observation"
    WEAKNESS_SIGNAL = "weakness_signal"
    BENCHMARK_CASE = "benchmark_case"
    REPLAY_FIXTURE = "replay_fixture"
    NEGATIVE_EXAMPLE = "negative_example"
    TRAINING_CORPUS = "training_corpus"
    REFERENCE_CORPUS = "reference_corpus"
    QUARANTINE = "quarantine"
    REJECT = "reject"


class CorpusRouteStatus(StrEnum):
    ALLOWED = "allowed"
    DENIED = "denied"
    QUARANTINED = "quarantined"


class CorpusDuplicateType(StrEnum):
    UNIQUE = "unique"
    EXACT_DUPLICATE = "exact_duplicate"
    SAME_SOURCE_REVISION = "same_source_revision"
    SAME_LINEAGE = "same_lineage"
    DESTINATION_DUPLICATE = "destination_duplicate"
    NEAR_DUPLICATE_CANDIDATE = "near_duplicate_candidate"
    CONFLICTING_DUPLICATE = "conflicting_duplicate"


class CorpusQualityTier(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BLOCKED = "blocked"


class CorpusLicenseStatus(StrEnum):
    APPROVED = "approved"
    INTERNAL = "internal"
    UNKNOWN = "unknown"
    CONFLICTING = "conflicting"
    RESTRICTED = "restricted"


class CorpusUsageRight(StrEnum):
    INTERNAL_USE = "internal_use"
    REDISTRIBUTION = "redistribution"
    MODIFICATION = "modification"
    DERIVATIVE_WORK = "derivative_work"
    BENCHMARK_USE = "benchmark_use"
    MODEL_TRAINING = "model_training"
    COMMERCIAL_USE = "commercial_use"
    PUBLIC_RELEASE = "public_release"


class CorpusSensitivityStatus(StrEnum):
    ALLOWED = "allowed"
    REQUIRES_REVIEW = "requires_review"
    QUARANTINED = "quarantined"
    REJECTED = "rejected"


class CorpusExportType(StrEnum):
    JSONL = "jsonl"
    COGNITIVE_OS_PACKAGE = "cognitive_os_package"


class CorpusAccessType(StrEnum):
    SOURCE_REGISTRATION = "source_registration"
    SOURCE_READ = "source_read"
    NORMALIZATION = "normalization"
    DEDUPLICATION = "deduplication"
    CLASSIFICATION = "classification"
    LICENSE_REVIEW = "license_review"
    QUALITY_SCORING = "quality_scoring"
    ROUTING = "routing"
    MANIFEST_READ = "manifest_read"
    EXPORT = "export"


class CorpusRejectionReason(StrEnum):
    SOURCE_INTEGRITY = "source_integrity"
    PROHIBITED_RIGHTS = "prohibited_rights"
    PROHIBITED_SENSITIVITY = "prohibited_sensitivity"
    UNSUPPORTED_FORMAT = "unsupported_format"
    DESTINATION_SCHEMA = "destination_schema"
    AUTHORITY_VIOLATION = "authority_violation"
    CANCELLED = "cancelled"


class CorpusQuarantineReason(StrEnum):
    UNCLEAR_LICENSE = "unclear_license"
    CONFLICTING_LICENSE = "conflicting_license"
    SOURCE_INTEGRITY_WARNING = "source_integrity_warning"
    # This is a policy reason code, not credential material. pragma: allowlist secret
    SECRET_DETECTED = "secret_detected"  # nosec B105
    UNSUPPORTED_SENSITIVITY = "unsupported_sensitivity"
    CONFLICTING_PROVENANCE = "conflicting_provenance"
    MALFORMED_ARCHIVE = "malformed_archive"
    UNVERIFIABLE_PROVIDER_DATA = "unverifiable_provider_data"
    ROUTE_AMBIGUITY = "route_ambiguity"
    NEAR_DUPLICATE_REVIEW = "near_duplicate_review"


class CorpusLineageRelationship(StrEnum):
    NORMALIZED_FROM = "normalized_from"
    DERIVED_FROM = "derived_from"
    DUPLICATE_OF = "duplicate_of"
    NEAR_DUPLICATE_OF = "near_duplicate_of"
    MERGED_PROVENANCE_FROM = "merged_provenance_from"
    COMPILED_FROM = "compiled_from"
    EXPORTED_FROM = "exported_from"
    SUPERSEDES = "supersedes"
    SPLIT_FROM = "split_from"


class CorpusQualityDimensionName(StrEnum):
    SOURCE_AUTHORITY = "source_authority"
    VERIFIER_COVERAGE = "verifier_coverage"
    ACCEPTANCE_STATUS = "acceptance_status"
    PROVENANCE_COMPLETENESS = "provenance_completeness"
    REPRODUCIBILITY = "reproducibility"
    CONSISTENCY = "consistency"
    SENSITIVITY_RISK = "sensitivity_risk"
    LICENSING_CLARITY = "licensing_clarity"
    FORMATTING_INTEGRITY = "formatting_integrity"
    GENERALIZABILITY = "generalizability"
    DUPLICATE_STATUS = "duplicate_status"
    CONTRADICTION_STATUS = "contradiction_status"


class LicensePolicyOutcome(StrEnum):
    ALLOWED = "allowed"
    ALLOWED_INTERNAL_ONLY = "allowed_internal_only"
    REQUIRES_REVIEW = "requires_review"
    QUARANTINED = "quarantined"
    REJECTED = "rejected"


class CorpusSplit(StrEnum):
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"
    HOLDOUT = "holdout"


class SourceFileEntry(HashedExperienceContract):
    relative_path: NonEmptyStr
    size_bytes: int = Field(ge=0)
    media_type: NonEmptyStr
    file_hash: Sha256Hex
    content_hash: str = ""
    encoding: NonEmptyStr | None = None
    archive_origin: NonEmptyStr | None = None
    is_symlink: bool = False
    is_hard_link: bool = False

    @field_validator("relative_path")
    @classmethod
    def path_is_safe(cls, value: str) -> str:
        posix = PurePosixPath(value)
        if (
            posix.is_absolute()
            or PureWindowsPath(value).is_absolute()
            or ".." in posix.parts
            or re.match(r"^[A-Za-z]:[\\/]", value)
        ):
            raise ValueError("source path must be normalized and relative")
        normalized = posix.as_posix()
        if normalized in {"", "."}:
            raise ValueError("source path must name a file")
        return normalized


class SourceArchiveEntry(SourceFileEntry):
    compressed_size_bytes: int = Field(ge=0)


class SourceInspectionReport(HashedExperienceContract):
    source_identity: NonEmptyStr
    entries: Annotated[tuple[SourceFileEntry, ...], Field(min_length=1, max_length=10_000)]
    total_bytes: int = Field(ge=0)
    warnings: tuple[NonEmptyStr, ...] = ()
    safe: bool


class SourceIntegrityResult(HashedExperienceContract):
    passed: bool
    artifact_hashes: tuple[Sha256Hex, ...]
    reason_codes: tuple[NonEmptyStr, ...] = ()


class LicenseDeclaration(HashedExperienceContract):
    identifier: NonEmptyStr
    status: CorpusLicenseStatus
    declared_by: NonEmptyStr
    evidence_refs: tuple[Sha256Hex, ...]


class UsageRightAssessment(HashedExperienceContract):
    right: CorpusUsageRight
    allowed: bool | None
    evidence_refs: tuple[Sha256Hex, ...]
    reason: NonEmptyStr


class SourceManifest(HashedExperienceContract):
    source_manifest_id: UUID
    source_type: CorpusSourceType
    source_identity: NonEmptyStr
    source_revision: NonEmptyStr
    content_artifacts: Annotated[tuple[ArtifactRef, ...], Field(min_length=1, max_length=10_000)]
    source_hashes: Annotated[tuple[Sha256Hex, ...], Field(min_length=1, max_length=10_000)]
    origin: NonEmptyStr
    license_declarations: tuple[LicenseDeclaration, ...]
    usage_right_declarations: tuple[UsageRightAssessment, ...]
    scope: NonEmptyStr
    sensitivity: MemorySensitivity
    language: NonEmptyStr | None = None
    encoding: NonEmptyStr | None = None
    created_at: UtcDatetime
    created_by: NonEmptyStr

    @model_validator(mode="after")
    def artifacts_match_hashes(self) -> SourceManifest:
        hashes = tuple(item.content_hash for item in self.content_artifacts)
        if hashes != self.source_hashes:
            raise ValueError("source artifact hashes must use deterministic artifact order")
        if PurePosixPath(self.source_identity).is_absolute() or re.match(
            r"^[A-Za-z]:[\\/]", self.source_identity
        ):
            raise ValueError("source identity must not expose a raw host path")
        return self


class CorpusResourceLimits(HashedExperienceContract):
    maximum_item_bytes: int = Field(ge=1)
    maximum_files: int = Field(ge=1)
    maximum_archive_depth: int = Field(ge=1)


class NormalizationProfile(HashedExperienceContract):
    profile_id: NonEmptyStr
    version: int = Field(ge=1)
    supported_formats: frozenset[NonEmptyStr]
    newline_policy: NonEmptyStr = "lf"
    unicode_policy: NonEmptyStr = "nfc"
    whitespace_policy: NonEmptyStr = "trim-trailing"
    metadata_policy: NonEmptyStr = "separate"
    code_policy: NonEmptyStr = "parse-without-execution"
    diff_policy: NonEmptyStr = "validate-without-application"
    binary_policy: NonEmptyStr = "reject"
    resource_limits: CorpusResourceLimits


class NormalizedContent(HashedExperienceContract):
    normalized_content_id: UUID
    source_manifest_id: UUID
    source_file_refs: tuple[SourceFileEntry, ...]
    content_type: CorpusContentType
    original_artifact_refs: Annotated[tuple[ArtifactRef, ...], Field(min_length=1)]
    normalized_artifact_ref: ArtifactRef
    canonical_content_hash: Sha256Hex
    normalization_profile: NonEmptyStr
    language: NonEmptyStr | None = None
    encoding: NonEmptyStr | None = None
    warnings: tuple[NonEmptyStr, ...] = ()
    created_at: UtcDatetime

    @model_validator(mode="after")
    def normalized_hash_matches_artifact(self) -> NormalizedContent:
        if self.canonical_content_hash != self.normalized_artifact_ref.content_hash:
            raise ValueError("normalized artifact hash mismatch")
        return self


class CorpusLineageEdge(HashedExperienceContract):
    source_identity: NonEmptyStr
    target_identity: NonEmptyStr
    relationship: CorpusLineageRelationship
    evidence_refs: tuple[Sha256Hex, ...]

    @model_validator(mode="after")
    def disallow_self_cycle(self) -> CorpusLineageEdge:
        if self.source_identity == self.target_identity:
            raise ValueError("corpus lineage self-cycle is forbidden")
        return self


class CorpusSourceContribution(HashedExperienceContract):
    source_manifest_id: UUID
    contribution: NonEmptyStr
    evidence_refs: tuple[Sha256Hex, ...]


class CorpusLineage(HashedExperienceContract):
    lineage_id: UUID
    edges: tuple[CorpusLineageEdge, ...]
    contributions: Annotated[tuple[CorpusSourceContribution, ...], Field(min_length=1)]


class DuplicateEvidence(HashedExperienceContract):
    key_type: NonEmptyStr
    key_hash: Sha256Hex
    matched_item_id: UUID | None = None
    similarity: float | None = Field(default=None, ge=0, le=1)


class DuplicateCandidate(HashedExperienceContract):
    corpus_item_id: UUID
    candidate_item_id: UUID
    duplicate_type: CorpusDuplicateType
    evidence: tuple[DuplicateEvidence, ...]


class DuplicateDecision(HashedExperienceContract):
    corpus_item_id: UUID
    duplicate_type: CorpusDuplicateType
    evidence: tuple[DuplicateEvidence, ...]
    provenance_action: NonEmptyStr
    automatic_merge: bool = False

    @model_validator(mode="after")
    def prohibit_automatic_merge(self) -> DuplicateDecision:
        if self.automatic_merge:
            raise ValueError("automatic corpus duplicate merging is forbidden")
        return self


class DeduplicationProfile(HashedExperienceContract):
    profile_id: NonEmptyStr
    version: int = Field(ge=1)
    exact_keys: tuple[NonEmptyStr, ...]
    near_duplicate_advisory: bool = False
    near_duplicate_threshold: float = Field(default=0.95, ge=0, le=1)


class CorpusClassification(HashedExperienceContract):
    classification_id: UUID
    corpus_item_id: UUID
    item_revision: int = Field(ge=1)
    content_type: CorpusContentType
    domain: NonEmptyStr
    problem_class: NonEmptyStr
    knowledge_type: CorpusKnowledgeType
    candidate_destinations: Annotated[
        tuple[CorpusDestinationType, ...], Field(min_length=1, max_length=13)
    ]
    negative_example_type: NonEmptyStr | None = None
    training_suitability: bool
    benchmark_suitability: bool
    reference_suitability: bool
    confidence: float = Field(ge=0, le=1)
    classifier_profile: NonEmptyStr
    evidence: tuple[Sha256Hex, ...]
    limitations: tuple[NonEmptyStr, ...] = ()
    created_at: UtcDatetime


class LicenseConflict(HashedExperienceContract):
    identifiers: Annotated[tuple[NonEmptyStr, ...], Field(min_length=2)]
    evidence_refs: tuple[Sha256Hex, ...]


class LicenseClassification(HashedExperienceContract):
    classification_id: UUID
    corpus_item_id: UUID
    item_revision: int = Field(ge=1)
    status: CorpusLicenseStatus
    declarations: tuple[LicenseDeclaration, ...]
    rights: Annotated[tuple[UsageRightAssessment, ...], Field(min_length=8, max_length=8)]
    conflicts: tuple[LicenseConflict, ...] = ()
    profile: NonEmptyStr
    created_at: UtcDatetime

    @model_validator(mode="after")
    def has_each_usage_right_once(self) -> LicenseClassification:
        if {item.right for item in self.rights} != set(CorpusUsageRight):
            raise ValueError("license classification must assess every usage right")
        return self


class LicensePolicyDecision(HashedExperienceContract):
    corpus_item_id: UUID
    destination: CorpusDestinationType
    outcome: LicensePolicyOutcome
    policy_id: NonEmptyStr
    policy_version: int = Field(ge=1)
    reason_codes: tuple[NonEmptyStr, ...]
    evidence_refs: tuple[Sha256Hex, ...]


class CorpusSecretFinding(HashedExperienceContract):
    finding_type: NonEmptyStr
    relative_path: NonEmptyStr
    line_number: int | None = Field(default=None, ge=1)
    fingerprint: Sha256Hex


class CorpusPrivacyFinding(HashedExperienceContract):
    finding_type: NonEmptyStr
    relative_path: NonEmptyStr
    review_required: bool = True


class CorpusSensitivityAssessment(HashedExperienceContract):
    assessment_id: UUID
    corpus_item_id: UUID
    item_revision: int = Field(ge=1)
    inherited_sensitivity: MemorySensitivity
    effective_sensitivity: MemorySensitivity
    status: CorpusSensitivityStatus
    secret_findings: tuple[CorpusSecretFinding, ...] = ()
    privacy_findings: tuple[CorpusPrivacyFinding, ...] = ()
    compatible_destinations: tuple[CorpusDestinationType, ...]
    reason_codes: tuple[NonEmptyStr, ...]
    created_at: UtcDatetime

    @model_validator(mode="after")
    def sensitivity_cannot_be_lowered(self) -> CorpusSensitivityAssessment:
        order = list(MemorySensitivity)
        if order.index(self.effective_sensitivity) < order.index(self.inherited_sensitivity):
            raise ValueError("corpus sensitivity cannot be lowered silently")
        return self


class SensitivityPolicyDecision(HashedExperienceContract):
    corpus_item_id: UUID
    destination: CorpusDestinationType
    status: CorpusSensitivityStatus
    reason_codes: tuple[NonEmptyStr, ...]


class CorpusQualityDimension(HashedExperienceContract):
    dimension: CorpusQualityDimensionName
    score: float = Field(ge=0, le=1)
    status: NonEmptyStr
    evidence: tuple[Sha256Hex, ...]
    limitations: tuple[NonEmptyStr, ...] = ()
    profile_version: int = Field(ge=1)


class CorpusQualityProfile(HashedExperienceContract):
    profile_id: NonEmptyStr
    version: int = Field(ge=1)
    weights: dict[CorpusQualityDimensionName, float]
    hard_blockers: frozenset[NonEmptyStr]
    destination_thresholds: dict[CorpusDestinationType, float]

    @model_validator(mode="after")
    def weights_are_complete_and_normalized(self) -> CorpusQualityProfile:
        if set(self.weights) != set(CorpusQualityDimensionName):
            raise ValueError("quality profile must weight every dimension")
        if abs(sum(self.weights.values()) - 1.0) > 1e-9:
            raise ValueError("quality profile weights must total one")
        configured_values = (*self.weights.values(), *self.destination_thresholds.values())
        if any(not 0 <= value <= 1 for value in configured_values):
            raise ValueError("quality weights and thresholds must be finite unit values")
        return self


class CorpusQualityAssessment(HashedExperienceContract):
    assessment_id: UUID
    corpus_item_id: UUID
    item_revision: int = Field(ge=1)
    dimensions: Annotated[tuple[CorpusQualityDimension, ...], Field(min_length=12, max_length=12)]
    score: float = Field(ge=0, le=1)
    tier: CorpusQualityTier
    hard_blockers: tuple[NonEmptyStr, ...]
    limitations: tuple[NonEmptyStr, ...]
    profile_hash: Sha256Hex
    created_at: UtcDatetime

    @model_validator(mode="after")
    def has_each_dimension_once(self) -> CorpusQualityAssessment:
        if {item.dimension for item in self.dimensions} != set(CorpusQualityDimensionName):
            raise ValueError("quality assessment must contain every required dimension")
        if self.hard_blockers and self.tier is not CorpusQualityTier.BLOCKED:
            raise ValueError("hard blockers require blocked quality tier")
        return self


class CorpusItem(HashedExperienceContract):
    corpus_item_id: UUID
    current_status: CorpusItemStatus
    canonical_content_hash: Sha256Hex
    normalized_content_artifact: ArtifactRef
    source_manifest_refs: Annotated[tuple[UUID, ...], Field(min_length=1, max_length=1_024)]
    source_refs: Annotated[tuple[Sha256Hex, ...], Field(min_length=1, max_length=1_024)]
    scope: NonEmptyStr
    sensitivity: MemorySensitivity
    classification_ref: Sha256Hex | None = None
    quality_ref: Sha256Hex | None = None
    license_ref: Sha256Hex | None = None
    duplicate_ref: Sha256Hex | None = None
    lineage_ref: Sha256Hex
    created_at: UtcDatetime
    created_by: NonEmptyStr
    current_revision: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def artifact_matches_canonical_hash(self) -> CorpusItem:
        if self.normalized_content_artifact.content_hash != self.canonical_content_hash:
            raise ValueError("corpus item canonical hash must match normalized artifact")
        return self


class DestinationPolicyReference(HashedExperienceContract):
    destination: CorpusDestinationType
    policy_id: NonEmptyStr
    version: int = Field(ge=1)
    required_content_types: frozenset[CorpusContentType]
    required_quality: float = Field(ge=0, le=1)
    required_rights: frozenset[CorpusUsageRight]
    maximum_sensitivity: MemorySensitivity
    required_verifiers: frozenset[NonEmptyStr]
    package_schema: NonEmptyStr
    destination_available: bool


class CorpusRouteRequest(HashedExperienceContract):
    route_request_id: UUID
    corpus_item_id: UUID
    item_revision: int = Field(ge=1)
    destination: CorpusDestinationType
    destination_policy_hash: Sha256Hex
    requested_at: UtcDatetime
    requested_by: NonEmptyStr


class CorpusRouteDecision(HashedExperienceContract):
    route_decision_id: UUID
    corpus_item_id: UUID
    item_revision: int = Field(ge=1)
    destination: CorpusDestinationType
    destination_policy_hash: Sha256Hex
    status: CorpusRouteStatus
    reason_codes: tuple[NonEmptyStr, ...]
    required_verifiers: tuple[NonEmptyStr, ...]
    required_review: bool
    created_at: UtcDatetime


class DestinationPackageReference(HashedExperienceContract):
    package_id: UUID
    corpus_item_id: UUID
    item_revision: int = Field(ge=1)
    destination: CorpusDestinationType
    schema_version: NonEmptyStr
    artifact: ArtifactRef
    checksums: tuple[Sha256Hex, ...]
    authority_claims: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def package_has_no_authority_claim(self) -> DestinationPackageReference:
        if self.authority_claims:
            raise ValueError("destination packages cannot contain authority claims")
        return self


class CorpusRoutingReceipt(HashedExperienceContract):
    receipt_id: UUID
    route_decision_hash: Sha256Hex
    package: DestinationPackageReference
    promoted: bool = False
    created_at: UtcDatetime

    @model_validator(mode="after")
    def prohibit_promotion_receipt(self) -> CorpusRoutingReceipt:
        if self.promoted:
            raise ValueError("corpus routing receipts cannot claim promotion")
        return self


class CorpusManifestItem(HashedExperienceContract):
    corpus_item_id: UUID
    item_revision: int = Field(ge=1)
    item_hash: Sha256Hex
    split: CorpusSplit | None = None


class CorpusSplitManifest(HashedExperienceContract):
    profile_id: NonEmptyStr
    seed: int = Field(ge=0)
    assignments: tuple[CorpusManifestItem, ...]
    lineage_group_hashes: tuple[Sha256Hex, ...]


class CorpusManifest(HashedExperienceContract):
    corpus_id: UUID
    revision: int = Field(ge=1)
    previous_revision: int | None = Field(default=None, ge=1)
    purpose: CorpusDestinationType
    items: tuple[CorpusManifestItem, ...]
    selection_policy: NonEmptyStr
    normalization_profile: Sha256Hex
    deduplication_profile: Sha256Hex
    classification_profile: Sha256Hex
    quality_profile: Sha256Hex
    license_summary: dict[str, int]
    sensitivity_summary: dict[str, int]
    split_manifest: CorpusSplitManifest | None = None
    lineage_hash: Sha256Hex
    artifact_reference: ArtifactRef
    created_at: UtcDatetime
    created_by: NonEmptyStr

    @model_validator(mode="after")
    def revision_and_items_are_canonical(self) -> CorpusManifest:
        if (self.revision == 1) != (self.previous_revision is None):
            raise ValueError("manifest previous revision must be contiguous")
        identities = [(str(item.corpus_item_id), item.item_revision) for item in self.items]
        if identities != sorted(identities) or len(identities) != len(set(identities)):
            raise ValueError("manifest items must be unique and canonically ordered")
        return self


class CorpusExportRequest(HashedExperienceContract):
    export_id: UUID
    corpus_id: UUID
    corpus_revision: int = Field(ge=1)
    export_type: CorpusExportType
    requested_at: UtcDatetime
    requested_by: NonEmptyStr
    upload: bool = False
    train: bool = False

    @model_validator(mode="after")
    def prohibit_upload_and_training(self) -> CorpusExportRequest:
        if self.upload or self.train:
            raise ValueError("corpus export cannot upload content or initiate training")
        return self


class CorpusExportManifest(HashedExperienceContract):
    export_id: UUID
    corpus_id: UUID
    corpus_revision: int = Field(ge=1)
    export_type: CorpusExportType
    artifact: ArtifactRef
    item_hashes: tuple[Sha256Hex, ...]
    manifest_hash: Sha256Hex
    created_at: UtcDatetime


class CorpusExportResult(HashedExperienceContract):
    export_manifest: CorpusExportManifest
    reproduced: bool
    network_writes: int = Field(default=0, ge=0, le=0)
    training_actions: int = Field(default=0, ge=0, le=0)


class CorpusAccessRecord(HashedExperienceContract):
    access_id: UUID
    access_type: CorpusAccessType
    source_manifest_id: UUID | None = None
    corpus_item_id: UUID | None = None
    item_revision: int | None = Field(default=None, ge=1)
    corpus_id: UUID | None = None
    corpus_revision: int | None = Field(default=None, ge=1)
    export_id: UUID | None = None
    actor_id: NonEmptyStr
    accessed_at: UtcDatetime


class CorpusStatusTransition(HashedExperienceContract):
    corpus_item_id: UUID
    expected_revision: int = Field(ge=1)
    expected_status: CorpusItemStatus
    next_revision: int = Field(ge=2)
    next_status: CorpusItemStatus
    actor_id: NonEmptyStr
    reason: NonEmptyStr
    verifier_bundle_hash: Sha256Hex
    policy_decision_hash: Sha256Hex
    created_at: UtcDatetime

    @model_validator(mode="after")
    def revision_is_contiguous(self) -> CorpusStatusTransition:
        if self.next_revision != self.expected_revision + 1:
            raise ValueError("corpus status revision must be contiguous")
        return self


class CorpusVerifierResult(HashedExperienceContract):
    capability: NonEmptyStr
    passed: bool
    evidence_refs: tuple[Sha256Hex, ...]
    reason: NonEmptyStr


class CorpusVerifierBundle(HashedExperienceContract):
    bundle_id: UUID
    corpus_item_id: UUID
    item_revision: int = Field(ge=1)
    registry_hash: Sha256Hex
    results: Annotated[tuple[CorpusVerifierResult, ...], Field(min_length=20)]
    created_at: UtcDatetime

    @property
    def passed(self) -> bool:
        return all(item.passed for item in self.results)


class CorpusVerificationSubject(HashedExperienceContract):
    artifact_hashes: tuple[Sha256Hex, ...]


class CorpusSourceVerificationSubject(CorpusVerificationSubject):
    source_manifest_id: UUID
    source_manifest_hash: Sha256Hex


class CorpusNormalizationVerificationSubject(CorpusVerificationSubject):
    normalized_content_id: UUID
    normalization_profile_hash: Sha256Hex


class CorpusItemVerificationSubject(CorpusVerificationSubject):
    corpus_item_id: UUID
    item_revision: int = Field(ge=1)


class CorpusRouteVerificationSubject(CorpusItemVerificationSubject):
    route_decision_hash: Sha256Hex


class CorpusManifestVerificationSubject(CorpusVerificationSubject):
    corpus_id: UUID
    corpus_revision: int = Field(ge=1)


class CorpusExportVerificationSubject(CorpusManifestVerificationSubject):
    export_id: UUID
    export_hash: Sha256Hex


class CorpusFactoryRequest(HashedExperienceContract):
    request_id: UUID
    source_type: CorpusSourceType
    source_identity: NonEmptyStr
    source_revision: NonEmptyStr
    scope: NonEmptyStr
    sensitivity: MemorySensitivity
    license_identifiers: tuple[NonEmptyStr, ...] = ()
    usage_rights: dict[CorpusUsageRight, bool | None]
    requested_destination: CorpusDestinationType | None = None
    created_at: UtcDatetime
    created_by: NonEmptyStr


class CorpusFactoryResult(HashedExperienceContract):
    request_id: UUID
    source_manifest: SourceManifest
    normalized: tuple[NormalizedContent, ...]
    items: tuple[CorpusItem, ...]
    duplicates: tuple[DuplicateDecision, ...]
    classifications: tuple[CorpusClassification, ...]
    licenses: tuple[LicenseClassification, ...]
    sensitivity: tuple[CorpusSensitivityAssessment, ...]
    quality: tuple[CorpusQualityAssessment, ...]
    route_decisions: tuple[CorpusRouteDecision, ...]
    receipts: tuple[CorpusRoutingReceipt, ...]
    access_records: tuple[CorpusAccessRecord, ...]
    manifest: CorpusManifest | None = None
    export: CorpusExportResult | None = None
    warnings: tuple[NonEmptyStr, ...] = ()
    usage: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def prohibit_deferred_authority_usage(self) -> CorpusFactoryResult:
        forbidden = (
            "destination_writes",
            "training_actions",
            "network_writes",
            "automatic_promotions",
        )
        if any(self.usage.get(key, 0) != 0 for key in forbidden):
            raise ValueError("Corpus Factory results cannot report authoritative side effects")
        return self


PUBLIC_CORPUS_CONTRACTS: tuple[type[HashedExperienceContract], ...] = (
    SourceFileEntry,
    SourceArchiveEntry,
    SourceInspectionReport,
    SourceIntegrityResult,
    LicenseDeclaration,
    UsageRightAssessment,
    SourceManifest,
    CorpusResourceLimits,
    NormalizationProfile,
    NormalizedContent,
    CorpusLineageEdge,
    CorpusSourceContribution,
    CorpusLineage,
    DuplicateEvidence,
    DuplicateCandidate,
    DuplicateDecision,
    DeduplicationProfile,
    CorpusClassification,
    LicenseConflict,
    LicenseClassification,
    LicensePolicyDecision,
    CorpusSecretFinding,
    CorpusPrivacyFinding,
    CorpusSensitivityAssessment,
    SensitivityPolicyDecision,
    CorpusQualityDimension,
    CorpusQualityProfile,
    CorpusQualityAssessment,
    CorpusItem,
    DestinationPolicyReference,
    CorpusRouteRequest,
    CorpusRouteDecision,
    DestinationPackageReference,
    CorpusRoutingReceipt,
    CorpusManifestItem,
    CorpusSplitManifest,
    CorpusManifest,
    CorpusExportRequest,
    CorpusExportManifest,
    CorpusExportResult,
    CorpusAccessRecord,
    CorpusStatusTransition,
    CorpusVerifierResult,
    CorpusVerifierBundle,
    CorpusSourceVerificationSubject,
    CorpusNormalizationVerificationSubject,
    CorpusItemVerificationSubject,
    CorpusRouteVerificationSubject,
    CorpusManifestVerificationSubject,
    CorpusExportVerificationSubject,
    CorpusFactoryRequest,
    CorpusFactoryResult,
)
