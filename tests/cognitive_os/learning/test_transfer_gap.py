"""The §4 measurement, tested on the quantity the successor's decision rule reads.

The transfer gap is not a rate, it is a *difference of differences*: how far the sealed
direction sits above the strongest deterministic rung on one corpus, minus the same distance on
another. Every sprint before D7 could have reported two rates and read a collapse into corpus
difficulty. So what is tested here is the arithmetic that separates them, on two synthetic
corpora built to make the separation checkable by hand:

*A learned rate that falls while the ladder falls with it is not a collapse* — the difference
holds, `difference_shift` is zero, and §3.4 would read `stable`.

*A learned rate that falls while the ladder holds is one* — the difference shifts negative,
which is the reading the released record carries at -0.32.

The record is also round-tripped through its own JSON, because the D7 backlog binds W2 to it as
sealed W-stage evidence: a record that does not reproduce its content hash after a reload is a
record no later wave can cite.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from uuid import UUID, uuid5

from cognitive_os.learning.correction_ladder import (
    FIXED_INPUT_ORDER,
    LADDER_RUNGS,
    WIDTH_20_BOUNDED_GRAPH,
)
from cognitive_os.learning.correction_matrix import FittedMatrix, FittedRow
from cognitive_os.learning.correction_ranking import (
    NUMERIC_FEATURE_NAMES,
    CorrectionFeatureVector,
)
from cognitive_os.learning.transfer_gap import (
    COLLAPSED_READING,
    STABLE_READING,
    CorpusHalf,
    TransferGapRecordV1,
    measure_corpus,
    measure_transfer_gap,
)

NAMESPACE = UUID("5e2c8a41-9b76-5d03-8f14-3a7e6c2b91d5")
AT = datetime(2026, 8, 10, 12, 46, tzinfo=UTC)
COLUMNS = (
    *NUMERIC_FEATURE_NAMES,
    "query_to_candidate_cosine",
    "missing_value_indicators",
    "declared_verifier_capabilities",
)
FAMILIES = ("boundary", "state")


def _vector(seed: int, *, cosine: float) -> CorrectionFeatureVector:
    digest = sha256(f"transfer:{seed}".encode()).digest()
    values = tuple(
        (name, cosine if name == "query_to_candidate_cosine" else round((digest[i] + 1) / 256, 6))
        for i, name in enumerate(COLUMNS)
    )
    return CorrectionFeatureVector(
        encoder_version="correction-ranking-v1",
        values=values,
        embedding=tuple(round((digest[index] + 1) / 256, 6) for index in range(8)),
    )


def _half(
    name: str,
    *,
    learned_correct: int,
    accepted_position: int,
    informative: bool = True,
) -> CorpusHalf:
    """Four groups, and the two knobs that move a rung and the direction independently.

    `accepted_position` 0 makes `fixed_input_order` right on every group; `informative` decides
    whether the cosine channel points at the accepted candidate, which is what lets a corpus be
    built where the deterministic ladder itself is weak. The learned verdicts are handed in,
    because this module is fit-free and scores no model of its own.
    """
    rows: list[FittedRow] = []
    order: dict[str, tuple[str, ...]] = {}
    requirements: dict[str, str] = {}
    deltas: dict[str, str] = {}
    families: dict[str, str] = {}
    learned: dict[str, bool] = {}
    for index in range(4):
        group = f"{name}-group-{index}"
        ids: list[str] = []
        for position in range(4):
            # A stable seed: `hash()` on a string is salted per process, which would make the
            # fixture — and therefore the rung rates it produces — differ between runs.
            seed = int.from_bytes(sha256(f"{name}:{index}:{position}".encode()).digest()[:4])
            informed = informative and position == accepted_position
            vector = _vector(seed, cosine=0.9 if informed else 0.1)
            candidate_id = uuid5(NAMESPACE, f"{name}:candidate:{index}:{position}")
            ids.append(str(candidate_id))
            rows.append(
                FittedRow(
                    candidate_id=candidate_id,
                    task_id=uuid5(NAMESPACE, group),
                    group=group,
                    partition="calibration",
                    vector=vector,
                    accepted=position == accepted_position,
                    sealed_at=AT,
                    outcome_at=AT,
                    observation_id=uuid5(NAMESPACE, f"{name}:observation:{index}:{position}"),
                    sealed_feature_hash=vector.content_hash(),
                )
            )
            deltas[str(candidate_id)] = f"diff {group} slot {position}"
        order[group] = tuple(ids)
        requirements[group] = "return the normalised sequence"
        families[group] = FAMILIES[index // 2]
        learned[group] = index < learned_correct
    return CorpusHalf(
        name=name,
        matrix=FittedMatrix(split="calibration", rows=tuple(rows)),
        order=order,
        requirement_texts=requirements,
        delta_texts=deltas,
        family_by_group=families,
        learned_first_choice_correct=learned,
    )


class TestOneCorpus:
    def test_every_frozen_rung_is_reported_and_the_ineligible_one_carries_its_reason(self) -> None:
        rates = measure_corpus(_half("d5", learned_correct=4, accepted_position=0), measured_at=AT)

        assert tuple(rung.rung for rung in rates.rungs) == LADDER_RUNGS
        graph = next(rung for rung in rates.rungs if rung.rung == WIDTH_20_BOUNDED_GRAPH)
        assert graph.eligible is False
        assert graph.first_choice_rate is None
        assert graph.ineligible_reason
        assert rates.groups == 4
        assert rates.matrix_hash == rates.matrix_hash

    def test_the_difference_is_the_learned_rate_minus_the_strongest_rung(self) -> None:
        """Accepted at slot 0, so `fixed_input_order` is right everywhere and is the ceiling."""
        rates = measure_corpus(_half("d5", learned_correct=3, accepted_position=0), measured_at=AT)

        assert rates.strongest_rung == FIXED_INPUT_ORDER
        assert Decimal(rates.strongest_rung_rate) == Decimal("1")
        assert Decimal(rates.learned_first_choice_rate) == Decimal("0.75")
        assert Decimal(rates.learned_minus_strongest) == Decimal("-0.25")

    def test_every_rate_is_also_reported_per_family(self) -> None:
        rates = measure_corpus(_half("d5", learned_correct=2, accepted_position=0), measured_at=AT)

        assert dict(rates.learned_by_family) == {"boundary": "1", "state": "0"}
        for rung in rates.rungs:
            assert bool(rung.by_family) is rung.eligible
            assert {family for family, _ in rung.by_family} <= set(FAMILIES)


class TestTheGapBetweenTwoCorpora:
    def test_a_learned_rate_that_falls_with_the_ladder_is_not_a_collapse(self) -> None:
        record = measure_transfer_gap(
            _half("d5", learned_correct=4, accepted_position=0),
            _half("d6", learned_correct=0, accepted_position=3, informative=False),
            measured_at=AT,
        )

        # The learned rate falls as far as a rate can fall — and every rung falls with it, so
        # the difference holds at zero. That is §4's `stable` reading: the transfer gap is
        # corpus difficulty, and a sprint reporting only the two rates would have called it a
        # collapse and gone looking for a new class it did not need.
        assert Decimal(record.learned_shift) == Decimal("-1")
        assert Decimal(record.difference_shift) == Decimal("0")

    def test_a_learned_rate_that_falls_while_the_ladder_holds_is_one(self) -> None:
        record = measure_transfer_gap(
            _half("d5", learned_correct=4, accepted_position=0),
            _half("d6", learned_correct=2, accepted_position=0),
            measured_at=AT,
        )

        assert Decimal(record.learned_shift) == Decimal("-0.5")
        assert Decimal(record.difference_shift) == Decimal("-0.5")
        assert dict(record.baseline_shift_by_rung)[FIXED_INPUT_ORDER] == "0"
        # The ineligible rung contributes no shift rather than a zero one.
        assert WIDTH_20_BOUNDED_GRAPH not in dict(record.baseline_shift_by_rung)

    def test_both_readings_travel_with_the_record_and_no_verdict_does(self) -> None:
        record = measure_transfer_gap(
            _half("d5", learned_correct=4, accepted_position=0),
            _half("d6", learned_correct=2, accepted_position=0),
            measured_at=AT,
        )

        assert record.stable_reading == STABLE_READING
        assert record.collapsed_reading == COLLAPSED_READING
        assert "verdict" not in record.model_dump()
        assert len(record.corpora) == 2

    def test_the_record_round_trips_through_its_own_json(self) -> None:
        record = measure_transfer_gap(
            _half("d5", learned_correct=4, accepted_position=0),
            _half("d6", learned_correct=2, accepted_position=0),
            measured_at=AT,
        )
        reloaded = TransferGapRecordV1.model_validate(json.loads(record.model_dump_json()))

        assert reloaded.content_hash == record.content_hash
        assert reloaded.difference_shift == record.difference_shift
