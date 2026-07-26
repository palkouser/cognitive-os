"""Builders for the inert learned-evidence fixture.

Everything here is deterministic and learns nothing. `AlwaysAbstainingRanker` is the
component under test throughout: it abstains unconditionally, so it is promotable in
shape while being incapable of changing any outcome. That is the point — Sprint 21C1
proves the *governance* of activation, and a fixture that could actually influence a
decision would let a persistence test be mistaken for evidence of usefulness.

None of these builders is importable from the shipped package, and nothing here is
registered as a default component. See ADR 0086.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4, uuid5

from cognitive_os.domain.common import ArtifactRef
from cognitive_os.domain.learned import (
    BaselineKind,
    BaselineLadder,
    BaselineRung,
    ForgettingAssessment,
    ForgettingVerdict,
    LearnedComponentDescriptor,
    LearnedPromotionAssessment,
    LearnedPromotionDecision,
    MandatoryPathInvariance,
    OutOfDistributionAssessment,
)
from cognitive_os.domain.learned_evidence import (
    LearnedActivationApproval,
    LearnedApprovalAuthorityKind,
    LearnedArtifactLineage,
    LearnedArtifactRole,
    LearnedEvidenceKind,
    LearnedEvidenceRecord,
    LearnedObservationRecord,
    ObservationAttribution,
    ObservationStatus,
    ProvenanceClass,
)
from cognitive_os.infrastructure.learned.reference import AlwaysAbstainingRanker, ConstantClassifier

FIXTURE_NOW = datetime(2026, 7, 26, 12, 0, tzinfo=UTC)
FIXTURE_NAMESPACE = UUID("0f8c1d2e-3a4b-5c6d-8e9f-0a1b2c3d4e5f")

#: The inert component. Promotable in shape, incapable of changing an outcome.
INERT = AlwaysAbstainingRanker()
#: The negative control: it cannot abstain, so it can never legitimately activate.
UNPROMOTABLE = ConstantClassifier()

ARTIFACT_ID = uuid5(FIXTURE_NAMESPACE, "model-artifact")
ARTIFACT_HASH = "c" * 64
ARTIFACT_SIZE = 128


def descriptor() -> LearnedComponentDescriptor:
    return INERT.descriptor


def surface() -> str:
    return INERT.descriptor.surface


def artifact_ref(**overrides: object) -> ArtifactRef:
    fields: dict[str, object] = {
        "artifact_id": ARTIFACT_ID,
        "media_type": "application/octet-stream",
        "content_hash": ARTIFACT_HASH,
        "size_bytes": ARTIFACT_SIZE,
        "storage_key": "cc/cc/" + ARTIFACT_HASH,
        "created_at": FIXTURE_NOW,
    }
    fields.update(overrides)
    return ArtifactRef(**fields)  # type: ignore[arg-type]


def lineage(*, verified_at: datetime | None = None, **overrides: object) -> LearnedArtifactLineage:
    fields: dict[str, object] = {
        "lineage_id": uuid5(FIXTURE_NAMESPACE, "lineage"),
        "artifact_id": ARTIFACT_ID,
        "role": LearnedArtifactRole.MODEL,
        "component_id": INERT.component_id,
        "media_type": "application/octet-stream",
        "declared_format": "none",
        "declared_content_hash": ARTIFACT_HASH,
        "observed_content_hash": ARTIFACT_HASH,
        "size_bytes": ARTIFACT_SIZE,
        "verified_by": "learned-evidence-fixture",
        "verified_at": verified_at or FIXTURE_NOW,
    }
    fields.update(overrides)
    return LearnedArtifactLineage(**fields)  # type: ignore[arg-type]


def ladder() -> BaselineLadder:
    """A ladder whose strongest non-learned rung is the deterministic baseline."""
    return BaselineLadder(
        ladder_id=uuid5(FIXTURE_NAMESPACE, "ladder"),
        surface=surface(),
        split="group-aware-by-case",
        rungs=(
            BaselineRung(
                name="majority",
                kind=BaselineKind.TRIVIAL,
                score=Decimal("0.40"),
                evaluated_count=200,
                abstained=0,
                confident_errors=120,
            ),
            BaselineRung(
                name="specificity_scope_statistics",
                kind=BaselineKind.DETERMINISTIC,
                score=Decimal("0.60"),
                evaluated_count=200,
                abstained=0,
                confident_errors=80,
            ),
        ),
        created_at=FIXTURE_NOW,
    )


def invariance(**overrides: object) -> MandatoryPathInvariance:
    """All three replays agree, which is what makes the component provably inert."""
    fields: dict[str, object] = {
        "record_id": uuid5(FIXTURE_NAMESPACE, "invariance"),
        "component_id": INERT.component_id,
        "case_set_hash": "d" * 64,
        "case_count": 200,
        "decision_hash_absent": "f" * 64,
        "decision_hash_disabled": "f" * 64,
        "decision_hash_abstaining": "f" * 64,
        "created_at": FIXTURE_NOW,
    }
    fields.update(overrides)
    return MandatoryPathInvariance(**fields)  # type: ignore[arg-type]


def forgetting(**overrides: object) -> ForgettingAssessment:
    fields: dict[str, object] = {
        "assessment_id": uuid5(FIXTURE_NAMESPACE, "forgetting"),
        "session_id": uuid5(FIXTURE_NAMESPACE, "forgetting-session"),
        "baseline_manifest_hash": "d" * 64,
        "per_domain_before": (("mathematics", 100), ("coding", 100)),
        "per_domain_after": (("mathematics", 100), ("coding", 100)),
        "regressed_cases": (),
        "retained_case_count": 200,
        "tolerance": 0,
        "verdict": ForgettingVerdict.RETAINED,
        "created_at": FIXTURE_NOW,
    }
    fields.update(overrides)
    return ForgettingAssessment(**fields)  # type: ignore[arg-type]


def out_of_distribution(**overrides: object) -> OutOfDistributionAssessment:
    fields: dict[str, object] = {
        "assessment_id": uuid5(FIXTURE_NAMESPACE, "ood"),
        "component_id": INERT.component_id,
        "held_out_groups": ("mathematics",),
        "evaluated_count": 200,
        "abstained": 200,
        "confident_errors": 0,
        "confidence_threshold": Decimal("0.5"),
        "created_at": FIXTURE_NOW,
    }
    fields.update(overrides)
    return OutOfDistributionAssessment(**fields)  # type: ignore[arg-type]


def promotion_assessment(**overrides: object) -> LearnedPromotionAssessment:
    """Eligible for operator approval. Eligibility is not activation."""
    fields: dict[str, object] = {
        "assessment_id": uuid5(FIXTURE_NAMESPACE, "promotion"),
        "component_id": INERT.component_id,
        "descriptor": descriptor(),
        "baseline_metric": Decimal("0.60"),
        "candidate_metric": Decimal("0.70"),
        "minimum_material_improvement": Decimal("0.05"),
        "forgetting": forgetting(),
        "invariance": invariance(),
        "baseline_ladder": ladder(),
        "out_of_distribution": out_of_distribution(),
        "decision": LearnedPromotionDecision.ELIGIBLE_FOR_OPERATOR_APPROVAL,
        "reason": "fixture assessment: shape only, no accuracy claim is made",
        "created_at": FIXTURE_NOW,
    }
    fields.update(overrides)
    return LearnedPromotionAssessment(**fields)  # type: ignore[arg-type]


def evidence(
    kind: LearnedEvidenceKind, payload_hash: str, **overrides: object
) -> LearnedEvidenceRecord:
    fields: dict[str, object] = {
        "evidence_id": uuid5(FIXTURE_NAMESPACE, f"evidence:{kind.value}:{payload_hash}"),
        "evidence_kind": kind,
        "component_id": INERT.component_id,
        "surface": surface(),
        "schema_version": "1",
        "payload_hash": payload_hash,
        "recorded_by": "learned-evidence-fixture",
        "recorded_at": FIXTURE_NOW,
    }
    fields.update(overrides)
    return LearnedEvidenceRecord(**fields)  # type: ignore[arg-type]


def approval(
    *,
    revision: int,
    promotion_hash: str,
    lineage_id: UUID | None = None,
    **overrides: object,
) -> LearnedActivationApproval:
    fields: dict[str, object] = {
        "approval_id": uuid4(),
        "component_id": INERT.component_id,
        "component_revision": revision,
        "surface": surface(),
        "promotion_assessment_hash": promotion_hash,
        "artifact_lineage_id": lineage_id or lineage().lineage_id,
        "approved": True,
        "approver": "release-operator",
        "approver_kind": LearnedApprovalAuthorityKind.HUMAN_OPERATOR,
        "reason": "fixture approval issued inside an isolated test",
        "approved_at": FIXTURE_NOW,
    }
    fields.update(overrides)
    return LearnedActivationApproval(**fields)  # type: ignore[arg-type]


def observation(**overrides: object) -> LearnedObservationRecord:
    fields: dict[str, object] = {
        "observation_id": uuid4(),
        "surface": surface(),
        "source_kind": "governed_task_run",
        "source_payload_hash": "e" * 64,
        "provenance_class": ProvenanceClass.SELF_PLAY,
        "attribution": ObservationAttribution.DIRECT,
        "status": ObservationStatus.ACCEPTED,
        "usage_rights_verified": True,
        "sensitivity": "internal",
        "decision_reason": "reproducible self-play outcome with direct attribution",
        "evaluation_eligible": True,
        "idempotency_key": "observation-1",
        "recorded_at": FIXTURE_NOW,
    }
    fields.update(overrides)
    return LearnedObservationRecord(**fields)  # type: ignore[arg-type]


class StubArtifactVerifier:
    """An Artifact Store that answers about metadata and hashes, and never loads bytes.

    It has no `load`, `open` or `deserialise` method on purpose: the stub can only be
    used the way the real port may be used, so a test cannot accidentally prove that a
    code path which deserialises an artifact works.
    """

    def __init__(
        self,
        *,
        known: dict[UUID, ArtifactRef] | None = None,
        verifies: bool = True,
    ) -> None:
        self._known = known if known is not None else {ARTIFACT_ID: artifact_ref()}
        self._verifies = verifies
        self.verify_calls: list[UUID] = []

    async def artifact_metadata(self, artifact_id: UUID) -> ArtifactRef | None:
        return self._known.get(artifact_id)

    async def verify_artifact(self, artifact_id: UUID) -> bool:
        self.verify_calls.append(artifact_id)
        return self._verifies and artifact_id in self._known
