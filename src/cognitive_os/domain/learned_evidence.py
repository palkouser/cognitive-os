"""Immutable contracts for durable learned evidence.

Sprint 21 proved a learning substrate whose state lived entirely in memory. These
contracts are what makes that state survivable: lifecycle history, artifact lineage,
typed evidence, governed-outcome intake, activation authority, and read audit.

Three boundaries are enforced here rather than in review, because review does not run
in CI:

* an activation names the *exact* promotion assessment and human approval that
  authorised it, by identity and by hash, so an activation can never be justified after
  the fact by a different assessment;
* an approval issued by a model or provider identity is refused, because a component
  that can approve itself is not governed;
* a real governed run enters the evidence store as evaluation-only, and the training
  exclusion already stated by `LearnedDatasetSnapshot` is restated at the observation
  level so the rule holds before a dataset exists.

Machine learning is a mandatory Cognitive OS capability, and no individual model is.
Nothing in this module authorises activating a component; it records what would have to
be true for an activation to be legitimate. See ADR 0086.
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from .common import NonEmptyStr, Sha256Hex, UtcDatetime
from .experience import HashedExperienceContract
from .learned import CorpusRole, LearnedComponentState, ProvenanceClass


class LearnedEvidenceKind(StrEnum):
    """The allowlisted evidence contracts the store accepts.

    One typed table rather than one table per contract; an unknown kind fails here and
    again at a database CHECK constraint, so an unrecognised record cannot be stored and
    later mistaken for evidence. See ADR 0086.
    """

    PREDICTION = "prediction"
    SHADOW_RESULT = "shadow_result"
    MANDATORY_PATH_INVARIANCE = "mandatory_path_invariance"
    FORGETTING_ASSESSMENT = "forgetting_assessment"
    DISTRIBUTION_COMPARISON = "distribution_comparison"
    RETRIEVAL_CAPACITY = "retrieval_capacity"
    BASELINE_LADDER = "baseline_ladder"
    OUT_OF_DISTRIBUTION_ASSESSMENT = "out_of_distribution_assessment"
    PROMOTION_ASSESSMENT = "promotion_assessment"


class ObservationAttribution(StrEnum):
    """How confidently an outcome can be attributed to the decision under study."""

    DIRECT = "direct"
    CONTRIBUTING = "contributing"
    UNKNOWN = "unknown"


class ObservationStatus(StrEnum):
    ACCEPTED = "accepted"
    QUARANTINED = "quarantined"
    REJECTED = "rejected"


class LearnedActivationAction(StrEnum):
    APPROVAL = "approval"
    ACTIVATION = "activation"
    DISABLE = "disable"
    ROLLBACK = "rollback"


class LearnedArtifactRole(StrEnum):
    """What a referenced artifact is, which decides how lineage may use it."""

    DATASET = "dataset"
    SPLIT_MANIFEST = "split_manifest"
    EXAMPLE_MANIFEST = "example_manifest"
    MODEL = "model"
    REPORT = "report"
    METRIC_BUNDLE = "metric_bundle"


class LearnedApprovalAuthorityKind(StrEnum):
    """Who issued an approval.

    `MODEL` and `PROVIDER` exist so that a self-approval can be *named* and refused,
    rather than being unrepresentable and therefore unchecked.
    """

    HUMAN_OPERATOR = "human_operator"
    MODEL = "model"
    PROVIDER = "provider"


class LearnedComponentRevisionRecord(HashedExperienceContract):
    """One append-only lifecycle step. This is the authority for learned state.

    The projection in `learned_components` is derived from these rows and is wrong by
    definition if replay disagrees with it.
    """

    component_id: NonEmptyStr
    revision: int = Field(ge=1)
    previous_revision: int | None = None
    surface: NonEmptyStr
    state_before: LearnedComponentState | None = None
    state_after: LearnedComponentState
    descriptor_hash: Sha256Hex
    artifact_lineage_id: UUID | None = None
    promotion_assessment_hash: Sha256Hex | None = None
    activation_approval_hash: Sha256Hex | None = None
    rollback_target_revision: int | None = None
    actor: NonEmptyStr
    authority: NonEmptyStr
    reason: NonEmptyStr
    idempotency_key: NonEmptyStr
    recorded_at: UtcDatetime

    @model_validator(mode="after")
    def chain_is_coherent(self) -> LearnedComponentRevisionRecord:
        if self.revision == 1:
            if self.previous_revision is not None:
                raise ValueError("the first revision cannot name a predecessor")
            if self.state_before is not None:
                raise ValueError("the first revision has no state before it")
        else:
            if self.previous_revision is None:
                raise ValueError("a non-initial revision must name its predecessor")
            if self.previous_revision >= self.revision:
                raise ValueError("a predecessor revision must precede its successor")
            if self.state_before is None:
                raise ValueError("a non-initial revision must record the state it left")
        if self.state_after is LearnedComponentState.ACTIVE and (
            self.promotion_assessment_hash is None or self.activation_approval_hash is None
        ):
            raise ValueError(
                "reaching the active state requires both a promotion assessment and an "
                "approval; an activation that cannot name them is not governed"
            )
        if (
            self.rollback_target_revision is not None
            and self.rollback_target_revision >= self.revision
        ):
            raise ValueError("a rollback target must precede the rollback")
        return self


class LearnedArtifactLineage(HashedExperienceContract):
    """A reference to bytes that already live in the Artifact Store.

    Bytes are never copied here. `observed_content_hash` is what verification actually
    read; it must equal what was declared, or the lineage is not usable.
    """

    lineage_id: UUID
    artifact_id: UUID
    role: LearnedArtifactRole
    component_id: NonEmptyStr | None = None
    dataset_id: UUID | None = None
    media_type: NonEmptyStr
    declared_format: NonEmptyStr
    declared_content_hash: Sha256Hex
    observed_content_hash: Sha256Hex
    size_bytes: int = Field(ge=0)
    producing_evidence_hash: Sha256Hex | None = None
    verified_by: NonEmptyStr
    verified_at: UtcDatetime

    @model_validator(mode="after")
    def content_is_what_it_claims(self) -> LearnedArtifactLineage:
        if self.declared_content_hash != self.observed_content_hash:
            raise ValueError(
                "artifact content hash mismatch: the bytes on disk are not the bytes "
                "this lineage declares"
            )
        if self.component_id is None and self.dataset_id is None:
            raise ValueError("artifact lineage must belong to a component or a dataset")
        return self


class LearnedEvidenceRecord(HashedExperienceContract):
    """One typed, hash-bound evidence payload reference.

    The payload itself stays in the Artifact Store when it is large; what is stored here
    is its identity, its kind and its hash, so evidence can be located and verified
    without the store growing without bound.
    """

    evidence_id: UUID
    evidence_kind: LearnedEvidenceKind
    component_id: NonEmptyStr | None = None
    dataset_id: UUID | None = None
    surface: NonEmptyStr
    source_run_id: UUID | None = None
    schema_version: NonEmptyStr
    payload_hash: Sha256Hex
    payload_artifact_id: UUID | None = None
    recorded_by: NonEmptyStr
    recorded_at: UtcDatetime

    @model_validator(mode="after")
    def evidence_is_locatable(self) -> LearnedEvidenceRecord:
        if self.component_id is None and self.dataset_id is None:
            raise ValueError("evidence must reference a component or a dataset")
        return self


class LearnedObservationRecord(HashedExperienceContract):
    """A governed outcome offered to the learning plane, and what was decided about it.

    An accepted observation is *not* a dataset example. Selection into a dataset is a
    separate, immutable manifest, so accepting an outcome never silently enrols it in
    training.
    """

    observation_id: UUID
    surface: NonEmptyStr
    source_kind: NonEmptyStr
    source_task_id: UUID | None = None
    source_run_id: UUID | None = None
    source_event_id: UUID | None = None
    source_payload_hash: Sha256Hex
    provenance_class: ProvenanceClass
    attribution: ObservationAttribution
    status: ObservationStatus
    verifier_status: NonEmptyStr | None = None
    verifier_evidence_hash: Sha256Hex | None = None
    usage_rights_verified: bool
    sensitivity: NonEmptyStr
    decision_reason: NonEmptyStr
    evaluation_eligible: bool
    idempotency_key: NonEmptyStr
    recorded_at: UtcDatetime

    @model_validator(mode="after")
    def decision_is_consistent(self) -> LearnedObservationRecord:
        if self.status is ObservationStatus.ACCEPTED:
            if not self.usage_rights_verified:
                raise ValueError("an accepted observation requires verified usage rights")
            if self.attribution is ObservationAttribution.UNKNOWN:
                raise ValueError(
                    "an observation whose attribution is unknown cannot be accepted; "
                    "quarantine it so the ambiguity stays visible"
                )
            if not self.evaluation_eligible:
                raise ValueError("an accepted observation must be eligible for evaluation")
        else:
            if self.evaluation_eligible:
                raise ValueError("only an accepted observation may be evaluation-eligible")
        return self

    @property
    def training_eligible(self) -> bool:
        """Real governed runs are evaluation-only, restated before any dataset exists."""
        return (
            self.status is ObservationStatus.ACCEPTED
            and self.provenance_class is not ProvenanceClass.REAL_GOVERNED_RUN
        )


class ObservationDecisionCode(StrEnum):
    """Why intake decided what it decided.

    Stable codes rather than free text: an operator reviewing a quarantine queue needs to
    group by cause, and a reason that is only prose can be reworded into a different
    category without anyone noticing.
    """

    ACCEPTED = "accepted"
    QUARANTINED_ATTRIBUTION_UNKNOWN = "quarantined_attribution_unknown"
    QUARANTINED_VERIFIER_EVIDENCE_MISSING = "quarantined_verifier_evidence_missing"
    QUARANTINED_SOURCE_INCOMPLETE = "quarantined_source_incomplete"
    REJECTED_USAGE_RIGHTS_UNVERIFIED = "rejected_usage_rights_unverified"
    REJECTED_PROVENANCE_NOT_CREDIBLE = "rejected_provenance_not_credible"

    @property
    def status(self) -> ObservationStatus:
        if self is ObservationDecisionCode.ACCEPTED:
            return ObservationStatus.ACCEPTED
        if self.value.startswith("quarantined_"):
            return ObservationStatus.QUARANTINED
        return ObservationStatus.REJECTED


class GovernedOutcomeReference(HashedExperienceContract):
    """A pointer to an outcome that already happened, offered to the learning plane.

    Carries identity and hashes only. The outcome itself stays where it was produced, so
    intake reads and classifies without ever modifying — or copying — a source record.

    `occurred_at` is the outcome's own time, taken from the event or record that produced
    it. Intake stamps it onto the observation instead of reading a clock, which is what
    makes re-offering the same outcome produce a byte-identical record rather than an
    idempotency conflict.
    """

    surface: NonEmptyStr
    source_kind: NonEmptyStr
    source_task_id: UUID | None = None
    source_run_id: UUID | None = None
    source_event_id: UUID | None = None
    source_payload_hash: Sha256Hex
    provenance_class: ProvenanceClass
    attribution: ObservationAttribution
    usage_rights_verified: bool
    sensitivity: NonEmptyStr
    verifier_status: NonEmptyStr | None = None
    verifier_evidence_hash: Sha256Hex | None = None
    occurred_at: UtcDatetime

    @model_validator(mode="after")
    def something_identifies_the_source(self) -> GovernedOutcomeReference:
        if (
            self.source_task_id is None
            and self.source_run_id is None
            and self.source_event_id is None
        ):
            raise ValueError(
                "a governed outcome must name the task, run or event it came from; an "
                "observation nobody can trace back is not evidence"
            )
        return self

    @property
    def identity(self) -> str:
        """The stable key two intakes of the same outcome must agree on."""
        return "|".join(
            (
                self.surface,
                self.source_kind,
                str(self.source_task_id),
                str(self.source_run_id),
                str(self.source_event_id),
            )
        )


class LearnedActivationApproval(HashedExperienceContract):
    """A human authorisation to activate one exact component revision."""

    approval_id: UUID
    component_id: NonEmptyStr
    component_revision: int = Field(ge=1)
    surface: NonEmptyStr
    promotion_assessment_hash: Sha256Hex
    artifact_lineage_id: UUID
    approved: bool
    approver: NonEmptyStr
    approver_kind: LearnedApprovalAuthorityKind
    reason: NonEmptyStr
    approved_at: UtcDatetime

    @model_validator(mode="after")
    def approval_authority_is_human(self) -> LearnedActivationApproval:
        if self.approved and self.approver_kind is not LearnedApprovalAuthorityKind.HUMAN_OPERATOR:
            raise ValueError(
                "a model or provider identity cannot approve an activation: a component "
                "that can approve itself is not governed"
            )
        return self


class LearnedActivationReceipt(HashedExperienceContract):
    """The immutable record of an activation, disable, rollback or approval action."""

    receipt_id: UUID
    action: LearnedActivationAction
    component_id: NonEmptyStr
    component_revision: int = Field(ge=1)
    surface: NonEmptyStr
    artifact_lineage_id: UUID | None = None
    promotion_assessment_hash: Sha256Hex | None = None
    approval_id: UUID | None = None
    approval_hash: Sha256Hex | None = None
    previous_receipt_id: UUID | None = None
    rollback_target_receipt_id: UUID | None = None
    actor: NonEmptyStr
    authority: NonEmptyStr
    reason: NonEmptyStr
    idempotency_key: NonEmptyStr
    recorded_at: UtcDatetime

    @model_validator(mode="after")
    def action_carries_its_evidence(self) -> LearnedActivationReceipt:
        if self.action is LearnedActivationAction.ACTIVATION:
            missing = [
                name
                for name, value in (
                    ("artifact_lineage_id", self.artifact_lineage_id),
                    ("promotion_assessment_hash", self.promotion_assessment_hash),
                    ("approval_id", self.approval_id),
                    ("approval_hash", self.approval_hash),
                )
                if value is None
            ]
            if missing:
                raise ValueError(
                    f"an activation must name its evidence exactly; missing: {sorted(missing)}"
                )
        if self.action is LearnedActivationAction.ROLLBACK:
            if self.rollback_target_receipt_id is None:
                raise ValueError("a rollback must name the activation it restores")
            if self.rollback_target_receipt_id == self.receipt_id:
                raise ValueError("a rollback cannot target itself")
        elif self.rollback_target_receipt_id is not None:
            raise ValueError("only a rollback may name a rollback target")
        return self


class LearnedExampleManifest(HashedExperienceContract):
    """Which observations a dataset is made of, by identity and hash.

    Stored in the Artifact Store, never in a table column. Two reasons, and the second is
    the important one: manifests grow with the corpus, and a manifest that lived in JSONB
    would tempt someone to put the example bodies in it. This carries references only, so
    a sensitive outcome is never copied into the learning plane's own storage.
    """

    dataset_id: UUID
    revision: int = Field(ge=1)
    surface: NonEmptyStr
    corpus_role: NonEmptyStr
    #: `(observation_id, source_payload_hash)` in a stable order. The hash is what makes
    #: the manifest verifiable: a selected observation that later changed is detectable.
    members: tuple[tuple[NonEmptyStr, Sha256Hex], ...]
    created_at: UtcDatetime

    @field_validator("members")
    @classmethod
    def canonical_members(cls, value: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
        """Sorted and de-duplicated, so selection order cannot change the dataset hash."""
        unique = dict(value)
        if len(unique) != len(value):
            raise ValueError("an observation cannot appear twice in one manifest")
        return tuple(sorted(value))

    @model_validator(mode="after")
    def a_manifest_selects_something(self) -> LearnedExampleManifest:
        if not self.members:
            raise ValueError("a dataset manifest must select at least one observation")
        return self


class LearnedSplitManifest(HashedExperienceContract):
    """How a dataset's members are divided, and by what rule.

    The rule is named rather than implied: a split whose policy is not recorded cannot be
    reproduced, and a comparison against an unreproducible split measures nothing.
    """

    dataset_id: UUID
    revision: int = Field(ge=1)
    policy: NonEmptyStr
    #: `(split_name, (observation_id, ...))`, both levels in a stable order.
    splits: tuple[tuple[NonEmptyStr, tuple[NonEmptyStr, ...]], ...]
    created_at: UtcDatetime

    @field_validator("splits")
    @classmethod
    def canonical_splits(
        cls, value: tuple[tuple[str, tuple[str, ...]], ...]
    ) -> tuple[tuple[str, tuple[str, ...]], ...]:
        return tuple(sorted((name, tuple(sorted(members))) for name, members in value))

    @model_validator(mode="after")
    def a_member_belongs_to_one_split(self) -> LearnedSplitManifest:
        seen: set[str] = set()
        for _, members in self.splits:
            overlap = seen & set(members)
            if overlap:
                raise ValueError(
                    f"observations appear in more than one split: {sorted(overlap)}; "
                    "an example evaluated on the split it trained on proves nothing"
                )
            seen |= set(members)
        return self


class LearnedDatasetRecord(HashedExperienceContract):
    """A durable, immutable dataset snapshot: what was selected, and how it was split.

    Mirrors `learned_datasets`. The training exclusion is enforced here *and* by a
    database CHECK, because a training corpus contaminated with real governed runs would
    not fail anything — it would only make every later distribution comparison mean less
    than it claims.
    """

    dataset_id: UUID
    revision: int = Field(ge=1)
    surface: NonEmptyStr
    corpus_role: CorpusRole
    feature_schema_hash: Sha256Hex
    split_manifest_artifact_id: UUID | None = None
    split_manifest_hash: Sha256Hex
    example_manifest_artifact_id: UUID | None = None
    example_manifest_hash: Sha256Hex
    #: `{provenance_class: count}`. A JSON object rather than a list of pairs, so the
    #: database CHECK can test key existence directly.
    provenance_counts: dict[str, int]
    observation_count: int = Field(ge=0)
    usage_rights_verified: bool
    sensitivity: NonEmptyStr
    created_at: UtcDatetime

    @field_validator("provenance_counts")
    @classmethod
    def only_known_provenance(cls, value: dict[str, int]) -> dict[str, int]:
        known = {item.value for item in ProvenanceClass}
        unknown = sorted(set(value) - known)
        if unknown:
            raise ValueError(f"unknown provenance classes in a dataset: {unknown}")
        if any(count < 0 for count in value.values()):
            raise ValueError("a provenance count cannot be negative")
        return dict(sorted(value.items()))

    @model_validator(mode="after")
    def training_excludes_real_runs(self) -> LearnedDatasetRecord:
        if self.corpus_role is CorpusRole.TRAINING:
            if ProvenanceClass.REAL_GOVERNED_RUN.value in self.provenance_counts:
                raise ValueError(
                    "a training dataset cannot contain real-governed-run evidence: the "
                    "evaluation corpus must stay uncontaminated"
                )
            if not self.usage_rights_verified:
                raise ValueError("a training dataset requires verified usage rights")
        if sum(self.provenance_counts.values()) != self.observation_count:
            raise ValueError("the provenance counts must add up to the observation count")
        return self


class LearnedAccessRecord(HashedExperienceContract):
    """Read and export audit for sensitive learned datasets and artifacts.

    The payload deliberately carries no example body: an audit trail that copies the
    sensitive content it audits has widened the exposure it exists to record.
    """

    access_id: UUID
    actor: NonEmptyStr
    authority: NonEmptyStr
    target_type: NonEmptyStr
    target_id: NonEmptyStr
    purpose: NonEmptyStr
    decision: NonEmptyStr
    recorded_at: UtcDatetime


class LearnedRepositoryConflict(StrEnum):
    """Why a write was refused. Each maps to a distinct caller response."""

    STALE_REVISION = "stale_revision"
    IDEMPOTENCY_KEY_REUSED = "idempotency_key_reused"
    SURFACE_ALREADY_ACTIVE = "surface_already_active"
    NOT_FOUND = "not_found"
    ILLEGAL_TRANSITION = "illegal_transition"
    EVIDENCE_MISMATCH = "evidence_mismatch"
    INTEGRITY_FAILURE = "integrity_failure"


class LearnedRepositoryError(RuntimeError):
    """A refused learned write, carrying the reason as a typed value."""

    def __init__(self, conflict: LearnedRepositoryConflict, detail: str) -> None:
        super().__init__(f"{conflict.value}: {detail}")
        self.conflict = conflict
        self.detail = detail


class LearnedProjectionRow(HashedExperienceContract):
    """The current state of one component, derived from its revision history."""

    component_id: NonEmptyStr
    surface: NonEmptyStr
    descriptor_version: NonEmptyStr
    current_revision: int = Field(ge=1)
    current_state: LearnedComponentState
    descriptor_hash: Sha256Hex
    artifact_lineage_id: UUID | None = None
    created_at: UtcDatetime
    updated_at: UtcDatetime

    @model_validator(mode="after")
    def timestamps_advance(self) -> LearnedProjectionRow:
        if self.updated_at < self.created_at:
            raise ValueError("a projection cannot be updated before it was created")
        return self


class LearnedReplayResult(HashedExperienceContract):
    """What replaying append-only history produced, and whether it agreed.

    Replay mutates nothing, so this is usable as a health check against a live
    database. Disagreement means the projection is wrong, by definition.
    """

    replayed_components: int = Field(ge=0)
    replayed_revisions: int = Field(ge=0)
    projection_matches: bool
    hash_chain_verified: bool
    failures: tuple[NonEmptyStr, ...] = ()
    replayed_at: UtcDatetime

    @field_validator("failures")
    @classmethod
    def canonical_failures(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted(set(value)))

    @model_validator(mode="after")
    def agreement_and_failures_are_consistent(self) -> LearnedReplayResult:
        healthy = self.projection_matches and self.hash_chain_verified
        if healthy and self.failures:
            raise ValueError("a replay that reported failures cannot also claim agreement")
        if not healthy and not self.failures:
            raise ValueError("a replay that disagreed must say what disagreed")
        return self


#: Contracts exported to `schemas/v1/learned/`. Kept beside the Sprint 21 tuple rather
#: than merged into it, so a durable-evidence contract cannot be mistaken for a runtime
#: learning contract when reading either list.
PUBLIC_LEARNED_EVIDENCE_CONTRACTS: tuple[type[HashedExperienceContract], ...] = (
    LearnedComponentRevisionRecord,
    LearnedProjectionRow,
    LearnedArtifactLineage,
    LearnedEvidenceRecord,
    GovernedOutcomeReference,
    LearnedObservationRecord,
    LearnedExampleManifest,
    LearnedSplitManifest,
    LearnedDatasetRecord,
    LearnedActivationApproval,
    LearnedActivationReceipt,
    LearnedAccessRecord,
    LearnedReplayResult,
)
