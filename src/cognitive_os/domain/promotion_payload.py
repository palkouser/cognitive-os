"""S21D3-048: what a D3 promotion has to say for itself, as bytes, in one versioned shape.

The v1 assessment in `domain.learned` records six things: a ladder, a forgetting verdict, an
invariance record, an OOD assessment, an optional distribution comparison, and a decision. Gate
L2 asks about twenty. The gap was closed in D1 and D2 by *reports* — prose beside the record,
saying what else had been measured — and prose is not evidence a verifier can check.

So the D3 payload names every gate as a row: what it measured, what that measurement hashes to,
and whether it passed. A gate nobody ran is `not_measured`, which is deliberately not a synonym
for `failed`: they need different remedies, and D2's narrative had to explain in prose which of
the two a blank field meant.

Three separations are load-bearing.

*The payload is not the assessment.* The payload is the bundle of measurements and lives in the
Artifact Store as inert bytes. The assessment is the decision, and it names the payload's
artifact ID and byte hash — so the assessment's own content hash commits to exactly which bytes
were read. A payload that embedded its own artifact identity could not be hashed without first
knowing what to exclude, which is the mistake the correction artifact already avoids.

*The configurations are sealed separately from the decision.* The exact canary and the bounded
steady state are two canonical documents with their own hashes, and the payload binds both. An
activation that could reinterpret its configuration after the evidence was read would make the
evidence about a system nobody ran.

*Nothing here decides anything.* Every field is a recorded measurement. The evaluator in
`learning.promotion` reads them; a payload that could talk itself into eligibility would make
every gate advisory, which is the failure `assess_promotion` was written to avoid.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from enum import StrEnum
from uuid import UUID

from pydantic import Field, model_validator

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, UtcDatetime
from cognitive_os.domain.experience import HashedExperienceContract

#: The payload schema. Named, not numbered alone: a v1 reader handed v2 bytes must fail on a
#: name it does not know rather than on whichever shared field the two shapes disagree about.
D3_PROMOTION_SCHEMA = "d3-promotion-payload"
D3_PROMOTION_SCHEMA_VERSION = 2

#: The legacy shape, still readable. Sprint 21D2 stored `LearnedPromotionAssessment` documents
#: directly, and those remain valid evidence of what they covered.
LEGACY_PROMOTION_SCHEMA = "learned-promotion-assessment"
LEGACY_PROMOTION_SCHEMA_VERSION = 1

D3_PROMOTION_MEDIA_TYPE = "application/vnd.cognitive-os.d3-promotion-payload+json"


class PromotionPayloadError(ValueError):
    """The bytes are not a usable promotion payload. Never a partial read."""


class PromotionGateOutcome(StrEnum):
    """What one gate concluded.

    `NOT_MEASURED` is not a weak `FAILED`. A gate that failed has a measurement and a verdict;
    a gate nobody ran has neither, and the second is the one that quietly turns a promotion
    into an assertion. Both refuse eligibility; only one of them names a result.
    """

    PASSED = "passed"
    FAILED = "failed"
    NOT_MEASURED = "not_measured"


#: Every gate a D3 promotion is made of, in first-failure precedence order: identity before
#: measurement, measurement before runtime, runtime last. The order is the order the recorded
#: reason is chosen in, so a payload with three failures names the most fundamental one.
D3_PROMOTION_GATES: tuple[str, ...] = (
    "feature_contract",
    "dataset_identity",
    "split_identity",
    "member_identity",
    "matrix",
    "calibration",
    "metamorphic_ood",
    "benefit",
    "paired_interval",
    "independent_batch_direction",
    "safety",
    "retention",
    "shadow",
    "retrieval",
    "resource",
    "fallback",
    "artifact",
    "canary_configuration",
    "steady_state_configuration",
    "canary_to_steady_transition",
)


class PromotionGateRecord(ImmutableContractModel):
    """One gate's measured result, and the evidence hash it is derived from."""

    name: NonEmptyStr
    outcome: PromotionGateOutcome
    #: The evidence this verdict came from. Present even when the gate failed — a failure
    #: without a locatable measurement is an opinion.
    evidence_hash: Sha256Hex
    detail: NonEmptyStr


class PromotionDependency(ImmutableContractModel):
    """One thing this promotion is downstream of, and the exact revision of it that was used."""

    name: NonEmptyStr
    content_hash: Sha256Hex


class D3ArtifactBinding(ImmutableContractModel):
    """The stored model bytes, described exactly as the Artifact Store describes them.

    Media type, schema and size travel with the hash because activation revalidates all four.
    An artifact substituted for one with the same hash is impossible; one substituted for a
    different artifact whose *metadata row* was edited is not, unless the metadata is bound too.
    """

    artifact_id: UUID
    media_type: NonEmptyStr
    #: What the bytes will have to declare when something eventually reads them. Verification
    #: never opens the artifact, so this is the loader's precondition travelling with the
    #: promotion rather than a field verification compares against the store.
    schema_name: NonEmptyStr
    schema_version: int = Field(ge=1)
    content_hash: Sha256Hex
    size_bytes: int = Field(ge=1)


class D3RuntimeConfiguration(HashedExperienceContract):
    """One canonical runtime configuration: the exact canary, or the bounded steady state.

    Sealed as a document rather than assembled from settings at start-up, because the question
    an operator has to answer after the fact is "which configuration produced this evidence",
    and a set of environment variables cannot answer it.
    """

    name: NonEmptyStr
    component_id: NonEmptyStr
    component_revision: int = Field(ge=1)
    surface: NonEmptyStr
    routed_group_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    routing_manifest_hash: Sha256Hex
    sequence_mode: NonEmptyStr
    persistence_enabled: bool
    activation_enabled: bool
    #: A bound on how much traffic this configuration may touch before it must stop and be
    #: re-decided. The canary's is small by construction; steady state's is the campaign size.
    maximum_tasks: int = Field(ge=1)
    kill_switch_enabled: bool
    maximum_inference_ms: int = Field(ge=1)
    fallback_on_refusal: NonEmptyStr
    declared_limitations: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def the_configuration_can_always_fall_back(self) -> D3RuntimeConfiguration:
        if not self.kill_switch_enabled:
            raise ValueError("a runtime configuration without a kill switch cannot be sealed")
        if self.sequence_mode not in {"label_all", "stop_on_first_accepted"}:
            raise ValueError(f"unknown sequence mode {self.sequence_mode!r}")
        if len(set(self.routed_group_ids)) != len(self.routed_group_ids):
            raise ValueError("a routed group is named twice")
        return self


class CanaryToSteadyCondition(HashedExperienceContract):
    """What a canary must show before the bounded steady state may be entered, and its rollback.

    Both halves in one document because they are one decision. A condition that named only the
    success path would leave "what happens otherwise" to whoever is holding the pager.
    """

    minimum_canary_tasks: int = Field(ge=1)
    maximum_accepted_safety_regressions: int = Field(default=0, ge=0)
    maximum_verifier_disagreements: int = Field(default=0, ge=0)
    requires_intact_receipt_chain: bool = True
    #: The revision a failed canary returns to. A failed canary is never restorable to itself;
    #: only a previously approval-bound state is eligible.
    rollback_target_revision: int = Field(ge=1)
    rollback_leaves_evidence_intact: bool = True

    @model_validator(mode="after")
    def a_failed_canary_is_not_restorable_to_itself(self) -> CanaryToSteadyCondition:
        if not self.requires_intact_receipt_chain or not self.rollback_leaves_evidence_intact:
            raise ValueError(
                "the transition condition may not waive the receipt chain or evidence retention"
            )
        return self


class D3PromotionPayload(HashedExperienceContract):
    """Every gate, every dependency, both configurations, and the bytes they are all about."""

    schema_name: NonEmptyStr = D3_PROMOTION_SCHEMA
    schema_version: int = Field(default=D3_PROMOTION_SCHEMA_VERSION, ge=2)

    component_id: NonEmptyStr
    component_revision: int = Field(ge=1)
    surface: NonEmptyStr
    code_revision: NonEmptyStr

    #: The v1 assessment this payload preserves, by hash. Legacy fields are not restated here;
    #: they are read from the assessment the hash names, so the two cannot drift apart.
    legacy_assessment_hash: Sha256Hex
    legacy_decision: NonEmptyStr

    gates: tuple[PromotionGateRecord, ...] = Field(min_length=1)
    dependencies: tuple[PromotionDependency, ...] = Field(min_length=1)

    artifact: D3ArtifactBinding
    canary_configuration_hash: Sha256Hex
    steady_state_configuration_hash: Sha256Hex
    canary_to_steady_condition_hash: Sha256Hex

    recorded_at: UtcDatetime

    @model_validator(mode="after")
    def every_gate_is_named_once_and_none_is_invented(self) -> D3PromotionPayload:
        if self.schema_name != D3_PROMOTION_SCHEMA:
            raise ValueError(f"unknown promotion payload schema {self.schema_name!r}")
        names = tuple(gate.name for gate in self.gates)
        if len(set(names)) != len(names):
            raise ValueError("a gate is recorded twice")
        unknown = sorted(set(names) - set(D3_PROMOTION_GATES))
        if unknown:
            raise ValueError(f"the payload records gates that do not exist: {unknown}")
        dependency_names = tuple(item.name for item in self.dependencies)
        if len(set(dependency_names)) != len(dependency_names):
            raise ValueError("a dependency is recorded twice")
        if self.canary_configuration_hash == self.steady_state_configuration_hash:
            raise ValueError("the canary and steady-state configurations must differ")
        return self

    @property
    def gate(self) -> Mapping[str, PromotionGateRecord]:
        return {item.name: item for item in self.gates}

    @property
    def missing_gates(self) -> tuple[str, ...]:
        """Gates the payload never mentions at all — as refusing as a recorded failure."""
        return tuple(name for name in D3_PROMOTION_GATES if name not in self.gate)


class D3PromotionAssessment(HashedExperienceContract):
    """The decision, bound to the exact payload bytes that justify it.

    This is what the evidence record's `payload_hash` equals, and it names the artifact its
    `payload_artifact_id` must resolve to. Verification can therefore check that the stored
    evidence, the stored bytes, and the decision are all about one another without loading
    anything.
    """

    assessment_id: UUID
    component_id: NonEmptyStr
    component_revision: int = Field(ge=1)
    surface: NonEmptyStr
    schema_version: int = Field(default=D3_PROMOTION_SCHEMA_VERSION, ge=2)

    #: The two facts that make this an assessment *of* those bytes.
    payload_artifact_id: UUID
    payload_content_hash: Sha256Hex

    decision: NonEmptyStr
    reason: NonEmptyStr
    recorded_at: UtcDatetime


def canonical_payload_bytes(payload: D3PromotionPayload | D3PromotionAssessment) -> bytes:
    """Sorted keys, no whitespace, UTF-8. The exact bytes the Artifact Store hashes."""
    return json.dumps(
        json.loads(payload.model_dump_json()),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()


def promotion_payload_version(data: bytes) -> int:
    """Which schema these bytes declare, without constructing either shape.

    Dispatch has to happen before validation. Handing v1 bytes to the v2 model produces a
    complaint about a missing field, which reads as a corrupt payload rather than as an older
    one that is still perfectly readable.
    """
    try:
        document = json.loads(data.decode("utf-8"))
    except UnicodeDecodeError as error:
        raise PromotionPayloadError("promotion payload bytes are not UTF-8") from error
    except json.JSONDecodeError as error:
        raise PromotionPayloadError("promotion payload bytes are not JSON") from error
    if not isinstance(document, dict):
        raise PromotionPayloadError("a promotion payload is a JSON object")
    name = document.get("schema_name", LEGACY_PROMOTION_SCHEMA)
    if name == D3_PROMOTION_SCHEMA:
        return int(document.get("schema_version", D3_PROMOTION_SCHEMA_VERSION))
    if name == LEGACY_PROMOTION_SCHEMA:
        return LEGACY_PROMOTION_SCHEMA_VERSION
    raise PromotionPayloadError(f"unknown promotion payload schema {name!r}")


def load_promotion_payload(data: bytes) -> D3PromotionPayload:
    """Read v2 bytes. A v1 document is reported as legacy rather than coerced into v2."""
    version = promotion_payload_version(data)
    if version != D3_PROMOTION_SCHEMA_VERSION:
        raise PromotionPayloadError(
            f"these are schema version {version} bytes; read them through the legacy "
            "assessment contract, not the D3 payload"
        )
    try:
        return D3PromotionPayload.model_validate(json.loads(data.decode("utf-8")))
    except PromotionPayloadError:
        raise
    except Exception as error:  # pydantic raises its own type; the verdict is the same
        raise PromotionPayloadError(
            f"payload does not match the declared schema: {error}"
        ) from error


#: Exported for schema generation. The configurations and the condition are included because
#: an operator reading a sealed hash has to be able to see what shape produced it.
PUBLIC_PROMOTION_PAYLOAD_CONTRACTS: tuple[type[HashedExperienceContract], ...] = (
    D3RuntimeConfiguration,
    CanaryToSteadyCondition,
    D3PromotionPayload,
    D3PromotionAssessment,
)
