"""S21D2-054: the one place a learned score changes what the system does.

Two properties carry the sprint. `label_all` must execute the frozen baseline order even when
a learned order was resolved — otherwise a final batch is graded under an order the learner
chose, which is not a holdout. And `stop_on_first_accepted` must record what it deliberately
did not attempt — otherwise a resume reading only outcomes and plans re-runs work the campaign
already decided to skip, which is a different campaign wearing the same ID.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from cognitive_os.application.services.correction_candidate_sequencer import (
    AttemptResult,
    CorrectionCandidateSequencer,
    SequenceMode,
    SequencingError,
)
from cognitive_os.application.services.reality_campaign import (
    ReceiptAction,
    ReceiptAwareResumePlan,
    ResumePlan,
    TaskReceiptState,
)
from cognitive_os.domain.enums import StreamType
from cognitive_os.domain.reality import (
    RealityCandidateSource,
    RealityCandidateStrategy,
    RealityRunIdentity,
    RealityRunKind,
)
from cognitive_os.events.coding_event_service import CodingEventService
from cognitive_os.events.coding_events import RealityCampaignSequenceRecorded
from cognitive_os.events.memory_store import MemoryEventStore

CAMPAIGN = UUID(int=31)
TASK = UUID(int=32)
MANIFEST = "a" * 64
EVIDENCE = "b" * 64
CANDIDATES = tuple(UUID(int=100 + index) for index in range(4))


def _runner(accepting: set[UUID]):
    """Records what was actually asked for, so the order can be asserted afterwards."""
    seen: list[UUID] = []

    async def attempt(candidate_id: UUID) -> AttemptResult:
        seen.append(candidate_id)
        return AttemptResult(
            candidate_id=candidate_id,
            accepted=candidate_id in accepting,
            event_id=uuid4(),
            verifier_evidence_hash=EVIDENCE,
        )

    return attempt, seen


def _sequencer() -> tuple[CorrectionCandidateSequencer, MemoryEventStore]:
    store = MemoryEventStore()
    return CorrectionCandidateSequencer(CodingEventService(store)), store


async def _run(mode: SequenceMode, *, accepting: set[UUID], resolved=None, learned=False):
    sequencer, store = _sequencer()
    attempt, seen = _runner(accepting)
    outcome = await sequencer.run_task(
        campaign_id=CAMPAIGN,
        task_id=TASK,
        partition="training",
        mode=mode,
        campaign_manifest_hash=MANIFEST,
        baseline_order=CANDIDATES,
        attempt=attempt,
        resolved_order=resolved,
        learned_ordering_used=learned,
    )
    return outcome, seen, sequencer, store


@pytest.mark.asyncio
class TestLabelAllIgnoresTheLearnedOrder:
    async def test_it_executes_every_candidate_in_baseline_order(self) -> None:
        outcome, seen, _, _ = await _run(SequenceMode.LABEL_ALL, accepting={CANDIDATES[1]})

        assert seen == list(CANDIDATES)
        assert outcome.attempted_order == CANDIDATES
        assert outcome.intentionally_unattempted == ()

    async def test_a_resolved_order_is_recorded_but_not_executed(self) -> None:
        """The counterfactual is what makes shadow honest; executing it would bias the label."""
        reversed_order = tuple(reversed(CANDIDATES))
        outcome, seen, _, _ = await _run(
            SequenceMode.LABEL_ALL, accepting=set(), resolved=reversed_order, learned=True
        )

        assert seen == list(CANDIDATES)
        assert outcome.resolved_order == reversed_order
        assert outcome.attempted_order == CANDIDATES
        assert outcome.learned_ordering_used is False

    async def test_it_keeps_going_after_an_acceptance(self) -> None:
        outcome, seen, _, _ = await _run(SequenceMode.LABEL_ALL, accepting={CANDIDATES[0]})

        assert len(seen) == 4
        assert outcome.stop_reason == "all_candidates_labelled"


@pytest.mark.asyncio
class TestStopFirstStopsAndSaysWhatItSkipped:
    async def test_it_stops_at_the_first_acceptance(self) -> None:
        outcome, seen, _, _ = await _run(
            SequenceMode.STOP_ON_FIRST_ACCEPTED, accepting={CANDIDATES[1]}
        )

        assert seen == [CANDIDATES[0], CANDIDATES[1]]
        assert outcome.accepted_candidate_id == CANDIDATES[1]
        assert outcome.accepted_position == 1
        assert outcome.stop_reason == "verifier_accepted"

    async def test_the_skipped_candidates_are_named(self) -> None:
        outcome, _, _, _ = await _run(
            SequenceMode.STOP_ON_FIRST_ACCEPTED, accepting={CANDIDATES[1]}
        )

        assert outcome.intentionally_unattempted == CANDIDATES[2:]

    async def test_it_follows_the_resolved_order(self) -> None:
        resolved = (CANDIDATES[3], CANDIDATES[0], CANDIDATES[1], CANDIDATES[2])
        outcome, seen, _, _ = await _run(
            SequenceMode.STOP_ON_FIRST_ACCEPTED,
            accepting={CANDIDATES[0]},
            resolved=resolved,
            learned=True,
        )

        assert seen == [CANDIDATES[3], CANDIDATES[0]]
        assert outcome.learned_ordering_used is True

    async def test_nothing_accepted_exhausts_the_list_and_says_so(self) -> None:
        outcome, seen, _, _ = await _run(SequenceMode.STOP_ON_FIRST_ACCEPTED, accepting=set())

        assert len(seen) == 4
        assert outcome.stop_reason == "exhausted_without_acceptance"
        assert outcome.intentionally_unattempted == ()


@pytest.mark.asyncio
class TestTheReceiptIsTheTerminalAuthority:
    async def test_it_appends_to_the_campaign_stream_as_a_system_event(self) -> None:
        outcome, _, sequencer, store = await _run(
            SequenceMode.STOP_ON_FIRST_ACCEPTED, accepting={CANDIDATES[1]}
        )

        event_id = await sequencer.record(outcome, correlation_id=CAMPAIGN)

        stored = await store.get_event(event_id)
        assert stored is not None
        assert stored.envelope.stream_id == CAMPAIGN
        assert stored.envelope.stream_type is StreamType.SYSTEM
        assert stored.envelope.event_type == RealityCampaignSequenceRecorded.event_type

    async def test_the_receipt_carries_the_three_orders_and_the_skips(self) -> None:
        outcome, _, sequencer, store = await _run(
            SequenceMode.STOP_ON_FIRST_ACCEPTED, accepting={CANDIDATES[1]}
        )

        event_id = await sequencer.record(outcome, correlation_id=CAMPAIGN)
        payload = (await store.get_event(event_id)).envelope.payload

        assert [UUID(item) for item in payload["baseline_order"]] == list(CANDIDATES)
        assert [UUID(item) for item in payload["attempted_order"]] == list(CANDIDATES[:2])
        assert [UUID(item) for item in payload["intentionally_unattempted"]] == list(CANDIDATES[2:])

    async def test_two_sequences_of_one_campaign_share_one_ordered_stream(self) -> None:
        """One stream per campaign is what makes a concurrent resume lose the race."""
        outcome, _, sequencer, store = await _run(SequenceMode.LABEL_ALL, accepting={CANDIDATES[0]})
        await sequencer.record(outcome, correlation_id=CAMPAIGN)
        await sequencer.record(outcome, correlation_id=CAMPAIGN)

        assert await store.get_stream_version(CAMPAIGN) == 2


class TestTheReceiptContractRefusesAnIncoherentSequence:
    def _payload(self, **overrides: object) -> dict[str, object]:
        fields: dict[str, object] = {
            "campaign_id": CAMPAIGN,
            "task_id": TASK,
            "partition": "canary",
            "mode": "stop_on_first_accepted",
            "campaign_manifest_hash": MANIFEST,
            "baseline_order": CANDIDATES,
            "resolved_order": CANDIDATES,
            "attempted_order": CANDIDATES[:2],
            "accepted_candidate_id": CANDIDATES[1],
            "accepted_position": 1,
            "accepted_event_id": uuid4(),
            "verifier_evidence_hash": EVIDENCE,
            "stop_reason": "verifier_accepted",
            "intentionally_unattempted": CANDIDATES[2:],
            "occurred_at": "2026-08-01T09:00:00Z",
        }
        fields.update(overrides)
        return fields

    def test_a_coherent_receipt_validates(self) -> None:
        assert RealityCampaignSequenceRecorded(**self._payload()).accepted_position == 1

    def test_a_resolved_order_that_is_not_a_permutation_is_refused(self) -> None:
        with pytest.raises(ValueError, match="permutation"):
            RealityCampaignSequenceRecorded(**self._payload(resolved_order=CANDIDATES[:3]))

    def test_a_candidate_both_attempted_and_skipped_is_refused(self) -> None:
        with pytest.raises(ValueError, match="both attempted and unattempted"):
            RealityCampaignSequenceRecorded(
                **self._payload(intentionally_unattempted=CANDIDATES[1:])
            )

    def test_an_unaccounted_candidate_is_refused(self) -> None:
        """Every candidate is an outcome or a deliberate skip; there is no third silence."""
        with pytest.raises(ValueError, match="unaccounted"):
            RealityCampaignSequenceRecorded(**self._payload(intentionally_unattempted=()))

    def test_an_acceptance_without_verifier_evidence_is_refused(self) -> None:
        with pytest.raises(ValueError, match="a claim, not a result"):
            RealityCampaignSequenceRecorded(**self._payload(verifier_evidence_hash=None))

    def test_an_accepted_position_that_disagrees_with_the_order_is_refused(self) -> None:
        with pytest.raises(ValueError, match="does not match the attempt order"):
            RealityCampaignSequenceRecorded(**self._payload(accepted_position=0))

    def test_skipping_candidates_with_nothing_accepted_is_refused(self) -> None:
        with pytest.raises(ValueError, match="neither finished nor stopped"):
            RealityCampaignSequenceRecorded(
                **self._payload(
                    accepted_candidate_id=None,
                    accepted_position=None,
                    accepted_event_id=None,
                    verifier_evidence_hash=None,
                    stop_reason="crashed",
                )
            )

    def test_a_repeated_attempt_is_refused(self) -> None:
        with pytest.raises(ValueError, match="attempted twice"):
            RealityCampaignSequenceRecorded(
                **self._payload(attempted_order=(CANDIDATES[0], CANDIDATES[0]))
            )


@pytest.mark.asyncio
class TestTheSequencerRefusesBadInput:
    async def test_a_task_with_no_candidates_is_refused(self) -> None:
        sequencer, _ = _sequencer()
        attempt, _ = _runner(set())

        with pytest.raises(SequencingError, match="no candidates"):
            await sequencer.run_task(
                campaign_id=CAMPAIGN,
                task_id=TASK,
                partition="training",
                mode=SequenceMode.LABEL_ALL,
                campaign_manifest_hash=MANIFEST,
                baseline_order=(),
                attempt=attempt,
            )

    async def test_a_resolved_order_that_drops_a_candidate_is_refused(self) -> None:
        sequencer, _ = _sequencer()
        attempt, _ = _runner(set())

        with pytest.raises(SequencingError, match="not a permutation"):
            await sequencer.run_task(
                campaign_id=CAMPAIGN,
                task_id=TASK,
                partition="canary",
                mode=SequenceMode.STOP_ON_FIRST_ACCEPTED,
                campaign_manifest_hash=MANIFEST,
                baseline_order=CANDIDATES,
                attempt=attempt,
                resolved_order=CANDIDATES[:2],
            )

    async def test_a_runner_returning_the_wrong_candidate_is_refused(self) -> None:
        sequencer, _ = _sequencer()

        async def wrong(candidate_id: UUID) -> AttemptResult:
            return AttemptResult(
                candidate_id=uuid4(),
                accepted=False,
                event_id=uuid4(),
                verifier_evidence_hash=EVIDENCE,
            )

        with pytest.raises(SequencingError, match="returned candidate"):
            await sequencer.run_task(
                campaign_id=CAMPAIGN,
                task_id=TASK,
                partition="training",
                mode=SequenceMode.LABEL_ALL,
                campaign_manifest_hash=MANIFEST,
                baseline_order=CANDIDATES,
                attempt=wrong,
            )


# ------------------------------------------------------ S21D3-053: the receipt-aware remainder


def _resume(
    *,
    remaining: tuple[UUID, ...],
    left_alone: tuple[UUID, ...] = (),
    action: ReceiptAction = ReceiptAction.REPLAY_MISSING_OUTCOME,
) -> ReceiptAwareResumePlan:
    """A reconciled plan for `TASK`, built directly rather than replayed from a store.

    The reconciliation itself is S21D3-025's and is tested there. What is under test here is
    that the sequencer consults it and nothing else.
    """
    identities = tuple(
        RealityRunIdentity(
            task_id=TASK,
            task_manifest_hash=MANIFEST,
            run_kind=RealityRunKind.CANDIDATE,
            candidate_id=candidate_id,
            strategy=RealityCandidateStrategy.CORRECT_NARROW,
            source=RealityCandidateSource.CURATED,
            generator_profile_id="reality.tasks",
            verifier_profile_hash=EVIDENCE,
            campaign_version=1,
        )
        for candidate_id in remaining
    )
    return ReceiptAwareResumePlan(
        plan=ResumePlan(remaining=identities),
        tasks=(
            TaskReceiptState(
                task_id=TASK,
                action=action,
                attempted=tuple(item for item in CANDIDATES if item not in left_alone),
                intentionally_unattempted=left_alone,
                effective_remaining=identities,
            ),
        ),
    )


async def _resumed(resume: ReceiptAwareResumePlan, *, accepting: set[UUID]):
    sequencer, _ = _sequencer()
    attempt, seen = _runner(accepting)
    outcome = await sequencer.run_task(
        campaign_id=CAMPAIGN,
        task_id=TASK,
        partition="canary",
        mode=SequenceMode.STOP_ON_FIRST_ACCEPTED,
        campaign_manifest_hash=MANIFEST,
        baseline_order=CANDIDATES,
        attempt=attempt,
        resume=resume,
    )
    return outcome, seen


class TestTheRemainderIsTheOnlySchedulableSet:
    @pytest.mark.asyncio
    async def test_only_the_named_missing_outcome_is_replayed(self) -> None:
        outcome, seen = await _resumed(
            _resume(remaining=(CANDIDATES[1],), left_alone=CANDIDATES[2:]), accepting=set()
        )

        assert seen == [CANDIDATES[1]]
        assert outcome.attempted_order == (CANDIDATES[1],)

    @pytest.mark.asyncio
    async def test_candidates_left_alone_never_re_enter(self) -> None:
        """The whole reason the receipt exists: an ordinary plan would list these as remaining."""
        outcome, seen = await _resumed(
            _resume(
                remaining=(),
                left_alone=CANDIDATES[2:],
                action=ReceiptAction.SEALED_AND_CONSISTENT,
            ),
            accepting=set(),
        )

        assert seen == []
        assert outcome.attempted_order == ()
        assert set(outcome.intentionally_unattempted) == set(CANDIDATES[2:])

    @pytest.mark.asyncio
    async def test_a_resume_restates_what_an_earlier_sequence_left_alone(self) -> None:
        """`sequence_receipts` keeps the latest seal only, so the new one must say it again."""
        outcome, _ = await _resumed(
            _resume(remaining=(CANDIDATES[1],), left_alone=CANDIDATES[2:]), accepting=set()
        )

        assert set(outcome.intentionally_unattempted) == set(CANDIDATES[2:])

    @pytest.mark.asyncio
    async def test_the_first_acceptance_still_stops_the_rest_of_the_remainder(self) -> None:
        outcome, seen = await _resumed(_resume(remaining=CANDIDATES[1:]), accepting={CANDIDATES[2]})

        assert seen == [CANDIDATES[1], CANDIDATES[2]]
        assert outcome.accepted_candidate_id == CANDIDATES[2]
        assert outcome.intentionally_unattempted == (CANDIDATES[3],)

    @pytest.mark.asyncio
    async def test_a_repeated_resume_with_nothing_left_runs_nothing(self) -> None:
        outcome, seen = await _resumed(
            _resume(remaining=(), action=ReceiptAction.SEALED_AND_CONSISTENT), accepting=set()
        )

        assert seen == []
        assert outcome.stop_reason == "exhausted_without_acceptance"

    @pytest.mark.asyncio
    async def test_a_contradicted_receipt_makes_the_task_unrunnable(self) -> None:
        with pytest.raises(SequencingError, match="not resumable"):
            await _resumed(
                _resume(remaining=CANDIDATES, action=ReceiptAction.REFUSE_CONTRADICTED_RECEIPT),
                accepting=set(),
            )

    @pytest.mark.asyncio
    async def test_a_remainder_naming_a_stranger_is_refused(self) -> None:
        with pytest.raises(SequencingError, match="outside this task's order"):
            await _resumed(_resume(remaining=(uuid4(),)), accepting=set())

    @pytest.mark.asyncio
    async def test_a_learned_order_reorders_the_remainder_and_never_widens_it(self) -> None:
        sequencer, _ = _sequencer()
        attempt, seen = _runner(set())

        outcome = await sequencer.run_task(
            campaign_id=CAMPAIGN,
            task_id=TASK,
            partition="canary",
            mode=SequenceMode.STOP_ON_FIRST_ACCEPTED,
            campaign_manifest_hash=MANIFEST,
            baseline_order=CANDIDATES,
            attempt=attempt,
            resolved_order=tuple(reversed(CANDIDATES)),
            learned_ordering_used=True,
            resume=_resume(remaining=(CANDIDATES[0], CANDIDATES[2])),
        )

        assert seen == [CANDIDATES[2], CANDIDATES[0]]
        assert outcome.resolved_order == tuple(reversed(CANDIDATES))

    @pytest.mark.asyncio
    async def test_without_a_resume_the_full_order_still_runs(self) -> None:
        """The parameter is optional, and a fresh campaign has no receipt to consult."""
        outcome, seen, _, _ = await _run(SequenceMode.STOP_ON_FIRST_ACCEPTED, accepting=set())

        assert seen == list(CANDIDATES)
        assert outcome.attempted_order == CANDIDATES
