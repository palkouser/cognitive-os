"""Immutable contracts for governed provider output.

A provider is an advisory teacher. It can propose text, findings, tests or candidate
actions, and none of that is evidence until somebody decides three separate things about
it: whether the rights permit the intended use, whether the bytes may be retained at all,
and whether an *independent* verifier agreed with the content. This module is where those
three decisions become a record.

Two boundaries are enforced here rather than in review:

* the record carries identity, hashes and decisions, and never a prompt, a response body,
  an authorization value or a credential. `extra="forbid"` means a field carrying one
  cannot be added by accident;
* eligibility fails closed. Unknown rights, a failed or unrun secret scan, missing
  verifier evidence, an unrecognised sensitivity, an elapsed expiry or a physical-deletion
  obligation each make an output ineligible for corpus or training use, and no combination
  of the others rescues it.

Retention is deliberately *not* an extension of `LearnedObservationRecord`. That contract
is hash-bound and already has rows under migration `0014`; adding optional fields would
change the canonical hash of every one of them. See ADR 0087.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import Field, model_validator

from .base import ImmutableContractModel
from .common import NonEmptyStr, Sha256Hex, UtcDatetime
from .experience import HashedExperienceContract
from .memory import MemorySensitivity
from .model_requests import ModelProviderResponse

#: The sensitivity labels C1 learned intake recognises. `MemorySensitivity.CONFIDENTIAL`
#: is deliberately absent: intake's `KNOWN_SENSITIVITIES` does not know it, so a governed
#: output carrying it would quarantine on arrival for a reason nobody could act on. A new
#: sensitivity vocabulary would have been the other option, and two vocabularies that must
#: agree is the drift this refusal avoids.
GOVERNED_SENSITIVITIES: frozenset[MemorySensitivity] = frozenset(
    {
        MemorySensitivity.PUBLIC,
        MemorySensitivity.INTERNAL,
        MemorySensitivity.RESTRICTED,
    }
)

#: Sensitivities whose *normalized content* may be written to the Artifact Store. Restricted
#: content is representable and governable, but not storable: the Artifact Store is
#: immutable and content-addressed, so a later obligation to remove it could not be met.
STORABLE_SENSITIVITIES: frozenset[MemorySensitivity] = frozenset(
    {MemorySensitivity.PUBLIC, MemorySensitivity.INTERNAL}
)

#: Bumped when the contract's shape changes in a way stored revisions must be read against.
PROVIDER_OUTPUT_SCHEMA_VERSION = "1"


class ProviderAdapterKind(StrEnum):
    """Which adapter produced the output.

    Distinct from `ProviderKind`: two adapters share `cli_agent`, and the governance ledger
    has to be able to say *which* CLI answered.
    """

    MINIMAX = "minimax"
    OPENROUTER = "openrouter"
    CLAUDE_CODE = "claude_code"
    CODEX_CLI = "codex_cli"
    REPLAY = "replay"
    MOCK = "mock"


class ProviderOutputIntendedUse(StrEnum):
    """What the caller intends to do with the output, declared *before* the call.

    Declared up front because the rights question is not answerable in the abstract: the
    same response may be freely usable as transient advice and prohibited as training
    input, and a decision made after the bytes exist is a decision under pressure.
    """

    TRANSIENT_ADVICE = "transient_advice"
    EVALUATION_EVIDENCE = "evaluation_evidence"
    CORPUS_CANDIDATE = "corpus_candidate"
    SKILL_CANDIDATE = "skill_candidate"
    TRAINING_CANDIDATE = "training_candidate"


class UsageRightsDecision(StrEnum):
    UNKNOWN = "unknown"
    PROHIBITED = "prohibited"
    VERIFIED = "verified"


class SecretScanStatus(StrEnum):
    """Tri-state on purpose.

    "we redacted it" and "we checked and found nothing" are different claims. A scan that
    never ran cannot stand in for one that passed, so `NOT_RUN` blocks retention exactly as
    `FAILED` does.
    """

    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"


class ProviderOutputRetentionMode(StrEnum):
    """What is allowed to survive the call. `NONE` is the default everywhere."""

    NONE = "none"
    HASH_ONLY = "hash_only"
    NORMALIZED_CONTENT = "normalized_content"


class ProviderOutputVerifierStatus(StrEnum):
    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"


#: Intended uses that consume the output as *material* rather than reading it once.
#: Anything in this set needs verified rights and a passed scan before it is eligible.
_MATERIAL_USES: frozenset[ProviderOutputIntendedUse] = frozenset(
    {
        ProviderOutputIntendedUse.CORPUS_CANDIDATE,
        ProviderOutputIntendedUse.SKILL_CANDIDATE,
        ProviderOutputIntendedUse.TRAINING_CANDIDATE,
    }
)


class ProviderRetentionDirective(HashedExperienceContract):
    """The caller's explicit instruction for one governed execution.

    There is no default constructor value for `intended_use`: a governed call must say what
    it is for. `retention_mode` does default, to `NONE`, because the safe path should also
    be the one a caller reaches by not thinking about it.
    """

    intended_use: ProviderOutputIntendedUse
    retention_mode: ProviderOutputRetentionMode = ProviderOutputRetentionMode.NONE
    sensitivity: MemorySensitivity = MemorySensitivity.INTERNAL
    expires_at: UtcDatetime | None = None
    physical_deletion_required: bool = False
    prompt_template_id: NonEmptyStr | None = None
    prompt_template_version: NonEmptyStr | None = None

    @model_validator(mode="after")
    def directive_is_satisfiable(self) -> ProviderRetentionDirective:
        if self.sensitivity not in GOVERNED_SENSITIVITIES:
            raise ValueError(
                f"sensitivity {self.sensitivity.value!r} is not a label learned intake "
                "recognises; governed output must be public, internal or restricted"
            )
        if self.retention_mode is ProviderOutputRetentionMode.NORMALIZED_CONTENT:
            if self.physical_deletion_required:
                raise ValueError(
                    "normalized content cannot be retained under a physical-deletion "
                    "obligation: the Artifact Store is immutable, so the obligation could "
                    "not be met. Use hash_only or none"
                )
            if self.sensitivity not in STORABLE_SENSITIVITIES:
                raise ValueError(
                    f"{self.sensitivity.value} content may not be written to the immutable "
                    "Artifact Store; use hash_only or none"
                )
        if self.prompt_template_version is not None and self.prompt_template_id is None:
            raise ValueError("a prompt template version needs the template it versions")
        return self


class ProviderOutputRecord(HashedExperienceContract):
    """One immutable governance revision for one provider output.

    `provider_output_id` is stable across revisions; `revision` orders them. A rights
    revocation, a verifier correction or an expiry change appends a new revision and leaves
    every earlier row exactly as it was, so an audit can see what was believed and when.
    """

    #: The immutable identity of *this row*. `provider_output_id` is stable across
    #: revisions, so it cannot be the key: two revisions of one decision are two records.
    provider_output_revision_id: UUID
    provider_output_id: UUID
    revision: int = Field(ge=1)
    previous_revision_id: UUID | None = None
    schema_version: NonEmptyStr = PROVIDER_OUTPUT_SCHEMA_VERSION

    #: Provider identity and the call this governs.
    model_call_id: UUID
    provider_id: NonEmptyStr
    adapter_kind: ProviderAdapterKind
    requested_model: NonEmptyStr
    resolved_model: NonEmptyStr
    request_hash: Sha256Hex
    normalized_response_hash: Sha256Hex
    completed_event_id: UUID
    response_artifact_id: UUID | None = None
    response_artifact_hash: Sha256Hex | None = None

    #: Inputs, by identity. The prompt *body* is deliberately absent.
    prompt_template_id: NonEmptyStr | None = None
    prompt_template_version: NonEmptyStr | None = None
    parameter_hash: Sha256Hex
    input_source_ids: tuple[NonEmptyStr, ...] = ()
    input_source_hashes: tuple[Sha256Hex, ...] = ()

    #: The three decisions.
    intended_use: ProviderOutputIntendedUse
    rights_decision: UsageRightsDecision
    rights_evidence_hash: Sha256Hex | None = None
    sensitivity: MemorySensitivity
    secret_scan_status: SecretScanStatus
    secret_scan_evidence_hash: Sha256Hex | None = None
    secret_scan_ruleset_version: NonEmptyStr | None = None
    retention_mode: ProviderOutputRetentionMode
    expires_at: UtcDatetime | None = None
    physical_deletion_required: bool = False
    verifier_status: ProviderOutputVerifierStatus
    verifier_identity: NonEmptyStr | None = None
    verifier_evidence_hash: Sha256Hex | None = None
    human_reviewer: NonEmptyStr | None = None

    #: Provenance of the record itself.
    recorded_by: NonEmptyStr
    recorded_at: UtcDatetime
    idempotency_key: NonEmptyStr
    supersession_reason: NonEmptyStr | None = None

    @model_validator(mode="after")
    def record_is_coherent(self) -> ProviderOutputRecord:
        if self.revision == 1:
            if self.previous_revision_id is not None:
                raise ValueError("the first revision cannot name a predecessor")
            if self.supersession_reason is not None:
                raise ValueError("the first revision supersedes nothing")
        elif self.previous_revision_id is None:
            raise ValueError("a non-initial revision must name the revision it supersedes")
        if self.previous_revision_id == self.provider_output_revision_id:
            raise ValueError("a revision cannot supersede itself")

        if self.sensitivity not in GOVERNED_SENSITIVITIES:
            raise ValueError(
                f"sensitivity {self.sensitivity.value!r} is not a label learned intake recognises"
            )
        if len(self.input_source_ids) != len(self.input_source_hashes):
            raise ValueError("every input source must carry exactly one hash")

        artifact_present = self.response_artifact_id is not None
        if artifact_present != (self.response_artifact_hash is not None):
            raise ValueError("a retained response artifact must carry its content hash")

        if self.retention_mode is ProviderOutputRetentionMode.NORMALIZED_CONTENT:
            if not artifact_present:
                raise ValueError("normalized_content retention must name the artifact it retained")
            if self.rights_decision is not UsageRightsDecision.VERIFIED:
                raise ValueError("retaining normalized content requires verified usage rights")
            if self.secret_scan_status is not SecretScanStatus.PASSED:
                raise ValueError("retaining normalized content requires a passed secret scan")
            if self.physical_deletion_required:
                raise ValueError(
                    "normalized content cannot be retained under a physical-deletion "
                    "obligation; the Artifact Store cannot honour it"
                )
            if self.sensitivity not in STORABLE_SENSITIVITIES:
                raise ValueError(
                    f"{self.sensitivity.value} content may not be written to the immutable "
                    "Artifact Store"
                )
        elif artifact_present:
            raise ValueError(
                f"{self.retention_mode.value} retention must not name a response artifact"
            )

        if (
            self.secret_scan_status is not SecretScanStatus.NOT_RUN
            and self.secret_scan_evidence_hash is None
        ):
            raise ValueError("a secret scan that ran must record its evidence hash")
        if (
            self.verifier_status is not ProviderOutputVerifierStatus.NOT_RUN
            and self.verifier_evidence_hash is None
        ):
            raise ValueError("a verifier that ran must record its evidence hash")
        if self.verifier_evidence_hash is not None and self.verifier_identity is None:
            raise ValueError("verifier evidence must name the verifier that produced it")
        if self.verifier_identity is not None and self.verifier_identity == self.provider_id:
            raise ValueError(
                "a provider cannot verify its own output: schema validity proves shape, "
                "not correctness"
            )
        if self.rights_decision is UsageRightsDecision.VERIFIED and (
            self.rights_evidence_hash is None
        ):
            raise ValueError("a verified rights decision must name its evidence")
        if self.expires_at is not None and self.expires_at <= self.recorded_at:
            raise ValueError("an expiry must be after the moment the decision was recorded")
        return self

    def is_expired_at(self, moment: datetime) -> bool:
        """Expiry governs *future selection*, never the existence of stored bytes."""
        return self.expires_at is not None and moment >= self.expires_at

    def selection_refusals(self, moment: datetime) -> tuple[str, ...]:
        """Every reason this revision may not be newly selected, in a stable order.

        Returned as a tuple rather than a bool because an operator asking "why is this
        output not in my corpus" needs the whole answer, not the first refusal.
        """
        refusals: list[str] = []
        if self.rights_decision is not UsageRightsDecision.VERIFIED:
            refusals.append(f"usage rights are {self.rights_decision.value}")
        if self.secret_scan_status is not SecretScanStatus.PASSED:
            refusals.append(f"secret scan is {self.secret_scan_status.value}")
        if self.verifier_status is not ProviderOutputVerifierStatus.PASSED:
            refusals.append(f"verifier status is {self.verifier_status.value}")
        if self.is_expired_at(moment):
            refusals.append("the governance revision has expired")
        if self.physical_deletion_required:
            refusals.append("a physical-deletion obligation applies")
        if self.intended_use not in _MATERIAL_USES:
            refusals.append(f"intended use {self.intended_use.value} is not a material use")
        return tuple(refusals)

    def is_selectable_at(self, moment: datetime) -> bool:
        """Eligible for a *new* corpus or training selection. Fails closed by construction."""
        return not self.selection_refusals(moment)


class GovernedExecutionReceipt(ImmutableContractModel):
    """What one governed provider execution produced, by identity and hash.

    Deliberately not a superset of the response: it carries the normalized response the
    caller already has a right to see, plus the *handles* that make the call auditable. No
    raw provider payload, no request body, no credential, no routing detail beyond what the
    allowlist permitted into the response itself.
    """

    response: ModelProviderResponse
    provider_id: NonEmptyStr
    adapter_kind: ProviderAdapterKind
    requested_model: NonEmptyStr
    resolved_model: NonEmptyStr
    request_hash: Sha256Hex
    normalized_response_hash: Sha256Hex
    model_call_id: UUID
    completed_event_id: UUID | None = None
    request_artifact_id: UUID | None = None
    response_artifact_id: UUID | None = None
    retention_mode: ProviderOutputRetentionMode
    provider_output_id: UUID | None = None
    provider_output_revision: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def receipt_is_coherent(self) -> GovernedExecutionReceipt:
        if self.response.resolved_model != self.resolved_model:
            raise ValueError("the receipt must report the model the response actually used")
        if self.response.model_call_id != self.model_call_id:
            raise ValueError("the receipt must name the model call the response belongs to")
        if (self.provider_output_id is None) != (self.provider_output_revision is None):
            raise ValueError("a governance reference needs both its identity and its revision")
        if (
            self.retention_mode is ProviderOutputRetentionMode.NONE
            and self.response_artifact_id is not None
        ):
            raise ValueError("retention mode none must not retain a response artifact")
        return self


class ProviderOutputConflict(StrEnum):
    """Why a governance write was refused. Each maps to a distinct caller response."""

    IDEMPOTENCY_KEY_REUSED = "idempotency_key_reused"
    REVISION_CONFLICT = "revision_conflict"
    NOT_FOUND = "not_found"
    BROKEN_LINEAGE = "broken_lineage"
    RETENTION_REFUSED = "retention_refused"
    INTEGRITY_FAILURE = "integrity_failure"


class ProviderOutputRepositoryError(RuntimeError):
    """A refused governance write, carrying the reason as a typed value."""

    def __init__(self, conflict: ProviderOutputConflict, detail: str) -> None:
        super().__init__(f"{conflict.value}: {detail}")
        self.conflict = conflict
        self.detail = detail


#: Contracts exported to `schemas/v1/providers/`. The receipt is not hash-bound — it is a
#: return value, not a stored record — so the tuple is typed by the shared contract base.
PUBLIC_PROVIDER_OUTPUT_CONTRACTS: tuple[type[ImmutableContractModel], ...] = (
    ProviderRetentionDirective,
    ProviderOutputRecord,
    GovernedExecutionReceipt,
)
