"""Campaign resume and the outcome denominator, §S21C3-014.

Two failure modes this exists to prevent, both of which inflate a number that Gate C3 reads:

*Restart duplicates the denominator.* A campaign interrupted after 140 of 150 runs and then
restarted from zero produces 290 events for 150 executions. The count would clear the
200-outcome threshold on the strength of having crashed once. So the denominator is not "how
many times we recorded something"; it is the number of distinct `(event, task run, outcome
hash)` identities, and every re-appearance is reported as an exclusion with a reason rather
than silently dropped — an exclusion nobody can see is indistinguishable from a bug.

*Resume calls a provider again for work already done.* Completion is reconstructed from the
Event Store, not from campaign memory, because the campaign's memory is the thing the crash
destroyed. `CodingOutcomeRecorded.run_identity_key` is the join.

The ledger reads. It executes nothing, calls no provider and writes no event; deciding what
still needs running is a different job from running it, and keeping them apart is what lets
the resume decision be tested without a sandbox.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID

from cognitive_os.application.ports.event_store import EventStorePort
from cognitive_os.domain.reality import (
    RealityCampaignManifest,
    RealityOutcomeCountReason,
    RealityOutcomeReference,
    RealityRunIdentity,
)
from cognitive_os.events.coding_events import (
    CodingOutcomeRecorded,
    RealityCampaignSequenceRecorded,
)


class CampaignLedgerError(RuntimeError):
    """The recorded evidence and the campaign plan cannot both be right."""


@dataclass(frozen=True, slots=True)
class ExcludedOutcome:
    """One recorded execution that did not add to the denominator, and why."""

    source_event_id: UUID
    task_run_id: UUID
    outcome_hash: str
    reason: RealityOutcomeCountReason


@dataclass(frozen=True, slots=True)
class OutcomeCount:
    """The denominator, plus everything that was left out of it."""

    counted: tuple[RealityOutcomeReference, ...] = ()
    excluded: tuple[ExcludedOutcome, ...] = ()

    @property
    def unique(self) -> int:
        return len(self.counted)

    @property
    def duplicates_excluded(self) -> int:
        return len(self.excluded)

    @property
    def passed(self) -> int:
        return sum(1 for item in self.counted if item.hidden_verification_passed)

    @property
    def failed(self) -> int:
        """Failures are outcomes. A campaign that reported only successes would be a report
        about the campaign rather than about the candidates."""
        return self.unique - self.passed


@dataclass(frozen=True, slots=True)
class ResumePlan:
    """What is left to run, what is already done, and what does not belong to this revision."""

    remaining: tuple[RealityRunIdentity, ...] = ()
    completed: tuple[RealityRunIdentity, ...] = ()
    unplanned_keys: frozenset[str] = field(default_factory=frozenset)

    @property
    def is_complete(self) -> bool:
        return not self.remaining


class ReceiptAction(StrEnum):
    """What a resume must do about one task, once the sequence receipts have been read.

    S21D2-054. Outcomes and plans between them cannot express "deliberately unattempted", so a
    resume that reads only those two re-runs work the campaign decided not to do. These are the
    four answers the receipt chain can give, and each one means something different for cost
    and for correctness.
    """

    #: No receipt for this task. The plan stands as written.
    RESUME_AS_PLANNED = "resume_as_planned"
    #: A receipt that agrees with the outcomes. Nothing to run, including the unattempted.
    SEALED_AND_CONSISTENT = "sealed_and_consistent"
    #: Outcomes exist but no receipt sealed them: the sequence was interrupted before it ended.
    #: The task is re-run from the start, because a half-sequence has no defensible prefix.
    RERUN_UNSEALED_TASK = "rerun_unsealed_task"
    #: The receipt says a candidate was attempted and no outcome carries it. The append was
    #: lost between the sandbox and the event store, so that candidate alone is replayed.
    REPLAY_MISSING_OUTCOME = "replay_missing_outcome"
    #: An outcome exists for a candidate the receipt calls intentionally unattempted. The two
    #: durable records disagree; that is a new campaign revision, not a resume.
    REFUSE_CONTRADICTED_RECEIPT = "refuse_contradicted_receipt"


@dataclass(frozen=True, slots=True)
class TaskReceiptState:
    """One task's reconciliation between its sequence receipt and its recorded outcomes."""

    task_id: UUID
    action: ReceiptAction
    attempted: tuple[UUID, ...] = ()
    intentionally_unattempted: tuple[UUID, ...] = ()
    missing_outcomes: tuple[UUID, ...] = ()
    contradicted: tuple[UUID, ...] = ()
    stop_reason: str = ""


@dataclass(frozen=True, slots=True)
class ReceiptAwareResumePlan:
    """A resume plan that knows about the third state, and refuses when the records disagree."""

    plan: ResumePlan
    tasks: tuple[TaskReceiptState, ...] = ()

    @property
    def refused(self) -> tuple[TaskReceiptState, ...]:
        return tuple(
            task for task in self.tasks if task.action is ReceiptAction.REFUSE_CONTRADICTED_RECEIPT
        )

    @property
    def is_resumable(self) -> bool:
        """A campaign with a contradicted receipt is not resumable at any cost."""
        return not self.refused

    @property
    def candidates_to_replay(self) -> tuple[UUID, ...]:
        return tuple(candidate_id for task in self.tasks for candidate_id in task.missing_outcomes)

    @property
    def candidates_left_alone(self) -> tuple[UUID, ...]:
        """What the campaign decided not to do, and a resume must not undo."""
        return tuple(
            candidate_id
            for task in self.tasks
            if task.action is ReceiptAction.SEALED_AND_CONSISTENT
            for candidate_id in task.intentionally_unattempted
        )


def count_outcomes(references: Iterable[RealityOutcomeReference]) -> OutcomeCount:
    """Count distinct executions, reporting every exclusion with its cause.

    Three identities are checked independently rather than as one composite key, because they
    fail for different reasons and an operator needs to tell them apart: a repeated event ID
    means the same append was read twice, a repeated task-run ID means one run recorded two
    outcomes, and a repeated outcome hash across different runs means two executions produced
    byte-identical results — which is legitimate for a deterministic replay and is exactly why
    it must not be counted twice.
    """
    counted: list[RealityOutcomeReference] = []
    excluded: list[ExcludedOutcome] = []
    seen_events: set[UUID] = set()
    seen_runs: set[UUID] = set()
    seen_hashes: set[str] = set()
    for reference in references:
        reason: RealityOutcomeCountReason | None = None
        if reference.source_event_id in seen_events:
            reason = RealityOutcomeCountReason.DUPLICATE_EVENT_ID
        elif reference.task_run_id in seen_runs:
            reason = RealityOutcomeCountReason.DUPLICATE_TASK_RUN_ID
        elif reference.outcome_hash in seen_hashes:
            reason = RealityOutcomeCountReason.DUPLICATE_OUTCOME_HASH
        if reason is not None:
            excluded.append(
                ExcludedOutcome(
                    source_event_id=reference.source_event_id,
                    task_run_id=reference.task_run_id,
                    outcome_hash=reference.outcome_hash,
                    reason=reason,
                )
            )
            continue
        seen_events.add(reference.source_event_id)
        seen_runs.add(reference.task_run_id)
        seen_hashes.add(reference.outcome_hash)
        counted.append(reference)
    return OutcomeCount(counted=tuple(counted), excluded=tuple(excluded))


class RealityCampaignLedger:
    """Reconstructs campaign progress from recorded events. Read-only."""

    def __init__(self, event_store: EventStorePort) -> None:
        self._store = event_store

    async def recorded_runs(
        self, manifest: RealityCampaignManifest, *, task_run_ids: Iterable[UUID]
    ) -> tuple[tuple[RealityOutcomeReference, ...], frozenset[str]]:
        """Read every recorded outcome for the given task runs, and the identity keys seen.

        Task-run IDs come from the caller because the Event Store is keyed by stream and there
        is no index from campaign to stream. Passing them in keeps the ledger honest about
        what it read: it cannot claim a campaign is complete on the strength of streams it
        never opened.
        """
        references: list[RealityOutcomeReference] = []
        keys: set[str] = set()
        for task_run_id in task_run_ids:
            for stored in await self._store.read_stream(task_run_id):
                envelope = stored.envelope
                if envelope.event_type != CodingOutcomeRecorded.event_type:
                    continue
                payload = CodingOutcomeRecorded.model_validate(envelope.payload)
                if payload.run_identity_key is not None:
                    keys.add(payload.run_identity_key)
                references.append(_reference_from(payload, envelope.event_id))
        _require_consistent_with(manifest, references)
        return tuple(references), frozenset(keys)

    async def completed_by_identity(
        self, task_run_ids: Iterable[UUID]
    ) -> dict[str, RealityOutcomeReference]:
        """Recorded outcomes on the given streams, keyed by the run identity that produced them.

        `recorded_runs` needs a manifest because it verifies evidence against a plan. A
        campaign that is about to *execute* does not need that check yet — it needs to know
        which run identities already have an outcome, so it can skip them instead of paying
        for the containers again. Runs recorded without an identity key are not returned:
        they belong to no campaign, so no campaign may skip work on their account.
        """
        completed: dict[str, RealityOutcomeReference] = {}
        for task_run_id in task_run_ids:
            for stored in await self._store.read_stream(task_run_id):
                if stored.envelope.event_type != CodingOutcomeRecorded.event_type:
                    continue
                payload = CodingOutcomeRecorded.model_validate(stored.envelope.payload)
                if payload.run_identity_key is None:
                    continue
                completed[payload.run_identity_key] = _reference_from(
                    payload, stored.envelope.event_id
                )
        return completed

    async def plan_resume(
        self, manifest: RealityCampaignManifest, *, task_run_ids: Iterable[UUID]
    ) -> ResumePlan:
        """Decide what still has to run for this exact campaign revision."""
        _, keys = await self.recorded_runs(manifest, task_run_ids=task_run_ids)
        planned = {item.key: item for item in manifest.planned_runs}
        completed = tuple(planned[key] for key in planned if key in keys)
        remaining = tuple(planned[key] for key in planned if key not in keys)
        return ResumePlan(
            remaining=remaining,
            completed=completed,
            unplanned_keys=frozenset(keys - set(planned)),
        )

    async def sequence_receipts(
        self, campaign_id: UUID
    ) -> dict[UUID, RealityCampaignSequenceRecorded]:
        """The latest sealed sequence per task, read off the campaign stream.

        Latest rather than first: a task may be re-sequenced under the same campaign revision
        after an interruption, and the last seal is the one that describes what is now true.
        """
        latest: dict[UUID, RealityCampaignSequenceRecorded] = {}
        for stored in await self._store.read_stream(campaign_id):
            if stored.envelope.event_type != RealityCampaignSequenceRecorded.event_type:
                continue
            payload = RealityCampaignSequenceRecorded.model_validate(stored.envelope.payload)
            latest[payload.task_id] = payload
        return latest

    async def _recorded_candidates(
        self, task_run_ids: Iterable[UUID]
    ) -> dict[UUID, frozenset[UUID]]:
        """Every candidate that has a recorded outcome, grouped by the task it belonged to."""
        found: dict[UUID, set[UUID]] = {}
        for task_run_id in task_run_ids:
            for stored in await self._store.read_stream(task_run_id):
                if stored.envelope.event_type != CodingOutcomeRecorded.event_type:
                    continue
                payload = CodingOutcomeRecorded.model_validate(stored.envelope.payload)
                if payload.candidate_id is None:
                    continue
                found.setdefault(payload.task_id, set()).add(payload.candidate_id)
        return {task_id: frozenset(items) for task_id, items in found.items()}

    async def plan_resume_with_receipts(
        self,
        manifest: RealityCampaignManifest,
        *,
        task_run_ids: Iterable[UUID],
        campaign_id: UUID,
    ) -> ReceiptAwareResumePlan:
        """Resume against both durable records, not just the outcomes.

        `plan_resume` alone cannot tell a candidate that was never run from a candidate the
        campaign deliberately left alone, because the outcome stream has no row for either and
        the plan still lists both. Under `stop_on_first_accepted` that difference is the whole
        campaign: re-running the skipped candidates would produce a different experiment and
        report it under the same identity.
        """
        run_ids = tuple(task_run_ids)
        plan = await self.plan_resume(manifest, task_run_ids=run_ids)
        receipts = await self.sequence_receipts(campaign_id)
        # Read the candidate outcomes directly rather than through `completed_by_identity`:
        # that one is keyed by run identity and drops anything recorded without one, which
        # would make an interrupted candidate run look like a task nobody had touched.
        by_task = await self._recorded_candidates(run_ids)
        recorded_candidates = {
            candidate_id for candidates in by_task.values() for candidate_id in candidates
        }

        tasks: list[TaskReceiptState] = []
        for task_id in sorted({item.task_id for item in manifest.planned_runs}, key=str):
            receipt = receipts.get(task_id)
            observed = by_task.get(task_id, frozenset())
            if receipt is None:
                tasks.append(
                    TaskReceiptState(
                        task_id=task_id,
                        action=(
                            ReceiptAction.RERUN_UNSEALED_TASK
                            if observed
                            else ReceiptAction.RESUME_AS_PLANNED
                        ),
                    )
                )
                continue

            attempted = tuple(receipt.attempted_order)
            unattempted = tuple(receipt.intentionally_unattempted)
            contradicted = tuple(item for item in unattempted if item in recorded_candidates)
            missing = tuple(item for item in attempted if item not in observed)
            if contradicted:
                action = ReceiptAction.REFUSE_CONTRADICTED_RECEIPT
            elif missing:
                action = ReceiptAction.REPLAY_MISSING_OUTCOME
            else:
                action = ReceiptAction.SEALED_AND_CONSISTENT
            tasks.append(
                TaskReceiptState(
                    task_id=task_id,
                    action=action,
                    attempted=attempted,
                    intentionally_unattempted=unattempted,
                    missing_outcomes=missing,
                    contradicted=contradicted,
                    stop_reason=receipt.stop_reason,
                )
            )
        return ReceiptAwareResumePlan(plan=plan, tasks=tuple(tasks))


def _require_consistent_with(
    manifest: RealityCampaignManifest, references: Iterable[RealityOutcomeReference]
) -> None:
    """A recorded outcome for a planned task must match the manifest revision it names.

    Changed inputs require a new campaign revision. Silently accepting an outcome produced
    against an older task manifest would let a corpus mix two definitions of the same task and
    still report one denominator.
    """
    expected = {item.task_id: item.task_manifest_hash for item in manifest.planned_runs}
    for reference in references:
        declared = expected.get(reference.task_id)
        if declared is not None and declared != reference.task_manifest_hash:
            raise CampaignLedgerError(
                f"task {reference.task_id} has a recorded outcome from a different manifest "
                "revision; this needs a new campaign revision, not a resume"
            )


def _reference_from(payload: CodingOutcomeRecorded, event_id: UUID) -> RealityOutcomeReference:
    return RealityOutcomeReference(
        task_run_id=payload.task_run_id,
        run_kind=payload.run_kind,
        task_id=payload.task_id,
        task_manifest_hash=payload.task_manifest_hash,
        candidate_id=payload.candidate_id,
        strategy=payload.candidate_strategy,
        outcome_hash=payload.outcome_hash,
        outcome_artifact_id=payload.outcome_artifact_id,
        outcome_artifact_hash=payload.outcome_artifact_hash,
        hidden_evidence_artifact_id=payload.hidden_evidence_artifact_id,
        hidden_evidence_hash=payload.hidden_evidence_hash,
        final_status=payload.final_status,
        hidden_verification_passed=payload.hidden_verification_passed,
        provider_output_id=payload.provider_output_id,
        source_event_id=event_id,
        occurred_at=payload.occurred_at,
    )
