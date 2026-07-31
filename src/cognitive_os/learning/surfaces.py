"""The Sprint 21D1 candidate-surface audit, as data rather than prose.

Four surfaces were named in the D1 handoff. This module records what each one measures
on the frozen C3 evidence, so the audit is a hash-bound artifact that can be replayed
instead of a paragraph in a report that nobody can recompute.

Two rules shape everything here:

* the counts come from the *enumerated* C3 campaign identities, never from a raw table
  scan. The C3 evidence store was never emptied between waves, so `cognitive_os.events`
  holds 641 coding outcome rows against a released denominator of 214. Counting the
  table instead of the campaign inflates every surface by roughly three;
* the audit is written before any held-out metric is read. `SurfaceSampleAudit` carries
  `held_out_metrics_inspected` and `SurfaceSelectionDecision` refuses to rest on an
  audit that admits to it.

The measured verdict is recorded, including the unwelcome one: the provisional primary
surface fails. See `OUTCOME_TRIAGE`.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from cognitive_os.domain.learned import (
    LabelSource,
    SurfaceActionCostMatrix,
    SurfaceAdvisoryAction,
    SurfaceDisposition,
    SurfaceEligibilityReason,
    SurfaceSampleAudit,
    SurfaceSelectionDecision,
)
from cognitive_os.domains.fixtures import FIXTURE_TIME

#: Where every count below can be re-derived from.
AUTHORITY = "docs/sprints/sprint-21/evidence/sprint-21d1-c3-inventory.json"

#: The advisory actions a triage policy may take. None of them accepts anything.
ADVISORY_ACTIONS = tuple(SurfaceAdvisoryAction)

#: Fields that reveal the label. `candidate_strategy` is here because it was *measured*
#: to be a perfect oracle on the C3 coding evidence, not because it looked suspicious.
ANSWER_REVEALING_FIELDS = (
    "candidate_strategy",
    "final_status",
    "hidden_evidence_hash",
    "hidden_verification_passed",
    "outcome_artifact_hash",
    "outcome_hash",
)


def triage_cost_matrix() -> SurfaceActionCostMatrix:
    """Costs for `governed.outcome_triage`.

    Abstaining on a candidate the verifier would reject is the most expensive cell, so
    no policy can be optimised into skipping verification. That is a contract-level
    validator, not a convention.
    """
    return SurfaceActionCostMatrix(
        surface="governed.outcome_triage",
        verify_now_when_accepted=Decimal("1"),
        verify_now_when_rejected=Decimal("1"),
        request_repair_when_accepted=Decimal("2"),
        request_repair_when_rejected=Decimal("1"),
        abstain_when_accepted=Decimal("1"),
        abstain_when_rejected=Decimal("5"),
    )


OUTCOME_TRIAGE = SurfaceSampleAudit(
    surface="governed.outcome_triage",
    authority_reference=AUTHORITY,
    eligible_count=0,
    ineligible_counts=(
        (SurfaceEligibilityReason.NO_PRE_OUTCOME_FEATURE, 150),
        (SurfaceEligibilityReason.SOURCE_EVENT_UNRESOLVED, 64),
    ),
    positive_count=0,
    negative_count=0,
    group_count=30,
    domain_count=7,
    changeable_decision_count=0,
    label_source=LabelSource.INDEPENDENT_VERIFIER,
    deterministic_headroom=(
        "none. On the 150 coding outcomes candidate_strategy determines the verifier "
        "label exactly: baseline 30/30 false, correct_narrow 30/30 true, "
        "correct_robust 30/30 true, incomplete_a 30/30 false, incomplete_b 30/30 false. "
        "Removing that field leaves an identical 2-of-5 pattern on every one of the 30 "
        "tasks, so no remaining pre-outcome feature discriminates. The 64 benchmark "
        "cases are 64/64 passed, a single class."
    ),
    action_cost=triage_cost_matrix(),
    leakage_risks=(
        "candidate_strategy is a perfect label oracle, measured not suspected",
        "final_status, outcome_hash and hidden_evidence_hash are terminal by definition",
        "the 64 benchmark observations carry no source_event_id, so a label cannot be "
        "tied to an ordered pre-outcome event sequence",
    ),
    feature_timing_violations=(
        "candidate_strategy is nominally pre-outcome but is answer-revealing",
    ),
    disposition=SurfaceDisposition.REJECTED,
    audited_at=FIXTURE_TIME,
)

CORRECTION_RANKING = SurfaceSampleAudit(
    surface="experience.correction_ranking",
    authority_reference=AUTHORITY,
    eligible_count=120,
    ineligible_counts=((SurfaceEligibilityReason.ELIGIBLE, 120),),
    positive_count=60,
    negative_count=60,
    group_count=30,
    domain_count=1,
    changeable_decision_count=30,
    label_source=LabelSource.INDEPENDENT_VERIFIER,
    deterministic_headroom=(
        "a positional or majority baseline scores 0.5: every one of the 30 tasks has "
        "exactly 4 candidates of which exactly 2 pass. Patch content differs between "
        "candidates, so unlike outcome triage a content-based policy has something to "
        "discriminate on once candidate_strategy is excluded."
    ),
    action_cost=None,
    leakage_risks=(
        "candidate_strategy must be excluded for the same measured reason as above",
        "the identical 2-of-4 split on every task means group-frequency lookup is "
        "constant and cannot be mistaken for signal",
    ),
    disposition=SurfaceDisposition.DEFERRED,
    audited_at=FIXTURE_TIME,
)

CORRECTION_CONTEXT = SurfaceSampleAudit(
    surface="experience.correction_context",
    authority_reference=AUTHORITY,
    eligible_count=60,
    ineligible_counts=((SurfaceEligibilityReason.ELIGIBLE, 60),),
    positive_count=60,
    negative_count=0,
    group_count=30,
    domain_count=1,
    changeable_decision_count=60,
    label_source=LabelSource.DERIVED,
    deterministic_headroom=(
        "a retrieval surface, not a classification one. Relevance is judged by task and "
        "group identity, so the single-class label balance is expected rather than "
        "degenerate. 60 historical pairs plus the 20 fresh logic and mathematics pairs "
        "of S21D1-030..033 reach the 80-pair graph threshold."
    ),
    action_cost=None,
    leakage_risks=(
        "the query group must be excluded from the candidate pool",
        "correction bytes from the query group must not reach the graph arm",
    ),
    disposition=SurfaceDisposition.SELECTED_SECONDARY,
    audited_at=FIXTURE_TIME,
)

STRATEGY_SELECTION = SurfaceSampleAudit(
    surface="experience.strategy_selection",
    authority_reference=AUTHORITY,
    eligible_count=30,
    ineligible_counts=((SurfaceEligibilityReason.ELIGIBLE, 30),),
    positive_count=30,
    negative_count=0,
    group_count=30,
    domain_count=1,
    changeable_decision_count=0,
    label_source=LabelSource.INDEPENDENT_VERIFIER,
    deterministic_headroom=(
        "none. correct_narrow and correct_robust pass on 30 of 30 tasks and the other "
        "strategies fail on 30 of 30, so a constant policy is already optimal and no "
        "learned selection can change a decision."
    ),
    action_cost=None,
    leakage_risks=("the strategy name is the label",),
    disposition=SurfaceDisposition.REJECTED,
    audited_at=FIXTURE_TIME,
)

#: Every audited candidate, in the order the D1 handoff listed them.
CANDIDATE_SURFACES = (
    CORRECTION_RANKING,
    CORRECTION_CONTEXT,
    OUTCOME_TRIAGE,
    STRATEGY_SELECTION,
)


def surfaces_meeting_primary_thresholds(
    audits: tuple[SurfaceSampleAudit, ...] = CANDIDATE_SURFACES,
    *,
    minimum_eligible: int = 200,
    minimum_changeable: int = 20,
) -> tuple[SurfaceSampleAudit, ...]:
    """Which audits clear the Gate D1 primary-surface thresholds, conditions 6 and 7.

    Returning an empty tuple is a valid and reportable outcome. Gate D1 stays open when
    it happens; the thresholds are not relaxed to produce a winner.
    """
    return tuple(
        audit
        for audit in audits
        if audit.eligible_count >= minimum_eligible
        and audit.changeable_decision_count >= minimum_changeable
        and not audit.degenerate
    )


#: Stable identity for the D1 selection, so the decision hash is reproducible.
SELECTION_ID = uuid5(NAMESPACE_URL, "cognitive-os/sprint-21d1/surface-selection")


def selection_decision() -> SurfaceSelectionDecision:
    """The D1 pre-registration decision, including the primary surface it could not make.

    Recording "no primary surface" is the honest reading of the measurement, and the
    contract requires the reason alongside it. Gate D1 conditions 6 and 7 stay open;
    nothing was relaxed to close them.
    """
    return SurfaceSelectionDecision(
        decision_id=SELECTION_ID,
        primary_surface=None,
        primary_unavailable_reason=(
            "No candidate clears Gate D1 conditions 6 and 7 on frozen C3 evidence. "
            "governed.outcome_triage: candidate_strategy determines the verifier label "
            "with no error on all 150 enumerated coding outcomes, and removing it leaves "
            "the identical 2-of-5 pattern on every task, so nothing discriminates; the 64 "
            "benchmark cases are 64/64 passed. experience.strategy_selection: zero "
            "changeable decisions. experience.correction_ranking is the only balanced "
            "candidate at 60/60 but offers 120 eligible samples against a threshold of "
            "200, and the section 3.3 shortfall cap of 50 cannot close that gap."
        ),
        secondary_surface="experience.correction_context",
        audits=CANDIDATE_SURFACES,
        rationale=(
            "D1 pre-registers the secondary surface only and proceeds with the full "
            "Experience Memory Graph track. The primary-surface result is reported as a "
            "measured negative: the C3 corpus was built to prove a sandbox and a "
            "verifier, and it does that, but it does not carry a triage decision problem."
        ),
        decided_at=FIXTURE_TIME,
    )
