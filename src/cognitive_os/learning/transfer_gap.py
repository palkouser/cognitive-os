"""The transfer-gap measurement — §4 of the D7 handoff, as one deterministic function.

Three sprints measured numbers that were partly a property of a ranker and partly a property
of the gap between two authoring runs, and nothing separated the two. This module separates
them, exactly the way the handoff pre-registered: the released deterministic ladder over both
corpora, every rung, reported per family, beside the same sealed direction's first-choice
rate on each — and the one derived quantity the decision turns on, the learned-minus-baseline
difference per corpus.

The decision rule belongs to the successor's pre-registration, not to this module, so the
record carries both readings as vocabulary and no verdict field:

*stable* — the difference holds across corpora and only the absolute rates move: the
transfer gap is corpus difficulty, and the confidence axis over the existing class is
genuinely exhausted.

*collapsed* — the difference itself collapses: the direction does not transfer, no admission
rule over its margin ever will, and the class question is the right successor question.

Everything here is read-only and fit-free. The inputs are rebuilt released bytes — matrices
whose hashes must equal the published ones before a caller hands them in — and the outputs
are rates over decisions that are all already spent. Nothing here can open, spend or select.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from pydantic import Field

from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, UtcDatetime
from cognitive_os.domain.experience import HashedExperienceContract
from cognitive_os.learning.correction_ladder import (
    LADDER_RUNGS,
    TaskGroupCandidates,
    eligible_rungs,
    group_candidates,
)
from cognitive_os.learning.correction_matrix import FittedMatrix

#: The two readings §4 names. Stored in every record so the successor's pre-registered rule
#: can bind to exact strings rather than to a paraphrase.
STABLE_READING = (
    "the learned-minus-baseline difference is stable across corpora and only the absolute "
    "rates move: the transfer gap is corpus difficulty and the confidence axis is exhausted"
)
COLLAPSED_READING = (
    "the learned-minus-baseline difference itself collapses: the direction does not "
    "transfer, and no admission rule over it ever will"
)


@dataclass(frozen=True, slots=True)
class CorpusHalf:
    """One corpus as the measurement wants it: the matrix, the frozen order and the texts.

    `family_by_group` comes from the sealed catalogue, never from a heuristic over names.
    `learned_first_choice_correct` is the sealed direction's verdict per group, scored by
    the caller with the released ranker so this module stays fit-free and model-free.
    """

    name: str
    matrix: FittedMatrix
    order: Mapping[str, Sequence[str]]
    requirement_texts: Mapping[str, str]
    delta_texts: Mapping[str, str]
    family_by_group: Mapping[str, str]
    learned_first_choice_correct: Mapping[str, bool]


class RungRates(HashedExperienceContract):
    """One rung's rate on one corpus, whole and per family."""

    rung: NonEmptyStr
    eligible: bool
    first_choice_rate: str | None = None
    by_family: tuple[tuple[NonEmptyStr, str], ...] = ()
    ineligible_reason: str | None = None


class CorpusTransferRates(HashedExperienceContract):
    """Everything §4 asks of one corpus: every rung, the direction, and the difference."""

    corpus: NonEmptyStr
    matrix_hash: Sha256Hex
    groups: int = Field(ge=1)
    rungs: tuple[RungRates, ...] = Field(min_length=1)
    learned_first_choice_rate: str
    learned_by_family: tuple[tuple[NonEmptyStr, str], ...] = Field(min_length=1)
    strongest_rung: NonEmptyStr
    strongest_rung_rate: str
    learned_minus_strongest: str


class TransferGapRecordV1(HashedExperienceContract):
    """The §4 measurement over two corpora, and the collapse quantity between them.

    `difference_shift` is the second corpus's learned-minus-strongest minus the first's —
    the number whose sign and size the pre-registered rule reads. The two reading sentences
    travel with every record so the rule binds to frozen text.
    """

    revision: int = 1
    corpora: tuple[CorpusTransferRates, ...] = Field(min_length=2, max_length=2)
    learned_shift: str
    baseline_shift_by_rung: tuple[tuple[NonEmptyStr, str], ...] = Field(min_length=1)
    difference_shift: str
    stable_reading: NonEmptyStr = STABLE_READING
    collapsed_reading: NonEmptyStr = COLLAPSED_READING
    measured_at: UtcDatetime


def _rate(correct: int, total: int) -> Decimal:
    return Decimal(correct) / Decimal(total)


def _family_rates(
    groups: Sequence[TaskGroupCandidates],
    family_by_group: Mapping[str, str],
    verdict: Mapping[str, bool],
) -> tuple[tuple[str, str], ...]:
    counts: dict[str, list[int]] = {}
    for group in groups:
        family = family_by_group[group.group]
        totals = counts.setdefault(family, [0, 0])
        totals[0] += int(verdict[group.group])
        totals[1] += 1
    return tuple(
        (family, str(_rate(correct, total))) for family, (correct, total) in sorted(counts.items())
    )


def measure_corpus(half: CorpusHalf, *, measured_at: UtcDatetime) -> CorpusTransferRates:
    """Every rung and the sealed direction on one corpus, whole and per family."""
    groups = group_candidates(
        half.matrix,
        order=half.order,
        requirement_texts=half.requirement_texts,
        delta_texts=half.delta_texts,
    )
    available = eligible_rungs(half.matrix.rows[0].vector.encoder_version)
    rungs: list[RungRates] = []
    strongest: tuple[str, Decimal] | None = None
    for name in LADDER_RUNGS:
        ordering = available.get(name)
        if ordering is None:
            rungs.append(
                RungRates(
                    rung=name,
                    eligible=False,
                    ineligible_reason=(
                        "ineligible on this surface; the released ladder records the reason"
                    ),
                )
            )
            continue
        verdict = {group.group: group.accepted(ordering(group)[0]) for group in groups}
        rate = _rate(sum(verdict.values()), len(groups))
        rungs.append(
            RungRates(
                rung=name,
                eligible=True,
                first_choice_rate=str(rate),
                by_family=_family_rates(groups, half.family_by_group, verdict),
            )
        )
        if strongest is None or rate > strongest[1]:
            strongest = (name, rate)
    if strongest is None:  # pragma: no cover - the frozen ladder always has eligible rungs
        raise ValueError("no eligible rung; the ladder cannot anchor a difference")

    learned_rate = _rate(
        sum(half.learned_first_choice_correct[group.group] for group in groups), len(groups)
    )
    return CorpusTransferRates(
        corpus=half.name,
        matrix_hash=half.matrix.content_hash,
        groups=len(groups),
        rungs=tuple(rungs),
        learned_first_choice_rate=str(learned_rate),
        learned_by_family=_family_rates(
            groups, half.family_by_group, dict(half.learned_first_choice_correct)
        ),
        strongest_rung=strongest[0],
        strongest_rung_rate=str(strongest[1]),
        learned_minus_strongest=str(learned_rate - strongest[1]),
    )


def measure_transfer_gap(
    first: CorpusHalf,
    second: CorpusHalf,
    *,
    measured_at: UtcDatetime,
) -> TransferGapRecordV1:
    """§4's record: both corpora measured identically, and the collapse quantity between."""
    left = measure_corpus(first, measured_at=measured_at)
    right = measure_corpus(second, measured_at=measured_at)
    shifts = []
    for rung_left in left.rungs:
        rung_right = next(item for item in right.rungs if item.rung == rung_left.rung)
        if rung_left.eligible and rung_right.eligible:
            shifts.append(
                (
                    rung_left.rung,
                    str(
                        Decimal(str(rung_right.first_choice_rate))
                        - Decimal(str(rung_left.first_choice_rate))
                    ),
                )
            )
    return TransferGapRecordV1(
        corpora=(left, right),
        learned_shift=str(
            Decimal(right.learned_first_choice_rate) - Decimal(left.learned_first_choice_rate)
        ),
        baseline_shift_by_rung=tuple(shifts),
        difference_shift=str(
            Decimal(right.learned_minus_strongest) - Decimal(left.learned_minus_strongest)
        ),
        measured_at=measured_at,
    )
