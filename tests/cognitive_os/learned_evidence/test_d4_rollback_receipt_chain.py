"""S21D4-075: receipt-selected rollback, on the isolated lifecycle fixture.

The one item in E07 the backlog calls **unconditional**. It runs whether or not D4 activates,
and D4 activated nothing — S21D4-039 selected no candidate — so it runs here, against the
released inert component, with no database and no store.

Three of the item's properties are already proved by `test_inert_lifecycle.py`: a previously
approval-bound state restores, a `rollback_permitted=false` disable is structurally
non-restorable, and an unauthorised caller cannot roll back. This module adds the two the
acceptance names that nothing was checking, and one that follows from them.

*It survives restart.* A restored `ACTIVE` projection that a process boundary forgets is not a
restoration. The harness throws its service away and builds a new one over the same durable
state, which is the moment a service holding authoritative state of its own would be caught.

*It deletes no evidence.* Rollback is an append: every approval, evidence record, revision and
receipt that existed before the disable still resolves afterwards, and the receipt chain grows
rather than being rewritten. A rollback that tidied up after itself would destroy the record of
the activation it was undoing.

*A refusal survives restart too.* The failed-canary refusal is read off the durable chain, so a
restart must not turn it into a permission. A refusal a restart forgets is not a refusal.
"""

from __future__ import annotations

import inspect

import pytest

from cognitive_os.domain.learned import LearnedComponentState
from cognitive_os.domain.learned_evidence import (
    LearnedActivationAction,
    LearnedRepositoryError,
)

from . import fixtures as fx
from .test_inert_lifecycle import CORRELATION, OPERATOR, LifecycleHarness, ready


async def _activated() -> tuple[LifecycleHarness, object, object]:
    """The fixture at the one state rollback is about: activated, on its surface."""
    harness = await ready()
    approval = await harness.approve()
    activation = await harness.activate(approval)
    return harness, approval, activation


async def _disable(harness: LifecycleHarness, *, permitted: bool, key: str) -> object:
    return await harness.service.disable(
        fx.INERT.component_id,
        descriptor=fx.descriptor(),
        actor=OPERATOR,
        authority="operator",
        reason="withdraw the fixture" if permitted else "the scratch canary failed its gate",
        idempotency_key=key,
        correlation_id=CORRELATION,
        rollback_permitted=permitted,
    )


async def _roll_back(harness: LifecycleHarness, *, key: str) -> object:
    return await harness.service.roll_back(
        fx.INERT.component_id,
        descriptor=fx.descriptor(),
        actor=OPERATOR,
        authority="operator",
        reason="restore the prior activation",
        idempotency_key=key,
        correlation_id=CORRELATION,
    )


@pytest.mark.asyncio
async def test_the_restored_activation_survives_a_restart() -> None:
    harness, approval, activation = await _activated()
    await _disable(harness, permitted=True, key="disable-before-restart")
    rolled_back = await _roll_back(harness, key="rollback-before-restart")

    before = await harness.service.get_component(fx.INERT.component_id)
    assert before is not None and before.current_state is LearnedComponentState.ACTIVE

    harness.restart()

    after = await harness.service.get_component(fx.INERT.component_id)
    assert after is not None
    assert after.current_state is LearnedComponentState.ACTIVE
    assert after.current_revision == before.current_revision
    assert after.content_hash == before.content_hash
    holder = await harness.service.active_component_for(fx.surface())
    assert holder is not None and holder.component_id == fx.INERT.component_id

    # The chain the restart reads is the same chain: the rollback still names the activation it
    # restored, and that activation still names the approval that authorised it.
    stored = await harness.repository.get_activation_receipt(rolled_back.receipt_id)
    assert stored is not None
    assert stored.rollback_target_receipt_id == activation.receipt_id
    assert stored.approval_id == approval.approval_id


@pytest.mark.asyncio
async def test_the_rollback_deletes_no_evidence() -> None:
    """An append, not a repair. A rollback that tidied up would erase what it undid.

    Written as "every identity that existed still resolves" rather than as a row count, and
    through the repository's public reads only: a count taken off an internal list would be a
    test of this fixture's data structures rather than of the property the item names.
    """
    harness, approval, activation = await _activated()
    evidence_before = {
        item.evidence_id
        for item in await harness.repository.list_evidence(component_id=fx.INERT.component_id)
    }
    history_before = await harness.repository.component_history(fx.INERT.component_id)
    assert evidence_before and history_before, "counting nothing proves nothing"

    disabled = await _disable(harness, permitted=True, key="disable-no-deletion")
    rolled_back = await _roll_back(harness, key="rollback-no-deletion")

    # Three distinct receipts, each still resolving to the bytes it was issued with.
    assert len({activation.receipt_id, disabled.receipt_id, rolled_back.receipt_id}) == 3
    for receipt in (activation, disabled, rolled_back):
        stored = await harness.repository.get_activation_receipt(receipt.receipt_id)
        assert stored is not None and stored.content_hash == receipt.content_hash

    evidence_after = {
        item.evidence_id
        for item in await harness.repository.list_evidence(component_id=fx.INERT.component_id)
    }
    assert evidence_before <= evidence_after

    history_after = await harness.repository.component_history(fx.INERT.component_id)
    assert len(history_after) > len(history_before), "the rollback appended no revision"
    assert history_after[: len(history_before)] == history_before, "an earlier revision moved"

    # The authority is the one that already existed; a rollback invents none.
    assert (await harness.repository.get_approval(approval.approval_id)) is not None
    assert rolled_back.approval_id == approval.approval_id


@pytest.mark.asyncio
async def test_a_refused_rollback_is_still_refused_after_a_restart() -> None:
    """The refusal lives on the durable chain, so a process boundary must not soften it."""
    harness, _, _ = await _activated()
    disabled = await _disable(harness, permitted=False, key="disable-failed-canary")
    assert disabled.rollback_permitted is False

    harness.restart()

    with pytest.raises(LearnedRepositoryError, match="rollback_permitted=false"):
        await _roll_back(harness, key="rollback-after-restart")

    row = await harness.service.get_component(fx.INERT.component_id)
    assert row is not None and row.current_state is LearnedComponentState.DISABLED
    assert await harness.service.active_component_for(fx.surface()) is None


@pytest.mark.asyncio
async def test_the_target_is_read_from_the_chain_and_cannot_be_chosen() -> None:
    """Structural, not procedural: there is no parameter a caller could pass a target in."""
    parameters = set(inspect.signature(type(LifecycleHarness().service).roll_back).parameters)

    assert not parameters & {"target", "target_receipt_id", "revision", "to_revision"}

    harness, _, activation = await _activated()
    await _disable(harness, permitted=True, key="disable-chain-target")
    rolled_back = await _roll_back(harness, key="rollback-chain-target")

    assert rolled_back.action is LearnedActivationAction.ROLLBACK
    assert rolled_back.rollback_target_receipt_id == activation.receipt_id
