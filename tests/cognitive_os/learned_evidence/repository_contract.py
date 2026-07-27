"""One contract suite for every learned evidence repository.

The in-memory reference and the PostgreSQL implementation must be indistinguishable
through the port, so the suite lives here and each implementation binds to it. A rule
that only one of them enforces is not a rule, and the one that would quietly disagree is
always the one that writes to disk.

Bind an implementation by subclassing `LearnedRepositoryContract` and providing
`make_repository()` and `corrupt_projection()`.
"""

from __future__ import annotations

import asyncio
from typing import Protocol
from uuid import uuid4

import pytest

from cognitive_os.application.ports.learned_evidence import LearnedEvidenceRepositoryPort
from cognitive_os.domain.learned import LearnedComponentState
from cognitive_os.domain.learned_evidence import (
    LearnedActivationAction,
    LearnedActivationApproval,
    LearnedActivationReceipt,
    LearnedComponentRevisionRecord,
    LearnedEvidenceKind,
    LearnedRepositoryConflict,
    LearnedRepositoryError,
    ObservationStatus,
)

from . import fixtures as fx


class RepositoryFactory(Protocol):
    async def __call__(self) -> LearnedEvidenceRepositoryPort: ...


def revision(
    *,
    number: int,
    state_after: LearnedComponentState,
    state_before: LearnedComponentState | None = None,
    key: str | None = None,
    **overrides: object,
) -> LearnedComponentRevisionRecord:
    fields: dict[str, object] = {
        "component_id": fx.INERT.component_id,
        "revision": number,
        "previous_revision": number - 1 if number > 1 else None,
        "surface": fx.surface(),
        "state_before": state_before,
        "state_after": state_after,
        "descriptor_hash": fx.descriptor().content_hash,
        "actor": "release-operator",
        "authority": "operator",
        "reason": f"move to {state_after.value}",
        "idempotency_key": key or f"key-{number}-{state_after.value}",
        "recorded_at": fx.FIXTURE_NOW,
    }
    fields.update(overrides)
    return LearnedComponentRevisionRecord(**fields)  # type: ignore[arg-type]


async def drive_to_verified(repository: LearnedEvidenceRepositoryPort) -> None:
    """Register, shadow and verify the fixture: revisions 1 to 3."""
    await repository.register_component(
        revision=revision(number=1, state_after=LearnedComponentState.REGISTERED),
        descriptor_version=fx.descriptor().version,
    )
    for number, before, after in (
        (2, LearnedComponentState.REGISTERED, LearnedComponentState.SHADOW),
        (3, LearnedComponentState.SHADOW, LearnedComponentState.VERIFIED),
    ):
        await repository.advance_component(
            revision=revision(number=number, state_before=before, state_after=after),
            expected_revision=number - 1,
        )


def activation_step(
    *, number: int, key: str = "activate-1"
) -> tuple[LearnedComponentRevisionRecord, LearnedActivationReceipt, LearnedActivationApproval]:
    """A well-formed activation: its revision, its receipt and the approval they name.

    The approval is built here rather than invented per-test because a receipt whose
    `approval_id` points at nothing is exactly the corruption health is meant to catch —
    a fixture that produced it by default would make every health run report a defect
    that only the fixture had.
    """
    assessment = fx.promotion_assessment()
    approval = fx.approval(
        revision=number - 1,
        promotion_hash=assessment.content_hash,
        lineage_id=fx.lineage().lineage_id,
    )
    step = revision(
        number=number,
        state_before=LearnedComponentState.VERIFIED,
        state_after=LearnedComponentState.ACTIVE,
        key=key,
        artifact_lineage_id=fx.lineage().lineage_id,
        promotion_assessment_hash=assessment.content_hash,
        activation_approval_hash=approval.content_hash,
    )
    receipt = LearnedActivationReceipt(
        receipt_id=uuid4(),
        action=LearnedActivationAction.ACTIVATION,
        component_id=fx.INERT.component_id,
        component_revision=number,
        surface=fx.surface(),
        artifact_lineage_id=fx.lineage().lineage_id,
        promotion_assessment_hash=assessment.content_hash,
        approval_id=approval.approval_id,
        approval_hash=approval.content_hash,
        actor="release-operator",
        authority="operator",
        reason="contract-suite activation",
        idempotency_key=key,
        recorded_at=fx.FIXTURE_NOW,
    )
    return step, receipt, approval


async def drive_to_activated(repository: LearnedEvidenceRepositoryPort) -> None:
    """Take the verified fixture to `ACTIVE` at revision 4, with its receipt."""
    step, receipt, approval = activation_step(number=4)
    await repository.record_approval(approval)
    await repository.record_activation_step(revision=step, expected_revision=3, receipt=receipt)


async def attempt_stale_activation(repository: LearnedEvidenceRepositoryPort) -> None:
    """A well-formed activation whose expected revision is already stale.

    Both writes must be refused together: a receipt without its state change would claim
    an activation that never happened.
    """
    step, receipt, approval = activation_step(number=4, key="doomed-activation")
    await repository.record_approval(approval)
    await repository.record_activation_step(revision=step, expected_revision=1, receipt=receipt)


class LearnedRepositoryContract:
    """Behaviour every learned evidence repository must exhibit identically."""

    async def make_repository(self) -> LearnedEvidenceRepositoryPort:
        raise NotImplementedError

    async def corrupt_projection(
        self, repository: LearnedEvidenceRepositoryPort, component_id: str
    ) -> None:
        """Move the projection away from history without appending a revision.

        Only a bug or a manual write can produce this state, which is precisely why
        replay has to detect it rather than assume it away.
        """
        raise NotImplementedError

    async def registered(self) -> LearnedEvidenceRepositoryPort:
        repository = await self.make_repository()
        await repository.register_component(
            revision=revision(number=1, state_after=LearnedComponentState.REGISTERED),
            descriptor_version=fx.descriptor().version,
        )
        return repository

    async def verified(self) -> LearnedEvidenceRepositoryPort:
        repository = await self.make_repository()
        await drive_to_verified(repository)
        return repository

    # ---------------------------------------------------------------- registration

    @pytest.mark.asyncio
    async def test_registration_creates_history_and_a_projection(self) -> None:
        repository = await self.registered()
        row = await repository.get_component(fx.INERT.component_id)
        assert row is not None
        assert row.current_revision == 1
        assert row.current_state is LearnedComponentState.REGISTERED
        history = await repository.component_history(fx.INERT.component_id)
        assert [item.revision for item in history] == [1]

    @pytest.mark.asyncio
    async def test_an_identical_retry_returns_the_original_record(self) -> None:
        repository = await self.registered()
        again = await repository.register_component(
            revision=revision(number=1, state_after=LearnedComponentState.REGISTERED),
            descriptor_version=fx.descriptor().version,
        )
        assert again.revision == 1
        history = await repository.component_history(fx.INERT.component_id)
        assert len(history) == 1, "a retry must not append a second revision"

    @pytest.mark.asyncio
    async def test_reusing_a_key_for_different_content_is_refused(self) -> None:
        repository = await self.registered()
        with pytest.raises(LearnedRepositoryError) as raised:
            await repository.register_component(
                revision=revision(
                    number=1,
                    state_after=LearnedComponentState.REGISTERED,
                    reason="a different reason entirely",
                ),
                descriptor_version=fx.descriptor().version,
            )
        assert raised.value.conflict is LearnedRepositoryConflict.IDEMPOTENCY_KEY_REUSED

    # ------------------------------------------------------------------- lifecycle

    @pytest.mark.asyncio
    async def test_a_legal_step_advances_the_projection(self) -> None:
        repository = await self.registered()
        await repository.advance_component(
            revision=revision(
                number=2,
                state_before=LearnedComponentState.REGISTERED,
                state_after=LearnedComponentState.SHADOW,
            ),
            expected_revision=1,
        )
        row = await repository.get_component(fx.INERT.component_id)
        assert row is not None and row.current_state is LearnedComponentState.SHADOW

    @pytest.mark.asyncio
    async def test_an_illegal_step_is_refused(self) -> None:
        repository = await self.registered()
        with pytest.raises(LearnedRepositoryError) as raised:
            await repository.advance_component(
                revision=revision(
                    number=2,
                    state_before=LearnedComponentState.REGISTERED,
                    state_after=LearnedComponentState.VERIFIED,
                ),
                expected_revision=1,
            )
        assert raised.value.conflict is LearnedRepositoryConflict.ILLEGAL_TRANSITION

    @pytest.mark.asyncio
    async def test_a_stale_expected_revision_is_refused(self) -> None:
        repository = await self.verified()
        with pytest.raises(LearnedRepositoryError) as raised:
            await repository.advance_component(
                revision=revision(
                    number=2,
                    state_before=LearnedComponentState.REGISTERED,
                    state_after=LearnedComponentState.SHADOW,
                    key="stale-attempt",
                ),
                expected_revision=1,
            )
        assert raised.value.conflict is LearnedRepositoryConflict.STALE_REVISION

    @pytest.mark.asyncio
    @pytest.mark.concurrency
    async def test_two_concurrent_steps_from_one_state_leave_exactly_one_winner(self) -> None:
        """Compare-and-swap, not last-write-wins.

        Both callers read revision 1 and both believe they may advance from it. Exactly
        one may; the other must be told its view is stale rather than silently
        overwriting a step it never saw.
        """
        repository = await self.registered()
        attempts = [
            repository.advance_component(
                revision=revision(
                    number=2,
                    state_before=LearnedComponentState.REGISTERED,
                    state_after=LearnedComponentState.SHADOW,
                    key=f"race-{index}",
                    reason=f"racing writer {index}",
                ),
                expected_revision=1,
            )
            for index in range(2)
        ]
        results = await asyncio.gather(*attempts, return_exceptions=True)
        failures = [item for item in results if isinstance(item, LearnedRepositoryError)]
        assert len(failures) == 1
        assert failures[0].conflict is LearnedRepositoryConflict.STALE_REVISION
        history = await repository.component_history(fx.INERT.component_id)
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_disabled_cannot_return_to_active_without_a_rollback_target(self) -> None:
        """The most dangerous transition stays unreachable through the ordinary path."""
        repository = await self.activated()
        await repository.advance_component(
            revision=revision(
                number=5,
                state_before=LearnedComponentState.ACTIVE,
                state_after=LearnedComponentState.DISABLED,
            ),
            expected_revision=4,
        )
        with pytest.raises(LearnedRepositoryError) as raised:
            await repository.advance_component(
                revision=revision(
                    number=6,
                    state_before=LearnedComponentState.DISABLED,
                    state_after=LearnedComponentState.ACTIVE,
                    promotion_assessment_hash=fx.promotion_assessment().content_hash,
                    activation_approval_hash=fx.ARTIFACT_HASH,
                ),
                expected_revision=5,
            )
        assert raised.value.conflict is LearnedRepositoryConflict.ILLEGAL_TRANSITION

    @pytest.mark.asyncio
    async def test_disabled_returns_to_active_when_a_rollback_target_is_named(self) -> None:
        repository = await self.activated()
        await repository.advance_component(
            revision=revision(
                number=5,
                state_before=LearnedComponentState.ACTIVE,
                state_after=LearnedComponentState.DISABLED,
            ),
            expected_revision=4,
        )
        restored = await repository.advance_component(
            revision=revision(
                number=6,
                state_before=LearnedComponentState.DISABLED,
                state_after=LearnedComponentState.ACTIVE,
                promotion_assessment_hash=fx.promotion_assessment().content_hash,
                activation_approval_hash=fx.ARTIFACT_HASH,
                rollback_target_revision=4,
            ),
            expected_revision=5,
        )
        assert restored.state_after is LearnedComponentState.ACTIVE

    # ------------------------------------------------------------------ activation

    async def activated(self) -> LearnedEvidenceRepositoryPort:
        """Drive the fixture to `ACTIVE` at revision 4 with a receipt."""
        repository = await self.verified()
        await drive_to_activated(repository)
        return repository

    @pytest.mark.asyncio
    async def test_activation_records_the_step_and_the_receipt_together(self) -> None:
        repository = await self.activated()
        row = await repository.get_component(fx.INERT.component_id)
        assert row is not None and row.current_state is LearnedComponentState.ACTIVE
        receipt = await repository.latest_activation_for(fx.surface())
        assert receipt is not None
        assert receipt.action is LearnedActivationAction.ACTIVATION
        assert receipt.component_revision == row.current_revision

    @pytest.mark.asyncio
    async def test_a_refused_activation_step_leaves_no_receipt(self) -> None:
        """Atomicity, stated as the property that matters: no orphan receipt."""
        repository = await self.verified()
        with pytest.raises(LearnedRepositoryError):
            await attempt_stale_activation(repository)
        assert await repository.latest_activation_for(fx.surface()) is None
        history = await repository.component_history(fx.INERT.component_id)
        assert len(history) == 3, "the refused step must not have appended a revision"

    @pytest.mark.asyncio
    async def test_one_surface_holds_at_most_one_active_component(self) -> None:
        repository = await self.activated()
        other = fx.UNPROMOTABLE.component_id
        await repository.register_component(
            revision=revision(
                number=1,
                state_after=LearnedComponentState.REGISTERED,
                component_id=other,
                key="second-component",
            ),
            descriptor_version="1",
        )
        for number, before, after in (
            (2, LearnedComponentState.REGISTERED, LearnedComponentState.SHADOW),
            (3, LearnedComponentState.SHADOW, LearnedComponentState.VERIFIED),
        ):
            await repository.advance_component(
                revision=revision(
                    number=number,
                    state_before=before,
                    state_after=after,
                    component_id=other,
                    key=f"second-{number}",
                ),
                expected_revision=number - 1,
            )
        with pytest.raises(LearnedRepositoryError) as raised:
            await repository.advance_component(
                revision=revision(
                    number=4,
                    state_before=LearnedComponentState.VERIFIED,
                    state_after=LearnedComponentState.ACTIVE,
                    component_id=other,
                    key="second-activate",
                    promotion_assessment_hash=fx.promotion_assessment().content_hash,
                    activation_approval_hash=fx.ARTIFACT_HASH,
                ),
                expected_revision=3,
            )
        assert raised.value.conflict is LearnedRepositoryConflict.SURFACE_ALREADY_ACTIVE

    # ------------------------------------------------------------- immutable ledgers

    @pytest.mark.asyncio
    async def test_re_appending_an_identical_evidence_record_is_a_no_op(self) -> None:
        repository = await self.registered()
        record = fx.evidence(LearnedEvidenceKind.SHADOW_RESULT, fx.ARTIFACT_HASH)
        await repository.record_evidence(record)
        await repository.record_evidence(record)
        stored = await repository.list_evidence(component_id=fx.INERT.component_id)
        assert len(stored) == 1

    @pytest.mark.asyncio
    async def test_an_immutable_record_cannot_be_replaced_with_different_content(self) -> None:
        repository = await self.registered()
        record = fx.evidence(LearnedEvidenceKind.SHADOW_RESULT, fx.ARTIFACT_HASH)
        await repository.record_evidence(record)
        with pytest.raises(LearnedRepositoryError):
            await repository.record_evidence(
                fx.evidence(
                    LearnedEvidenceKind.SHADOW_RESULT,
                    fx.ARTIFACT_HASH,
                    evidence_id=record.evidence_id,
                    recorded_by="someone-else",
                )
            )

    @pytest.mark.asyncio
    async def test_an_observation_key_replay_returns_the_original(self) -> None:
        repository = await self.registered()
        record = fx.observation()
        first = await repository.record_observation(record)
        second = await repository.record_observation(record)
        assert first.observation_id == second.observation_id
        stored = await repository.list_observations(surface=fx.surface())
        assert len(stored) == 1

    @pytest.mark.asyncio
    async def test_an_observation_key_reused_for_different_content_is_refused(self) -> None:
        repository = await self.registered()
        await repository.record_observation(fx.observation())
        with pytest.raises(LearnedRepositoryError) as raised:
            await repository.record_observation(
                fx.observation(decision_reason="a different decision entirely")
            )
        assert raised.value.conflict is LearnedRepositoryConflict.IDEMPOTENCY_KEY_REUSED

    @pytest.mark.asyncio
    async def test_quarantined_observations_are_listable_by_status(self) -> None:
        repository = await self.registered()
        await repository.record_observation(
            fx.observation(
                status=ObservationStatus.QUARANTINED,
                evaluation_eligible=False,
                decision_reason="attribution could not be established",
            )
        )
        quarantined = await repository.list_observations(status=ObservationStatus.QUARANTINED)
        accepted = await repository.list_observations(status=ObservationStatus.ACCEPTED)
        assert len(quarantined) == 1 and not accepted

    # ---------------------------------------------------------------------- replay

    @pytest.mark.asyncio
    async def test_replay_agrees_with_the_projection(self) -> None:
        repository = await self.activated()
        result = await repository.replay()
        assert result.projection_matches
        assert result.hash_chain_verified
        assert result.failures == ()
        assert result.replayed_revisions == 4

    @pytest.mark.asyncio
    async def test_replay_fails_closed_when_the_projection_disagrees(self) -> None:
        """If replay and the projection disagree, the projection is wrong by definition."""
        repository = await self.verified()
        await self.corrupt_projection(repository, fx.INERT.component_id)
        result = await repository.replay()
        assert not result.projection_matches
        assert result.failures, "a replay that disagreed must say what disagreed"

    @pytest.mark.asyncio
    async def test_replay_mutates_nothing(self) -> None:
        repository = await self.activated()
        before = await repository.component_history(fx.INERT.component_id)
        await repository.replay()
        after = await repository.component_history(fx.INERT.component_id)
        assert [item.content_hash for item in before] == [item.content_hash for item in after]

    # --------------------------------------------------------------------- paging

    @pytest.mark.asyncio
    async def test_listings_are_bounded(self) -> None:
        repository = await self.registered()
        rows = await repository.list_components(limit=10_000)
        assert len(rows) <= 500
