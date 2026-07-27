"""Sprint 21C1: the boundaries durable learned evidence enforces in the contract layer.

These are the rules that must hold before any database exists, because a contract that
only fails at a CHECK constraint is a contract the in-memory implementation can violate.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from cognitive_os.domain.learned import LearnedComponentState, ProvenanceClass
from cognitive_os.domain.learned_evidence import (
    LearnedActivationAction,
    LearnedActivationApproval,
    LearnedActivationReceipt,
    LearnedApprovalAuthorityKind,
    LearnedArtifactLineage,
    LearnedArtifactRole,
    LearnedComponentRevisionRecord,
    LearnedEvidenceKind,
    LearnedEvidenceRecord,
    LearnedObservationRecord,
    LearnedReplayResult,
    ObservationAttribution,
    ObservationStatus,
)
from cognitive_os.infrastructure.learned.postgres import tables

NOW = datetime.now(UTC)
HASH_A = "a" * 64
HASH_B = "b" * 64


def revision(**overrides: object) -> LearnedComponentRevisionRecord:
    fields: dict[str, object] = {
        "component_id": "inert-fixture",
        "revision": 1,
        "surface": "skill-selection",
        "state_after": LearnedComponentState.REGISTERED,
        "descriptor_hash": HASH_A,
        "actor": "operator",
        "authority": "operator",
        "reason": "register the inert fixture",
        "idempotency_key": "key-1",
        "recorded_at": NOW,
    }
    fields.update(overrides)
    return LearnedComponentRevisionRecord(**fields)  # type: ignore[arg-type]


class TestHashingSealsTheRecord:
    def test_a_round_trip_preserves_the_hash(self) -> None:
        original = revision()
        restored = LearnedComponentRevisionRecord.model_validate(original.model_dump())
        assert restored.content_hash == original.content_hash

    def test_one_changed_field_changes_the_hash(self) -> None:
        assert revision().content_hash != revision(reason="a different reason").content_hash


class TestTheLifecycleChainMustBeCoherent:
    def test_the_first_revision_cannot_name_a_predecessor(self) -> None:
        with pytest.raises(ValueError, match="cannot name a predecessor"):
            revision(previous_revision=0)

    def test_a_later_revision_must_name_its_predecessor(self) -> None:
        with pytest.raises(ValueError, match="must name its predecessor"):
            revision(revision=2, state_before=LearnedComponentState.REGISTERED)

    def test_a_predecessor_cannot_follow_its_successor(self) -> None:
        with pytest.raises(ValueError, match="must precede its successor"):
            revision(
                revision=2,
                previous_revision=5,
                state_before=LearnedComponentState.REGISTERED,
            )

    def test_reaching_active_without_evidence_is_refused(self) -> None:
        """The single most dangerous transition may never be evidence-free."""
        with pytest.raises(ValueError, match="requires both a promotion assessment"):
            revision(
                revision=2,
                previous_revision=1,
                state_before=LearnedComponentState.VERIFIED,
                state_after=LearnedComponentState.ACTIVE,
            )

    def test_reaching_active_with_both_hashes_is_allowed(self) -> None:
        record = revision(
            revision=2,
            previous_revision=1,
            state_before=LearnedComponentState.VERIFIED,
            state_after=LearnedComponentState.ACTIVE,
            promotion_assessment_hash=HASH_A,
            activation_approval_hash=HASH_B,
        )
        assert record.state_after is LearnedComponentState.ACTIVE


class TestApprovalAuthority:
    def approval(self, **overrides: object) -> LearnedActivationApproval:
        fields: dict[str, object] = {
            "approval_id": uuid4(),
            "component_id": "inert-fixture",
            "component_revision": 2,
            "surface": "skill-selection",
            "promotion_assessment_hash": HASH_A,
            "artifact_lineage_id": uuid4(),
            "approved": True,
            "approver": "operator",
            "approver_kind": LearnedApprovalAuthorityKind.HUMAN_OPERATOR,
            "reason": "bounded activation",
            "approved_at": NOW,
        }
        fields.update(overrides)
        return LearnedActivationApproval(**fields)  # type: ignore[arg-type]

    def test_a_human_operator_may_approve(self) -> None:
        assert self.approval().approved

    @pytest.mark.parametrize(
        "kind", [LearnedApprovalAuthorityKind.MODEL, LearnedApprovalAuthorityKind.PROVIDER]
    )
    def test_a_model_or_provider_cannot_approve(self, kind: object) -> None:
        """A component that can approve itself is not governed."""
        with pytest.raises(ValueError, match="cannot approve an activation"):
            self.approval(approver="candidate-model", approver_kind=kind)

    def test_a_model_may_still_record_a_refusal(self) -> None:
        """Refusals stay representable, so the refusal itself remains auditable."""
        assert not self.approval(
            approved=False,
            approver="candidate-model",
            approver_kind=LearnedApprovalAuthorityKind.MODEL,
        ).approved


class TestObservationIntakePolicy:
    def observation(self, **overrides: object) -> LearnedObservationRecord:
        fields: dict[str, object] = {
            "observation_id": uuid4(),
            "surface": "skill-selection",
            "source_kind": "domain_pilot_run",
            "source_payload_hash": HASH_A,
            "provenance_class": ProvenanceClass.REAL_GOVERNED_RUN,
            "attribution": ObservationAttribution.DIRECT,
            "status": ObservationStatus.ACCEPTED,
            "usage_rights_verified": True,
            "sensitivity": "internal",
            "decision_reason": "verifier confirmed the outcome",
            "evaluation_eligible": True,
            "idempotency_key": "obs-1",
            "recorded_at": NOW,
        }
        fields.update(overrides)
        return LearnedObservationRecord(**fields)  # type: ignore[arg-type]

    def test_a_real_governed_run_is_never_training_eligible(self) -> None:
        """Restated at intake, before a dataset exists to enforce it."""
        assert self.observation().training_eligible is False

    def test_self_play_may_be_training_eligible(self) -> None:
        assert self.observation(provenance_class=ProvenanceClass.SELF_PLAY).training_eligible

    def test_acceptance_requires_verified_rights(self) -> None:
        with pytest.raises(ValueError, match="requires verified usage rights"):
            self.observation(usage_rights_verified=False)

    def test_unknown_attribution_cannot_be_accepted(self) -> None:
        """Ambiguity has to stay visible, so it is quarantined rather than absorbed."""
        with pytest.raises(ValueError, match="attribution is unknown cannot be accepted"):
            self.observation(attribution=ObservationAttribution.UNKNOWN)

    def test_only_an_accepted_observation_is_evaluation_eligible(self) -> None:
        with pytest.raises(ValueError, match="only an accepted observation"):
            self.observation(
                status=ObservationStatus.QUARANTINED,
                decision_reason="ambiguous attribution",
                evaluation_eligible=True,
            )

    def test_a_quarantined_observation_records_its_reason(self) -> None:
        record = self.observation(
            status=ObservationStatus.QUARANTINED,
            attribution=ObservationAttribution.UNKNOWN,
            decision_reason="attribution could not be established",
            evaluation_eligible=False,
        )
        assert record.status is ObservationStatus.QUARANTINED
        assert record.training_eligible is False


class TestArtifactLineageIsInert:
    def lineage(self, **overrides: object) -> LearnedArtifactLineage:
        fields: dict[str, object] = {
            "lineage_id": uuid4(),
            "artifact_id": uuid4(),
            "role": LearnedArtifactRole.MODEL,
            "component_id": "inert-fixture",
            "media_type": "application/octet-stream",
            "declared_format": "safetensors",
            "declared_content_hash": HASH_A,
            "observed_content_hash": HASH_A,
            "size_bytes": 128,
            "verified_by": "artifact-verifier",
            "verified_at": NOW,
        }
        fields.update(overrides)
        return LearnedArtifactLineage(**fields)  # type: ignore[arg-type]

    def test_declared_and_observed_hashes_must_agree(self) -> None:
        with pytest.raises(ValueError, match="content hash mismatch"):
            self.lineage(observed_content_hash=HASH_B)

    def test_lineage_must_belong_to_a_component_or_dataset(self) -> None:
        with pytest.raises(ValueError, match="must belong to a component or a dataset"):
            self.lineage(component_id=None)

    def test_lineage_stores_no_bytes(self) -> None:
        """The whole point of lineage: identity and hashes, never content."""
        fields = set(self.lineage().model_dump())
        assert not fields & {"payload", "content", "data", "bytes"}


class TestActivationReceiptEvidence:
    def receipt(self, **overrides: object) -> LearnedActivationReceipt:
        fields: dict[str, object] = {
            "receipt_id": uuid4(),
            "action": LearnedActivationAction.ACTIVATION,
            "component_id": "inert-fixture",
            "component_revision": 2,
            "surface": "skill-selection",
            "artifact_lineage_id": uuid4(),
            "promotion_assessment_hash": HASH_A,
            "approval_id": uuid4(),
            "approval_hash": HASH_B,
            "actor": "operator",
            "authority": "operator",
            "reason": "bounded activation",
            "idempotency_key": "act-1",
            "recorded_at": NOW,
        }
        fields.update(overrides)
        return LearnedActivationReceipt(**fields)  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "missing",
        ["artifact_lineage_id", "promotion_assessment_hash", "approval_id", "approval_hash"],
    )
    def test_an_activation_must_name_every_piece_of_evidence(self, missing: str) -> None:
        with pytest.raises(ValueError, match="must name its evidence exactly"):
            self.receipt(**{missing: None})

    def test_a_rollback_must_name_what_it_restores(self) -> None:
        with pytest.raises(ValueError, match="must name the activation it restores"):
            self.receipt(
                action=LearnedActivationAction.ROLLBACK,
                artifact_lineage_id=None,
                promotion_assessment_hash=None,
                approval_id=None,
                approval_hash=None,
            )

    def test_a_rollback_cannot_target_itself(self) -> None:
        identifier = uuid4()
        with pytest.raises(ValueError, match="cannot target itself"):
            self.receipt(
                receipt_id=identifier,
                action=LearnedActivationAction.ROLLBACK,
                artifact_lineage_id=None,
                promotion_assessment_hash=None,
                approval_id=None,
                approval_hash=None,
                rollback_target_receipt_id=identifier,
            )

    def test_only_a_rollback_may_name_a_rollback_target(self) -> None:
        with pytest.raises(ValueError, match="only a rollback"):
            self.receipt(rollback_target_receipt_id=uuid4())


class TestEvidenceRecordsAreLocatable:
    def test_evidence_must_reference_a_component_or_dataset(self) -> None:
        with pytest.raises(ValueError, match="must reference a component or a dataset"):
            LearnedEvidenceRecord(
                evidence_id=uuid4(),
                evidence_kind=LearnedEvidenceKind.PROMOTION_ASSESSMENT,
                surface="skill-selection",
                schema_version="1",
                payload_hash=HASH_A,
                recorded_by="learning-service",
                recorded_at=NOW,
            )

    def test_an_unknown_evidence_kind_is_refused(self) -> None:
        with pytest.raises(ValueError):
            LearnedEvidenceRecord(
                evidence_id=uuid4(),
                evidence_kind="telepathy",  # type: ignore[arg-type]
                component_id="inert-fixture",
                surface="skill-selection",
                schema_version="1",
                payload_hash=HASH_A,
                recorded_by="learning-service",
                recorded_at=NOW,
            )


class TestReplayResultCannotBeSelfContradictory:
    def test_agreement_with_failures_is_refused(self) -> None:
        with pytest.raises(ValueError, match="cannot also claim agreement"):
            LearnedReplayResult(
                replayed_components=1,
                replayed_revisions=2,
                projection_matches=True,
                hash_chain_verified=True,
                failures=("revision 2 missing",),
                replayed_at=NOW,
            )

    def test_disagreement_must_say_what_disagreed(self) -> None:
        with pytest.raises(ValueError, match="must say what disagreed"):
            LearnedReplayResult(
                replayed_components=1,
                replayed_revisions=2,
                projection_matches=False,
                hash_chain_verified=True,
                replayed_at=NOW,
            )


class TestDatabaseConstraintsMirrorTheDomainEnums:
    """A CHECK constraint that drifts from its enum silently stops constraining."""

    @pytest.mark.parametrize(
        ("enum_values", "constraint_values"),
        [
            ({item.value for item in LearnedComponentState}, tables.LEARNED_COMPONENT_STATES),
            ({item.value for item in LearnedEvidenceKind}, tables.LEARNED_EVIDENCE_KINDS),
            ({item.value for item in ObservationStatus}, tables.LEARNED_OBSERVATION_STATUSES),
            (
                {item.value for item in ObservationAttribution},
                tables.LEARNED_OBSERVATION_ATTRIBUTIONS,
            ),
            ({item.value for item in ProvenanceClass}, tables.LEARNED_PROVENANCE_CLASSES),
            ({item.value for item in LearnedActivationAction}, tables.LEARNED_ACTIVATION_ACTIONS),
            ({item.value for item in LearnedArtifactRole}, tables.LEARNED_ARTIFACT_ROLES),
        ],
    )
    def test_the_allowlists_agree(
        self, enum_values: set[str], constraint_values: tuple[str, ...]
    ) -> None:
        assert enum_values == set(constraint_values)


class TestTheProjectionIsDerivedNotAuthoritative:
    def test_only_the_projection_is_absent_from_the_append_only_set(self) -> None:
        append_only = {table.name for table in tables.LEARNED_APPEND_ONLY_TABLES}
        every = {table.name for table in tables.LEARNED_EVIDENCE_TABLES}
        assert every - append_only == {"learned_components"}

    def test_a_projection_cannot_be_updated_before_it_was_created(self) -> None:
        from cognitive_os.domain.learned_evidence import LearnedProjectionRow

        with pytest.raises(ValueError, match="cannot be updated before it was created"):
            LearnedProjectionRow(
                component_id="inert-fixture",
                surface="skill-selection",
                descriptor_version="1",
                current_revision=1,
                current_state=LearnedComponentState.REGISTERED,
                descriptor_hash=HASH_A,
                created_at=NOW,
                updated_at=NOW - timedelta(seconds=1),
            )
