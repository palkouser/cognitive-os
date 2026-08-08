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
from hashlib import sha256
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
from cognitive_os.domain.promotion_payload import (
    CONDITION_20_GATE,
    D3_PROMOTION_GATES,
    D3_PROMOTION_MEDIA_TYPE,
    CanaryToSteadyCondition,
    D3ArtifactBinding,
    D3PromotionAssessment,
    D3PromotionPayload,
    D3RuntimeConfiguration,
    PromotionDependency,
    PromotionGateOutcome,
    PromotionGateRecord,
    canonical_payload_bytes,
)
from cognitive_os.infrastructure.learned.reference import AlwaysAbstainingRanker, ConstantClassifier
from cognitive_os.learning.correction_protocol import DecisionCensusV4
from cognitive_os.learning.promotion import D3PromotionBindings, condition_20_gate

FIXTURE_NOW = datetime(2026, 7, 26, 12, 0, tzinfo=UTC)
FIXTURE_NAMESPACE = UUID("0f8c1d2e-3a4b-5c6d-8e9f-0a1b2c3d4e5f")

#: The inert component. Promotable in shape, incapable of changing an outcome.
INERT = AlwaysAbstainingRanker()
#: The negative control: it cannot abstain, so it can never legitimately activate.
UNPROMOTABLE = ConstantClassifier()

#: Real bytes with a real hash. An earlier version used a made-up digest, which let a
#: test insert artifact metadata with nothing behind it — exactly the metadata/filesystem
#: drift Sprint 21C1 exists to prevent, and which the restore verifier duly caught.
ARTIFACT_BYTES = b"inert reference component: this artifact is data and is never loaded\n"
ARTIFACT_HASH = sha256(ARTIFACT_BYTES).hexdigest()
ARTIFACT_SIZE = len(ARTIFACT_BYTES)
ARTIFACT_ID = uuid5(FIXTURE_NAMESPACE, "model-artifact")
#: The D3 promotion payload lives in the store as its own artifact, separate from the model.
#: Separate because verification re-reads both and they can drift independently.
D3_PAYLOAD_ARTIFACT_ID = uuid5(FIXTURE_NAMESPACE, "d3-promotion-payload-artifact")
#: The lifecycle revision a D3 promotion is about: the one sitting in SHADOW when it is
#: verified. Register is 1, SHADOW is 2, and VERIFIED becomes 3 — so an assessment that named
#: 3 would be about a state that does not exist until after the verification it authorises.
D3_VERIFIED_REVISION = 2


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
        "storage_key": f"{ARTIFACT_HASH[:2]}/{ARTIFACT_HASH[2:4]}/{ARTIFACT_HASH}",
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


def runtime_configuration(name: str, **overrides: object) -> D3RuntimeConfiguration:
    fields: dict[str, object] = {
        "name": name,
        "component_id": INERT.component_id,
        "component_revision": D3_VERIFIED_REVISION,
        "surface": surface(),
        "routed_group_ids": ("group-a",) if name == "exact_canary" else ("group-a", "group-b"),
        "routing_manifest_hash": "c" * 64,
        "sequence_mode": "stop_on_first_accepted",
        "persistence_enabled": True,
        "activation_enabled": True,
        "maximum_tasks": 20 if name == "exact_canary" else 200,
        "kill_switch_enabled": True,
        "maximum_inference_ms": 250,
        "fallback_on_refusal": "frozen deterministic baseline order",
    }
    fields.update(overrides)
    return D3RuntimeConfiguration(**fields)  # type: ignore[arg-type]


def transition_condition(**overrides: object) -> CanaryToSteadyCondition:
    fields: dict[str, object] = {
        "minimum_canary_tasks": 20,
        "rollback_target_revision": 1,
    }
    fields.update(overrides)
    return CanaryToSteadyCondition(**fields)  # type: ignore[arg-type]


#: The dependency set a D3 promotion is downstream of. Fixture values, but a complete set:
#: the evaluator's refusal for a missing dependency is only meaningful against a full one.
D3_DEPENDENCIES: dict[str, str] = {
    "feature_contract": "1" * 64,
    "dataset_snapshot": "2" * 64,
    "campaign_manifest": "3" * 64,
    "calibration_manifest": "4" * 64,
    "retrieval_protocol": "5" * 64,
}


def d3_gate(name: str, outcome: PromotionGateOutcome = PromotionGateOutcome.PASSED):
    """One gate row at the fixture baseline, carrying condition 20's census when it is that row.

    S21D4-048 makes the metamorphic/OOD row unbuildable without its two denominators once it
    claims a measurement, so the row a test wants to move has to be built rather than copied
    field by field. A `not_measured` outcome drops the census, because that is the distinction
    the payload validator enforces.
    """
    evidence_hash = sha256(name.encode()).hexdigest()
    detail = f"fixture: {name} measured and passed"
    if name != CONDITION_20_GATE or outcome is PromotionGateOutcome.NOT_MEASURED:
        return PromotionGateRecord(
            name=name, outcome=outcome, evidence_hash=evidence_hash, detail=detail
        )
    return condition_20_gate(
        outcome=outcome,
        evidence_hash=evidence_hash,
        detail=detail,
        census=DecisionCensusV4.from_feature_hashes(
            [sha256(f"fixture:decision:{index}".encode()).hexdigest() for index in range(20)]
        ),
        calibration_certificate_hash=sha256(b"fixture:calibration-certificate").hexdigest(),
    )


def d3_payload(**overrides: object) -> D3PromotionPayload:
    """Every gate passed. Individual tests fail one gate at a time from this baseline."""
    fields: dict[str, object] = {
        "component_id": INERT.component_id,
        "component_revision": D3_VERIFIED_REVISION,
        "surface": surface(),
        "code_revision": "21d3-fixture",
        "legacy_assessment_hash": promotion_assessment().content_hash,
        "legacy_decision": LearnedPromotionDecision.ELIGIBLE_FOR_OPERATOR_APPROVAL.value,
        "gates": tuple(d3_gate(name) for name in D3_PROMOTION_GATES),
        "dependencies": tuple(
            PromotionDependency(name=name, content_hash=value)
            for name, value in sorted(D3_DEPENDENCIES.items())
        ),
        "artifact": D3ArtifactBinding(
            artifact_id=ARTIFACT_ID,
            media_type="application/octet-stream",
            schema_name="correction-ranking-artifact-v2",
            schema_version=2,
            content_hash=ARTIFACT_HASH,
            size_bytes=ARTIFACT_SIZE,
        ),
        "canary_configuration_hash": runtime_configuration("exact_canary").content_hash,
        "steady_state_configuration_hash": runtime_configuration(
            "bounded_steady_state"
        ).content_hash,
        "canary_to_steady_condition_hash": transition_condition().content_hash,
        "recorded_at": FIXTURE_NOW,
    }
    fields.update(overrides)
    return D3PromotionPayload(**fields)  # type: ignore[arg-type]


def d3_payload_bytes(payload: D3PromotionPayload | None = None) -> bytes:
    return canonical_payload_bytes(payload or d3_payload())


def d3_payload_artifact(payload: D3PromotionPayload | None = None) -> ArtifactRef:
    data = d3_payload_bytes(payload)
    digest = sha256(data).hexdigest()
    return artifact_ref(
        artifact_id=D3_PAYLOAD_ARTIFACT_ID,
        media_type=D3_PROMOTION_MEDIA_TYPE,
        content_hash=digest,
        size_bytes=len(data),
        storage_key=f"{digest[:2]}/{digest[2:4]}/{digest}",
    )


def d3_assessment(payload: D3PromotionPayload | None = None, **overrides: object):
    resolved = payload or d3_payload()
    fields: dict[str, object] = {
        "assessment_id": uuid5(FIXTURE_NAMESPACE, "d3-promotion"),
        "component_id": INERT.component_id,
        "component_revision": D3_VERIFIED_REVISION,
        "surface": surface(),
        "payload_artifact_id": D3_PAYLOAD_ARTIFACT_ID,
        "payload_content_hash": sha256(canonical_payload_bytes(resolved)).hexdigest(),
        "decision": "eligible",
        "reason": "fixture assessment: every gate recorded as passed",
        "recorded_at": FIXTURE_NOW,
    }
    fields.update(overrides)
    return D3PromotionAssessment(**fields)  # type: ignore[arg-type]


def d3_bindings(**overrides: object) -> D3PromotionBindings:
    fields: dict[str, object] = {
        "component_id": INERT.component_id,
        "component_revision": D3_VERIFIED_REVISION,
        "surface": surface(),
        "artifact_content_hash": ARTIFACT_HASH,
        "artifact_size_bytes": ARTIFACT_SIZE,
        "canary_configuration": runtime_configuration("exact_canary"),
        "steady_state_configuration": runtime_configuration("bounded_steady_state"),
        "canary_to_steady_condition": transition_condition(),
        "dependency_hashes": dict(D3_DEPENDENCIES),
    }
    fields.update(overrides)
    return D3PromotionBindings(**fields)  # type: ignore[arg-type]


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


async def seed_artifact(engine: object, root: object) -> UUID:
    """Store the fixture bytes through the real Artifact Store and return its ID.

    Deliberately not a raw INSERT into `artifacts`. Metadata without bytes behind it is
    precisely the drift Sprint 21C1 refuses to create, and the restore verifier walks
    every artifact row, so a fabricated one breaks a release check several steps later.
    """
    from pathlib import Path

    from cognitive_os.infrastructure.artifacts.filesystem import ContentAddressedFilesystem
    from cognitive_os.infrastructure.artifacts.service import ArtifactService
    from cognitive_os.infrastructure.postgres.artifact_repository import (
        PostgresArtifactRepository,
    )

    service = ArtifactService(
        ContentAddressedFilesystem(Path(str(root))),
        PostgresArtifactRepository(engine),  # type: ignore[arg-type]
    )
    reference = await service.put_bytes(ARTIFACT_BYTES, media_type="application/octet-stream")
    return reference.artifact_id


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

    def corrupt(self) -> None:
        """Every subsequent rehash fails, as it would if the bytes were replaced on disk."""
        self._verifies = False

    def add(self, ref: ArtifactRef) -> None:
        """Put one more artifact in the store. Metadata only; there are still no bytes here."""
        self._known[ref.artifact_id] = ref

    async def artifact_metadata(self, artifact_id: UUID) -> ArtifactRef | None:
        return self._known.get(artifact_id)

    async def verify_artifact(self, artifact_id: UUID) -> bool:
        self.verify_calls.append(artifact_id)
        return self._verifies and artifact_id in self._known
