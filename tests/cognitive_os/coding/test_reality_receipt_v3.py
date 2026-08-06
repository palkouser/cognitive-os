from __future__ import annotations

from uuid import UUID

import pytest

from cognitive_os.application.services.reality_campaign import (
    CampaignLedgerError,
    RealityCampaignLedger,
    ReceiptAction,
)
from cognitive_os.domain.coding import CodingOutcomeStatus
from cognitive_os.domain.enums import StreamType
from cognitive_os.domain.reality import (
    RealityCampaignReceiptManifestV3,
    RealityCandidateSource,
    RealityCandidateStrategy,
    RealityReceiptTaskV3,
    RealityRunIdentity,
    RealityRunKind,
)
from cognitive_os.events.coding_event_service import CodingEventService
from cognitive_os.events.coding_events import CodingOutcomeRecorded, RealityCampaignSequenceRecorded
from cognitive_os.events.memory_store import MemoryEventStore

NOW = "2026-08-04T09:00:00Z"
CAMPAIGN = UUID(int=700)
TASK = UUID(int=701)
CANDIDATES = tuple(UUID(int=710 + index) for index in range(4))
STRATEGIES = (
    RealityCandidateStrategy.RECIPE_ALPHA,
    RealityCandidateStrategy.RECIPE_BETA,
    RealityCandidateStrategy.RECIPE_GAMMA,
    RealityCandidateStrategy.RECIPE_DELTA,
)


def _manifest(**changes: object) -> RealityCampaignReceiptManifestV3:
    verifier = "1" * 64
    planned = tuple(
        RealityRunIdentity(
            task_id=TASK,
            task_manifest_hash="2" * 64,
            run_kind=RealityRunKind.CANDIDATE,
            candidate_id=candidate,
            strategy=strategy,
            source=RealityCandidateSource.CURATED,
            generator_profile_id="d3-fixture",
            verifier_profile_hash=verifier,
            campaign_version=3,
        )
        for candidate, strategy in zip(CANDIDATES, STRATEGIES, strict=True)
    )
    fields: dict[str, object] = {
        "campaign_id": CAMPAIGN,
        "campaign_version": 3,
        "planned_runs": planned,
        "verifier_profile_hash": verifier,
        "created_at": NOW,
        "partition": "canary",
        "mode": "stop_on_first_accepted",
        "selection_manifest_hash": "3" * 64,
        "feature_schema_hash": "4" * 64,
        "feature_seal_root_hash": "5" * 64,
        "receipt_tasks": (
            RealityReceiptTaskV3(
                task_id=TASK,
                task_manifest_hash="2" * 64,
                bundle_id=UUID(int=702),
                bundle_hash="6" * 64,
                feature_seal_hash="7" * 64,
                candidate_order=CANDIDATES,
                selected_member_hashes=tuple(f"{800 + index:064x}" for index in range(4)),
            ),
        ),
    }
    fields.update(changes)
    return RealityCampaignReceiptManifestV3(**fields)


async def _append_sequence(
    store: MemoryEventStore,
    manifest: RealityCampaignReceiptManifestV3,
    *,
    baseline_order: tuple[UUID, ...] = CANDIDATES,
) -> None:
    await CodingEventService(store).append(
        CAMPAIGN,
        RealityCampaignSequenceRecorded(
            campaign_id=CAMPAIGN,
            task_id=TASK,
            partition="canary",
            mode="stop_on_first_accepted",
            campaign_manifest_hash=manifest.content_hash,
            baseline_order=baseline_order,
            resolved_order=baseline_order,
            attempted_order=baseline_order[:1],
            intentionally_unattempted=baseline_order[1:],
            accepted_candidate_id=baseline_order[0],
            accepted_position=0,
            accepted_event_id=UUID(int=799),
            verifier_evidence_hash="8" * 64,
            stop_reason="verifier_accepted",
            occurred_at=NOW,
        ),
        correlation_id=CAMPAIGN,
        stream_type=StreamType.SYSTEM,
    )


async def _append_outcome(
    store: MemoryEventStore, manifest: RealityCampaignReceiptManifestV3
) -> UUID:
    task_run_id = UUID(int=780)
    identity = manifest.planned_runs[0]
    await CodingEventService(store).append(
        task_run_id,
        CodingOutcomeRecorded(
            task_run_id=task_run_id,
            run_kind=RealityRunKind.CANDIDATE,
            task_id=TASK,
            task_manifest_hash="2" * 64,
            candidate_id=CANDIDATES[0],
            candidate_strategy=STRATEGIES[0],
            outcome_hash="9" * 64,
            outcome_artifact_id=UUID(int=781),
            outcome_artifact_hash="a" * 64,
            hidden_evidence_artifact_id=UUID(int=782),
            hidden_evidence_hash="b" * 64,
            final_status=CodingOutcomeStatus.ACCEPTED,
            hidden_verification_passed=True,
            run_identity_key=identity.key,
            occurred_at=NOW,
        ),
        correlation_id=CAMPAIGN,
        stream_type=StreamType.TASK_RUN,
    )
    return task_run_id


@pytest.mark.asyncio
async def test_restart_after_first_accept_keeps_intentionally_unattempted_candidates_out() -> None:
    store = MemoryEventStore()
    manifest = _manifest()
    await _append_sequence(store, manifest)
    task_run_id = await _append_outcome(store, manifest)
    ledger = RealityCampaignLedger(store)

    resumed = await ledger.plan_resume_with_receipts(
        manifest, task_run_ids=(task_run_id,), campaign_id=CAMPAIGN
    )
    repeated = await ledger.plan_resume_with_receipts(
        manifest, task_run_ids=(task_run_id,), campaign_id=CAMPAIGN
    )

    assert resumed.tasks[0].action is ReceiptAction.SEALED_AND_CONSISTENT
    assert resumed.effective_remainder == ()
    assert resumed.plan.remaining == ()
    assert resumed.candidates_left_alone == CANDIDATES[1:]
    assert repeated == resumed


@pytest.mark.asyncio
async def test_only_the_exact_missing_attempted_outcome_is_replayed() -> None:
    store = MemoryEventStore()
    manifest = _manifest()
    await _append_sequence(store, manifest)

    resumed = await RealityCampaignLedger(store).plan_resume_with_receipts(
        manifest, task_run_ids=(), campaign_id=CAMPAIGN
    )

    assert resumed.tasks[0].action is ReceiptAction.REPLAY_MISSING_OUTCOME
    assert tuple(item.candidate_id for item in resumed.effective_remainder) == CANDIDATES[:1]
    assert not (set(CANDIDATES[1:]) & {item.candidate_id for item in resumed.plan.remaining})


@pytest.mark.asyncio
async def test_outcome_without_receipt_reruns_the_exact_task_whole() -> None:
    store = MemoryEventStore()
    manifest = _manifest()
    task_run_id = await _append_outcome(store, manifest)

    resumed = await RealityCampaignLedger(store).plan_resume_with_receipts(
        manifest, task_run_ids=(task_run_id,), campaign_id=CAMPAIGN
    )

    assert resumed.tasks[0].action is ReceiptAction.RERUN_UNSEALED_TASK
    assert tuple(item.candidate_id for item in resumed.effective_remainder) == CANDIDATES


@pytest.mark.asyncio
async def test_stale_manifest_and_changed_order_are_refused() -> None:
    store = MemoryEventStore()
    manifest = _manifest()
    await _append_sequence(store, manifest)
    tampered = _manifest(feature_seal_root_hash="c" * 64)

    with pytest.raises(CampaignLedgerError, match="stale or tampered"):
        await RealityCampaignLedger(store).plan_resume_with_receipts(
            tampered, task_run_ids=(), campaign_id=CAMPAIGN
        )

    changed_store = MemoryEventStore()
    await _append_sequence(changed_store, manifest, baseline_order=tuple(reversed(CANDIDATES)))
    with pytest.raises(CampaignLedgerError, match="candidate order changed"):
        await RealityCampaignLedger(changed_store).plan_resume_with_receipts(
            manifest, task_run_ids=(), campaign_id=CAMPAIGN
        )


def test_receipt_manifest_refuses_changed_selected_order() -> None:
    current = _manifest()
    receipt = current.receipt_tasks[0].model_copy(
        update={"candidate_order": tuple(reversed(CANDIDATES)), "content_hash": ""}
    )

    with pytest.raises(ValueError, match="planned member order"):
        _manifest(receipt_tasks=(receipt,))
