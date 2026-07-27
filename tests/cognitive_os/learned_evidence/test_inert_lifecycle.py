"""S21C1-021: the full governed lifecycle, driven end to end by an inert fixture.

Nothing in this file demonstrates that the system learns anything. The component under
test abstains unconditionally: it cannot change a decision, and no accuracy claim is made
about it anywhere. What the file demonstrates is that the *governance* around activation
holds — that an activation without exact evidence fails, that a rollback restores only
what was actually approved before, and that the state survives losing the service object.

Gate C1 is about durability and authority. Gate L2, which is about usefulness, remains
closed and is untouched by every assertion here.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from cognitive_os.application.services.learned_evidence import LearnedEvidenceService
from cognitive_os.domain.learned import (
    LearnedComponentDescriptor,
    LearnedComponentState,
    LearnedPromotionDecision,
)
from cognitive_os.domain.learned_evidence import (
    LearnedActivationAction,
    LearnedApprovalAuthorityKind,
    LearnedEvidenceKind,
    LearnedRepositoryConflict,
    LearnedRepositoryError,
)
from cognitive_os.events.learned_event_service import LearnedEventService
from cognitive_os.events.memory_store import MemoryEventStore
from cognitive_os.infrastructure.learned.memory_repository import (
    InMemoryLearnedEvidenceRepository,
)

from . import fixtures as fx

OPERATOR = "release-operator"
CORRELATION = uuid4()

#: The only caller allowed to activate anything, and only inside these tests.
ACTIVATION_ACTORS = frozenset({OPERATOR})


class LifecycleHarness:
    """A service, its repository, its Artifact Store stub and its event store."""

    def __init__(self, *, activation_actors: frozenset[str] = ACTIVATION_ACTORS) -> None:
        self.repository = InMemoryLearnedEvidenceRepository()
        self.artifacts = fx.StubArtifactVerifier()
        self.store = MemoryEventStore()
        self.events = LearnedEventService(self.store)
        self.service = self._service(activation_actors)
        self.assessment = fx.promotion_assessment()
        self.lineage = fx.lineage()

    def _service(self, activation_actors: frozenset[str]) -> LearnedEvidenceService:
        return LearnedEvidenceService(
            self.repository,
            artifacts=self.artifacts,
            events=self.events,
            activation_actors=activation_actors,
            clock=lambda: fx.FIXTURE_NOW,
        )

    def restart(self) -> LearnedEvidenceService:
        """Throw the service away and build a new one over the same durable state.

        The service must hold no authoritative state of its own. If it did, this would
        be the moment the system quietly forgot which component was active.
        """
        self.service = self._service(ACTIVATION_ACTORS)
        return self.service

    async def register(self) -> None:
        await self.service.register_component(
            fx.descriptor(),
            actor=OPERATOR,
            authority="operator",
            reason="register the inert reference component",
            idempotency_key="register-inert",
            correlation_id=CORRELATION,
        )
        await self.service.register_artifact_lineage(
            self.lineage,
            correlation_id=CORRELATION,
            actor=OPERATOR,
            authority="operator",
            reason="link the verified model artifact",
        )

    async def gather_evidence(self) -> None:
        """Shadow, invariance, forgetting, OOD and promotion evidence, in that order."""
        await self.service.advance_component(
            fx.INERT.component_id,
            LearnedComponentState.SHADOW,
            descriptor=fx.descriptor(),
            actor=OPERATOR,
            authority="operator",
            reason="observe in shadow",
            idempotency_key="to-shadow",
            correlation_id=CORRELATION,
        )
        for kind, payload_hash in (
            (LearnedEvidenceKind.SHADOW_RESULT, fx.ARTIFACT_HASH),
            (LearnedEvidenceKind.MANDATORY_PATH_INVARIANCE, fx.invariance().content_hash),
            (LearnedEvidenceKind.FORGETTING_ASSESSMENT, fx.forgetting().content_hash),
            (
                LearnedEvidenceKind.OUT_OF_DISTRIBUTION_ASSESSMENT,
                fx.out_of_distribution().content_hash,
            ),
            (LearnedEvidenceKind.BASELINE_LADDER, fx.ladder().content_hash),
            (LearnedEvidenceKind.PROMOTION_ASSESSMENT, self.assessment.content_hash),
        ):
            await self.service.record_evidence(
                fx.evidence(kind, payload_hash),
                correlation_id=CORRELATION,
                actor=OPERATOR,
                authority="operator",
                reason=f"record {kind.value}",
            )
        await self.service.advance_component(
            fx.INERT.component_id,
            LearnedComponentState.VERIFIED,
            descriptor=fx.descriptor(),
            actor=OPERATOR,
            authority="operator",
            reason="evidence complete",
            idempotency_key="to-verified",
            correlation_id=CORRELATION,
        )

    async def approve(self, **overrides: object):  # type: ignore[no-untyped-def]
        approval = fx.approval(
            revision=3,
            promotion_hash=self.assessment.content_hash,
            lineage_id=self.lineage.lineage_id,
            **overrides,
        )
        return await self.service.record_approval(approval, correlation_id=CORRELATION)

    async def activate(self, approval, *, actor: str = OPERATOR):  # type: ignore[no-untyped-def]
        return await self.service.activate(
            descriptor=fx.descriptor(),
            component_revision=3,
            promotion_assessment=self.assessment,
            approval=approval,
            lineage=self.lineage,
            actor=actor,
            authority="operator",
            reason="activate the inert fixture inside an isolated test",
            idempotency_key="activate-inert",
            correlation_id=CORRELATION,
        )


async def ready() -> LifecycleHarness:
    harness = LifecycleHarness()
    await harness.register()
    await harness.gather_evidence()
    return harness


class TestTheFixtureReachesVerifiedWithItsEvidence:
    @pytest.mark.asyncio
    async def test_the_component_is_verified_and_holds_no_surface(self) -> None:
        harness = await ready()
        row = await harness.service.get_component(fx.INERT.component_id)
        assert row is not None
        assert row.current_state is LearnedComponentState.VERIFIED
        assert row.current_revision == 3
        assert await harness.service.active_component_for(fx.surface()) is None

    @pytest.mark.asyncio
    async def test_the_promotion_assessment_is_eligible_but_activates_nothing(self) -> None:
        """Eligibility is a precondition for approval, never a substitute for it."""
        harness = await ready()
        assert (
            harness.assessment.decision is LearnedPromotionDecision.ELIGIBLE_FOR_OPERATOR_APPROVAL
        )
        assert await harness.service.active_component_for(fx.surface()) is None


class TestActivationWithoutExactEvidenceFails:
    @pytest.mark.asyncio
    async def test_an_unrecorded_approval_is_refused(self) -> None:
        harness = await ready()
        never_recorded = fx.approval(
            revision=3,
            promotion_hash=harness.assessment.content_hash,
            lineage_id=harness.lineage.lineage_id,
        )
        with pytest.raises(LearnedRepositoryError, match="not the one recorded"):
            await harness.activate(never_recorded)

    @pytest.mark.asyncio
    async def test_an_approval_for_a_different_revision_is_refused(self) -> None:
        harness = await ready()
        approval = await harness.approve(component_revision=2)
        with pytest.raises(LearnedRepositoryError, match="component_revision"):
            await harness.activate(approval)

    @pytest.mark.asyncio
    async def test_an_approval_naming_a_different_assessment_is_refused(self) -> None:
        """The exact-evidence rule: an activation cannot be justified after the fact."""
        harness = await ready()
        approval = await harness.approve(promotion_assessment_hash="9" * 64)
        with pytest.raises(LearnedRepositoryError, match="promotion_assessment_hash"):
            await harness.activate(approval)

    @pytest.mark.asyncio
    async def test_a_refused_approval_cannot_activate(self) -> None:
        harness = await ready()
        approval = await harness.approve(
            approved=False,
            approver_kind=LearnedApprovalAuthorityKind.HUMAN_OPERATOR,
            reason="the operator declined",
        )
        with pytest.raises(LearnedRepositoryError, match="refused this activation"):
            await harness.activate(approval)

    @pytest.mark.asyncio
    async def test_a_refusal_by_a_model_identity_is_still_recorded(self) -> None:
        """A component cannot approve itself, but its refusal must stay auditable."""
        harness = await ready()
        refusal = await harness.approve(
            approved=False,
            approver="candidate-model",
            approver_kind=LearnedApprovalAuthorityKind.MODEL,
            reason="the candidate itself declined",
        )
        assert refusal.approver_kind is LearnedApprovalAuthorityKind.MODEL
        with pytest.raises(LearnedRepositoryError, match="refused this activation"):
            await harness.activate(refusal)

    @pytest.mark.asyncio
    async def test_a_model_identity_cannot_issue_a_positive_approval(self) -> None:
        harness = await ready()
        with pytest.raises(ValueError, match="cannot approve an activation"):
            await harness.approve(
                approver="candidate-model",
                approver_kind=LearnedApprovalAuthorityKind.MODEL,
            )

    @pytest.mark.asyncio
    async def test_an_unauthorised_caller_cannot_activate(self) -> None:
        """Persistence support for activation is not authorisation to activate."""
        harness = await ready()
        approval = await harness.approve()
        with pytest.raises(LearnedRepositoryError, match="not authorised to activate"):
            await harness.activate(approval, actor="some-background-job")

    @pytest.mark.asyncio
    async def test_the_default_service_authorises_nobody(self) -> None:
        harness = LifecycleHarness(activation_actors=frozenset())
        await harness.register()
        await harness.gather_evidence()
        approval = await harness.approve()
        with pytest.raises(LearnedRepositoryError, match="not authorised to activate"):
            await harness.activate(approval)

    @pytest.mark.asyncio
    async def test_activation_is_not_reachable_through_the_ordinary_transition(self) -> None:
        harness = await ready()
        with pytest.raises(LearnedRepositoryError, match="not an ordinary transition"):
            await harness.service.advance_component(
                fx.INERT.component_id,
                LearnedComponentState.ACTIVE,
                descriptor=fx.descriptor(),
                actor=OPERATOR,
                authority="operator",
                reason="sneak past the evidence requirement",
                idempotency_key="sneaky",
                correlation_id=CORRELATION,
            )

    @pytest.mark.asyncio
    async def test_an_unrecorded_promotion_assessment_is_refused(self) -> None:
        harness = LifecycleHarness()
        await harness.register()
        await harness.service.advance_component(
            fx.INERT.component_id,
            LearnedComponentState.SHADOW,
            descriptor=fx.descriptor(),
            actor=OPERATOR,
            authority="operator",
            reason="observe in shadow",
            idempotency_key="to-shadow",
            correlation_id=CORRELATION,
        )
        await harness.service.advance_component(
            fx.INERT.component_id,
            LearnedComponentState.VERIFIED,
            descriptor=fx.descriptor(),
            actor=OPERATOR,
            authority="operator",
            reason="skip straight past the evidence",
            idempotency_key="to-verified",
            correlation_id=CORRELATION,
        )
        approval = await harness.approve()
        with pytest.raises(LearnedRepositoryError, match="never recorded as evidence"):
            await harness.activate(approval)


class TestArtifactLineageIsVerifiedNeverLoaded:
    @pytest.mark.asyncio
    async def test_lineage_for_an_unknown_artifact_is_refused(self) -> None:
        harness = LifecycleHarness()
        harness.artifacts = fx.StubArtifactVerifier(known={})
        harness.service = harness._service(ACTIVATION_ACTORS)
        with pytest.raises(LearnedRepositoryError, match="not in the Artifact Store"):
            await harness.service.register_artifact_lineage(
                harness.lineage,
                correlation_id=CORRELATION,
                actor=OPERATOR,
                authority="operator",
                reason="link an artifact that does not exist",
            )

    @pytest.mark.asyncio
    async def test_lineage_whose_bytes_fail_verification_is_refused(self) -> None:
        harness = LifecycleHarness()
        harness.artifacts = fx.StubArtifactVerifier(verifies=False)
        harness.service = harness._service(ACTIVATION_ACTORS)
        with pytest.raises(LearnedRepositoryError, match="does not hash to"):
            await harness.service.register_artifact_lineage(
                harness.lineage,
                correlation_id=CORRELATION,
                actor=OPERATOR,
                authority="operator",
                reason="link a corrupted artifact",
            )

    @pytest.mark.asyncio
    async def test_the_artifact_store_stub_offers_no_way_to_load_bytes(self) -> None:
        """An artifact is data. A loader would make every lineage record an RCE surface."""
        verifier = fx.StubArtifactVerifier()
        for forbidden in ("load", "open", "deserialise", "deserialize", "get_bytes"):
            assert not hasattr(verifier, forbidden)


class TestTheGovernedActivationPath:
    @pytest.mark.asyncio
    async def test_exact_evidence_activates_the_component(self) -> None:
        harness = await ready()
        approval = await harness.approve()
        receipt = await harness.activate(approval)
        assert receipt.action is LearnedActivationAction.ACTIVATION
        assert receipt.approval_id == approval.approval_id
        assert receipt.promotion_assessment_hash == harness.assessment.content_hash
        row = await harness.service.get_component(fx.INERT.component_id)
        assert row is not None and row.current_state is LearnedComponentState.ACTIVE

    @pytest.mark.asyncio
    async def test_disable_then_rollback_restores_the_prior_activation(self) -> None:
        harness = await ready()
        approval = await harness.approve()
        activation = await harness.activate(approval)

        disabled = await harness.service.disable(
            fx.INERT.component_id,
            descriptor=fx.descriptor(),
            actor=OPERATOR,
            authority="operator",
            reason="withdraw the fixture",
            idempotency_key="disable-inert",
            correlation_id=CORRELATION,
        )
        assert disabled.action is LearnedActivationAction.DISABLE
        row = await harness.service.get_component(fx.INERT.component_id)
        assert row is not None and row.current_state is LearnedComponentState.DISABLED
        assert await harness.service.active_component_for(fx.surface()) is None

        rolled_back = await harness.service.roll_back(
            fx.INERT.component_id,
            descriptor=fx.descriptor(),
            actor=OPERATOR,
            authority="operator",
            reason="restore the prior activation",
            idempotency_key="rollback-inert",
            correlation_id=CORRELATION,
        )
        assert rolled_back.action is LearnedActivationAction.ROLLBACK
        assert rolled_back.rollback_target_receipt_id == activation.receipt_id
        assert rolled_back.approval_id == approval.approval_id
        restored = await harness.service.get_component(fx.INERT.component_id)
        assert restored is not None
        assert restored.current_state is LearnedComponentState.ACTIVE

    @pytest.mark.asyncio
    async def test_rollback_without_a_prior_activation_is_refused(self) -> None:
        harness = await ready()
        await harness.service.advance_component(
            fx.INERT.component_id,
            LearnedComponentState.DISABLED,
            descriptor=fx.descriptor(),
            actor=OPERATOR,
            authority="operator",
            reason="disable before ever activating",
            idempotency_key="disable-unactivated",
            correlation_id=CORRELATION,
        )
        with pytest.raises(LearnedRepositoryError, match="no prior activation"):
            await harness.service.roll_back(
                fx.INERT.component_id,
                descriptor=fx.descriptor(),
                actor=OPERATOR,
                authority="operator",
                reason="roll back to nothing",
                idempotency_key="rollback-nothing",
                correlation_id=CORRELATION,
            )

    @pytest.mark.asyncio
    async def test_an_unauthorised_caller_cannot_roll_back(self) -> None:
        harness = await ready()
        approval = await harness.approve()
        await harness.activate(approval)
        await harness.service.disable(
            fx.INERT.component_id,
            descriptor=fx.descriptor(),
            actor=OPERATOR,
            authority="operator",
            reason="withdraw",
            idempotency_key="disable-inert",
            correlation_id=CORRELATION,
        )
        with pytest.raises(LearnedRepositoryError, match="not authorised to activate"):
            await harness.service.roll_back(
                fx.INERT.component_id,
                descriptor=fx.descriptor(),
                actor="some-background-job",
                authority="operator",
                reason="restore without authority",
                idempotency_key="rollback-unauthorised",
                correlation_id=CORRELATION,
            )

    @pytest.mark.asyncio
    async def test_a_descriptor_that_does_not_match_the_store_is_refused(self) -> None:
        harness = await ready()
        approval = await harness.approve()
        rewritten = LearnedComponentDescriptor.model_validate(
            {
                **fx.descriptor().model_dump(),
                "declared_limitations": ("rewritten after registration",),
                "content_hash": "",
            }
        )
        assert rewritten.content_hash != fx.descriptor().content_hash
        with pytest.raises(LearnedRepositoryError, match="different descriptor hash"):
            await harness.service.activate(
                descriptor=rewritten,
                component_revision=3,
                promotion_assessment=harness.assessment,
                approval=approval,
                lineage=harness.lineage,
                actor=OPERATOR,
                authority="operator",
                reason="activate a component described differently",
                idempotency_key="activate-mismatched",
                correlation_id=CORRELATION,
            )


class TestTheStateSurvivesTheService:
    @pytest.mark.asyncio
    async def test_a_restarted_service_reconstructs_the_same_state(self) -> None:
        harness = await ready()
        approval = await harness.approve()
        await harness.activate(approval)
        before = harness.repository.snapshot()

        service = harness.restart()
        row = await service.get_component(fx.INERT.component_id)
        assert row is not None and row.current_state is LearnedComponentState.ACTIVE
        active = await service.active_component_for(fx.surface())
        assert active is not None and active.component_id == fx.INERT.component_id
        assert harness.repository.snapshot() == before

    @pytest.mark.asyncio
    async def test_replay_agrees_with_the_projection_after_the_full_lifecycle(self) -> None:
        harness = await ready()
        approval = await harness.approve()
        await harness.activate(approval)
        await harness.service.disable(
            fx.INERT.component_id,
            descriptor=fx.descriptor(),
            actor=OPERATOR,
            authority="operator",
            reason="withdraw",
            idempotency_key="disable-inert",
            correlation_id=CORRELATION,
        )
        await harness.service.roll_back(
            fx.INERT.component_id,
            descriptor=fx.descriptor(),
            actor=OPERATOR,
            authority="operator",
            reason="restore",
            idempotency_key="rollback-inert",
            correlation_id=CORRELATION,
        )
        result = await harness.service.replay()
        assert result.projection_matches
        assert result.hash_chain_verified
        assert result.failures == ()
        assert result.replayed_revisions == 6


class TestTheFixtureIsNeverAShippedDefault:
    @pytest.mark.asyncio
    async def test_a_fresh_store_has_no_active_component_on_any_surface(self) -> None:
        """The default state of the system is that nothing learned is active."""
        service = LearnedEvidenceService(InMemoryLearnedEvidenceRepository())
        for surface in (fx.surface(), "acceptance.prediction", "context.reranking"):
            assert await service.active_component_for(surface) is None

    @pytest.mark.asyncio
    async def test_activation_needs_an_explicitly_named_actor(self) -> None:
        service = LearnedEvidenceService(InMemoryLearnedEvidenceRepository())
        with pytest.raises(LearnedRepositoryError) as raised:
            await service.activate(
                descriptor=fx.descriptor(),
                component_revision=1,
                promotion_assessment=fx.promotion_assessment(),
                approval=fx.approval(
                    revision=1, promotion_hash=fx.promotion_assessment().content_hash
                ),
                lineage=fx.lineage(),
                actor=OPERATOR,
                authority="operator",
                reason="activate on a default service",
                idempotency_key="default-activate",
                correlation_id=CORRELATION,
            )
        assert raised.value.conflict is LearnedRepositoryConflict.EVIDENCE_MISMATCH
