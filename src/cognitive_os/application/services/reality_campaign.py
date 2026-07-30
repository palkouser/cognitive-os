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
from uuid import UUID

from cognitive_os.application.ports.event_store import EventStorePort
from cognitive_os.domain.reality import (
    RealityCampaignManifest,
    RealityOutcomeCountReason,
    RealityOutcomeReference,
    RealityRunIdentity,
)
from cognitive_os.events.coding_events import CodingOutcomeRecorded


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
