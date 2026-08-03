"""The decision seam: which correction is tried first, and whether anything is skipped.

S21D2-054. This is the only place in Sprint 21D2 where a learned score changes what the
system actually does, and it changes exactly two things — the order candidates are attempted
in, and how many are attempted at all. It does not create candidates, alter patch bytes, run a
retrieved graph path, or decide acceptance. Every attempted candidate goes through the same
sandbox and the same independent verifier it always did.

Two modes, and the difference between them is the difference between measuring and acting.

`label_all` runs every candidate in the frozen deterministic baseline order, always. Training
and calibration use it because no learner exists yet; the final batches use it because a label
produced under a learned order is a label the learner influenced, which is not a holdout. When
a selected artifact exists, final and shadow additionally *record* the counterfactual learned
order without executing it — that is what makes shadow honest rather than decorative.

`stop_on_first_accepted` is reachable only after activation. Candidates run in the resolved
order and execution stops at the first verifier acceptance, leaving the rest deliberately
unattempted. That third state — neither an outcome nor remaining work — is why the receipt
exists: a resume that reads only outcomes and plans would re-run what the campaign decided not
to do.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from cognitive_os.domain.common import utc_now
from cognitive_os.domain.enums import StreamType
from cognitive_os.events.coding_event_service import CodingEventService
from cognitive_os.events.coding_events import RealityCampaignSequenceRecorded


class SequenceMode(StrEnum):
    LABEL_ALL = "label_all"
    STOP_ON_FIRST_ACCEPTED = "stop_on_first_accepted"


class SequencingError(RuntimeError):
    """The sequence cannot be executed or recorded as described."""


@dataclass(frozen=True, slots=True)
class AttemptResult:
    """What the sandbox and the independent verifier said about one candidate."""

    candidate_id: UUID
    accepted: bool
    event_id: UUID
    verifier_evidence_hash: str


@dataclass(frozen=True, slots=True)
class SequenceOutcome:
    """One task's executed sequence, before it is appended."""

    campaign_id: UUID
    task_id: UUID
    partition: str
    mode: SequenceMode
    campaign_manifest_hash: str
    baseline_order: tuple[UUID, ...]
    resolved_order: tuple[UUID, ...]
    attempted_order: tuple[UUID, ...]
    intentionally_unattempted: tuple[UUID, ...]
    accepted_candidate_id: UUID | None
    accepted_position: int | None
    accepted_event_id: UUID | None
    verifier_evidence_hash: str | None
    stop_reason: str
    learned_ordering_used: bool


#: Executes one candidate through the existing sandbox and hidden verifier.
AttemptRunner = Callable[[UUID], Awaitable[AttemptResult]]


class CorrectionCandidateSequencer:
    """Runs one task's candidates in the declared mode and records what happened."""

    def __init__(
        self,
        events: CodingEventService,
        *,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._events = events
        self._clock = clock

    async def run_task(
        self,
        *,
        campaign_id: UUID,
        task_id: UUID,
        partition: str,
        mode: SequenceMode,
        campaign_manifest_hash: str,
        baseline_order: Sequence[UUID],
        attempt: AttemptRunner,
        resolved_order: Sequence[UUID] | None = None,
        learned_ordering_used: bool = False,
    ) -> SequenceOutcome:
        """Execute one task's candidates. The mode decides how many of them run.

        `resolved_order` is the learned permutation when one exists. Under `label_all` it is
        recorded and *not* executed; under `stop_on_first_accepted` it is the execution order.
        """
        if not baseline_order:
            raise SequencingError("a task with no candidates has no sequence to run")
        if len(set(baseline_order)) != len(baseline_order):
            raise SequencingError("the baseline order names a candidate twice")

        resolved = tuple(resolved_order) if resolved_order is not None else tuple(baseline_order)
        if sorted(resolved, key=str) != sorted(baseline_order, key=str):
            raise SequencingError("the resolved order is not a permutation of the baseline order")

        # Under label_all the execution order is the baseline order, whatever was resolved.
        # This is the line that keeps a final batch a holdout rather than a self-graded set.
        execution_order = (
            tuple(baseline_order) if mode is SequenceMode.LABEL_ALL else tuple(resolved)
        )

        attempted: list[UUID] = []
        accepted: AttemptResult | None = None
        for candidate_id in execution_order:
            result = await attempt(candidate_id)
            if result.candidate_id != candidate_id:
                raise SequencingError(
                    f"the runner returned candidate {result.candidate_id} for {candidate_id}"
                )
            attempted.append(candidate_id)
            if result.accepted:
                accepted = result
                if mode is SequenceMode.STOP_ON_FIRST_ACCEPTED:
                    break

        unattempted = tuple(item for item in execution_order if item not in set(attempted))
        if mode is SequenceMode.LABEL_ALL and unattempted:  # pragma: no cover - loop is total
            raise SequencingError("label_all left a candidate unattempted")

        if accepted is None:
            stop_reason = "exhausted_without_acceptance"
        elif mode is SequenceMode.STOP_ON_FIRST_ACCEPTED:
            stop_reason = "verifier_accepted"
        else:
            stop_reason = "all_candidates_labelled"

        return SequenceOutcome(
            campaign_id=campaign_id,
            task_id=task_id,
            partition=partition,
            mode=mode,
            campaign_manifest_hash=campaign_manifest_hash,
            baseline_order=tuple(baseline_order),
            resolved_order=resolved,
            attempted_order=tuple(attempted),
            intentionally_unattempted=unattempted,
            accepted_candidate_id=None if accepted is None else accepted.candidate_id,
            accepted_position=None if accepted is None else attempted.index(accepted.candidate_id),
            accepted_event_id=None if accepted is None else accepted.event_id,
            verifier_evidence_hash=None if accepted is None else accepted.verifier_evidence_hash,
            stop_reason=stop_reason,
            learned_ordering_used=learned_ordering_used and mode is not SequenceMode.LABEL_ALL,
        )

    async def record(self, outcome: SequenceOutcome, *, correlation_id: UUID) -> UUID:
        """Seal the sequence on the campaign stream with compare-and-set.

        The append is the terminal authority for this sequence. No process-local receipt and
        no second database: a receipt that lived anywhere else would be a second answer to the
        question of what this campaign already did.
        """
        payload = RealityCampaignSequenceRecorded(
            campaign_id=outcome.campaign_id,
            task_id=outcome.task_id,
            partition=outcome.partition,
            mode=outcome.mode.value,
            campaign_manifest_hash=outcome.campaign_manifest_hash,
            baseline_order=outcome.baseline_order,
            resolved_order=outcome.resolved_order,
            attempted_order=outcome.attempted_order,
            accepted_candidate_id=outcome.accepted_candidate_id,
            accepted_position=outcome.accepted_position,
            accepted_event_id=outcome.accepted_event_id,
            verifier_evidence_hash=outcome.verifier_evidence_hash,
            stop_reason=outcome.stop_reason,
            intentionally_unattempted=outcome.intentionally_unattempted,
            learned_ordering_used=outcome.learned_ordering_used,
            occurred_at=self._clock(),
        )
        return await self._events.append(
            outcome.campaign_id,
            payload,
            correlation_id=correlation_id,
            stream_type=StreamType.SYSTEM,
        )
