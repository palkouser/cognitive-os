"""What the C3 outcome corpus can and cannot support, measured rather than asserted.

Sprint 21D1 wave W2 was scoped around a primary surface. The W1 audit rejected that
surface, so this module does the honest remaining job: it quantifies the rejection.
Claiming "there is no signal" is worth little; showing that every rung of the declared
baseline ladder is already at its ceiling, and naming which pre-outcome fields are
oracles, is worth a great deal to D2.

The canonical outcome view is a committed artifact, not a database query, so every
number here replays on a machine with no access to the C3 evidence store. The task to
repository-group mapping is derived from `reality_task_specs` and was verified to match
the store exactly: 30 task identities, 30 groups, one to one.

Two rungs of the declared ladder turn out to be oracles by construction, which is a
finding rather than a defect:

* `candidate_strategy` determines the label with no error, measured in W1;
* `run_kind == "baseline"` predicts rejection on 30 of 30 coding baselines, because C3
  built every baseline to fail the hidden suite. That was the property C3 needed and it
  is exactly what makes the field unusable as a feature here.

Nothing in this module fits anything. It evaluates declared deterministic rules.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from random import Random
from uuid import NAMESPACE_URL, uuid5

from cognitive_os.domain.learned import BaselineKind, BaselineLadder, BaselineRung
from cognitive_os.domains.fixtures import FIXTURE_TIME

SURFACE = "governed.outcome_triage"

#: The committed canonical outcome view, one record per unique authoritative outcome.
OUTCOME_VIEW = (
    Path(__file__).resolve().parents[3]
    / "docs/sprints/sprint-21/evidence/sprint-21d1-outcome-view.json"
)

#: Seed for the paired bootstrap. Fixed, so an interval is reproducible.
BOOTSTRAP_SEED = 21_041

#: Why the ladder stops. Mirrors the phase 21.6 convention of recording a stop.
STOPPED_REASON = (
    "no rung has residual headroom that a learned component could take. The two rungs "
    "that score highest do so through fields that are oracles by construction, and the "
    "rungs that exclude those fields cannot beat predicting the class majority."
)


@dataclass(frozen=True, slots=True)
class Outcome:
    """One authoritative C3 outcome, with the grouping keys a split needs."""

    outcome_id: str
    population: str
    group: str
    domain: str
    run_kind: str
    candidate_strategy: str | None
    accepted: bool
    source_event_resolved: bool


def load_outcomes(path: Path = OUTCOME_VIEW) -> tuple[Outcome, ...]:
    """Load the canonical view. Duplicate outcome identities are refused, not collapsed.

    Collapsing silently would hide the very failure mode this view exists to prevent:
    the C3 store holds 641 coding outcome rows against a released denominator of 214.
    """
    records = json.loads(path.read_text())
    outcomes = tuple(
        Outcome(
            outcome_id=record["outcome_id"],
            population=record["population"],
            group=record["group"],
            domain=record["domain"],
            run_kind=record["run_kind"],
            candidate_strategy=record["candidate_strategy"],
            accepted=record["label_accepted_by_verifier"],
            source_event_resolved=record["source_event_resolved"],
        )
        for record in records
    )
    identities = [item.outcome_id for item in outcomes]
    if len(set(identities)) != len(identities):
        raise ValueError("the canonical outcome view contains duplicate outcome identities")
    return outcomes


def _quantise(value: float) -> Decimal:
    return Decimal(f"{value:.4f}")


def _rung(
    name: str, kind: BaselineKind, predictions: Sequence[bool | None], truth: Sequence[bool]
) -> BaselineRung:
    """Score one rung. `None` is an abstention and is never counted as correct."""
    pairs = zip(predictions, truth, strict=True)
    correct = sum(1 for predicted, actual in pairs if predicted == actual)
    abstained = sum(1 for predicted in predictions if predicted is None)
    return BaselineRung(
        name=name,
        kind=kind,
        score=_quantise(correct / len(truth)),
        evaluated_count=len(truth),
        abstained=abstained,
        confident_errors=len(truth) - correct - abstained,
    )


def always_verify_now(outcomes: Sequence[Outcome]) -> BaselineRung:
    """Rung 1. The safety constant: assume nothing is accepted until the verifier says so.

    It is the rung a triage policy must never be allowed to score worse than, because it
    is the only one that never skips a verification.
    """
    return _rung(
        "always_verify_now",
        BaselineKind.TRIVIAL,
        [False] * len(outcomes),
        [o.accepted for o in outcomes],
    )


def majority(outcomes: Sequence[Outcome]) -> BaselineRung:
    """Rung 2. Predict the class majority of the whole sample."""
    truth = [o.accepted for o in outcomes]
    winner = sum(truth) * 2 >= len(truth)
    return _rung(
        f"majority[{'accepted' if winner else 'rejected'}]",
        BaselineKind.TRIVIAL,
        [winner] * len(truth),
        truth,
    )


def visible_contract(outcomes: Sequence[Outcome]) -> BaselineRung:
    """Rung 3. The only allowed pre-outcome structural check: is this a baseline run?

    C3 built every baseline to fail the hidden suite, so this rung is an oracle on the
    30 coding baselines. It is scored and reported precisely so that the oracle is
    visible in the numbers instead of being argued about.
    """
    truth = [o.accepted for o in outcomes]
    predictions = [o.run_kind != "baseline" for o in outcomes]
    return _rung("visible_contract[run_kind]", BaselineKind.DETERMINISTIC, predictions, truth)


def grouped_frequency(outcomes: Sequence[Outcome]) -> BaselineRung:
    """Rung 4. Per-group majority with abstention on an unseen group.

    Leave-one-out per group, so a group never predicts from its own held-out record.
    """
    truth = [o.accepted for o in outcomes]
    by_group: dict[str, list[bool]] = {}
    for item in outcomes:
        by_group.setdefault(item.group, []).append(item.accepted)
    predictions: list[bool | None] = []
    for item in outcomes:
        peers = list(by_group[item.group])
        peers.remove(item.accepted)
        predictions.append(None if not peers else sum(peers) * 2 >= len(peers))
    return _rung("grouped_frequency[leave_one_out]", BaselineKind.DETERMINISTIC, predictions, truth)


def strategy_oracle(outcomes: Sequence[Outcome]) -> BaselineRung:
    """The forbidden rung, scored once to show exactly how much it leaks.

    It is never a candidate baseline. It exists in the report so that "candidate_strategy
    is an oracle" is a number rather than a claim.
    """
    truth = [o.accepted for o in outcomes]
    winning = {"correct_narrow", "correct_robust"}
    predictions = [
        True
        if o.candidate_strategy in winning
        else (None if o.candidate_strategy is None else False)
        for o in outcomes
    ]
    pairs = zip(predictions, outcomes, strict=True)
    resolved = [p if p is not None else o.accepted for p, o in pairs]
    return _rung("FORBIDDEN:candidate_strategy", BaselineKind.DETERMINISTIC, resolved, truth)


def ladder(outcomes: Sequence[Outcome], *, split: str) -> BaselineLadder:
    """Every declared rung on one population, all of them recorded."""
    return BaselineLadder(
        ladder_id=uuid5(NAMESPACE_URL, f"ladder:{SURFACE}:{split}:{len(outcomes)}"),
        surface=SURFACE,
        split=split,
        rungs=(
            always_verify_now(outcomes),
            majority(outcomes),
            visible_contract(outcomes),
            grouped_frequency(outcomes),
        ),
        created_at=FIXTURE_TIME,
    )


def oracle_free_population(outcomes: Sequence[Outcome]) -> tuple[Outcome, ...]:
    """The sample with both construction oracles removed.

    Drops the 30 coding baselines, because C3 built every one of them to fail, and
    leaves `candidate_strategy` unused. What remains is what a learned component would
    actually have to predict from.
    """
    return tuple(item for item in outcomes if item.run_kind != "baseline")


def residual_headroom(outcomes: Sequence[Outcome]) -> dict[str, object]:
    """How much a learned component could possibly gain, per population.

    Reported per population because the two halves fail for opposite reasons: the coding
    candidates are perfectly balanced with no discriminating field, and the benchmark
    cases are a single class where every rung is trivially right.
    """
    result: dict[str, object] = {}
    for population in ("coding", "benchmark"):
        subset = tuple(o for o in oracle_free_population(outcomes) if o.population == population)
        if not subset:
            continue
        accepted = sum(o.accepted for o in subset)
        rungs = ladder(subset, split=f"oracle-free:{population}")
        result[population] = {
            "count": len(subset),
            "accepted": accepted,
            "rejected": len(subset) - accepted,
            "single_class": accepted in (0, len(subset)),
            "strongest_rung": max(rungs.rungs, key=lambda r: r.score).name,
            "strongest_score": str(max(r.score for r in rungs.rungs)),
            "grouped_frequency_score": str(grouped_frequency(subset).score),
        }
    return result


def paired_bootstrap(
    left: Sequence[bool],
    right: Sequence[bool],
    *,
    seed: int = BOOTSTRAP_SEED,
    resamples: int = 2000,
) -> tuple[Decimal, Decimal, Decimal]:
    """Deterministic paired bootstrap of `right - left`, as (lower, point, upper) at 95%.

    Paired because both arms are scored on the same samples; resampling them
    independently would widen the interval by variation the comparison does not have.
    Pure standard library: a fixed-seed `Random` is reproducible across machines and
    costs no dependency.
    """
    if len(left) != len(right):
        raise ValueError("a paired bootstrap needs two equally sized score vectors")
    size = len(left)
    point = sum(right) / size - sum(left) / size
    rng = Random(seed)
    deltas = []
    for _ in range(resamples):
        picks = [rng.randrange(size) for _ in range(size)]
        deltas.append(sum(right[i] for i in picks) / size - sum(left[i] for i in picks) / size)
    deltas.sort()
    lower = deltas[int(0.025 * resamples)]
    upper = deltas[min(int(0.975 * resamples), resamples - 1)]
    return _quantise(lower), _quantise(point), _quantise(upper)


def correctness_vector(
    rung_predictions: Sequence[bool | None], outcomes: Sequence[Outcome]
) -> tuple[bool, ...]:
    """Per-sample correctness, the input a paired comparison needs."""
    return tuple(p == o.accepted for p, o in zip(rung_predictions, outcomes, strict=True))
