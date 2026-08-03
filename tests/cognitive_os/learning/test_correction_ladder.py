"""S21D2-042: the baseline is derived from the ladder, and a straw man cannot become it.

The baseline is the single number a caller could weaken to manufacture a win, so the tests that
matter are the ones that try to weaken it: naming a different rung, feeding in a learned rung
under a deterministic name, and asking a rung to look at the label.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from uuid import UUID, uuid5

import pytest

from cognitive_os.learning.correction_ladder import (
    FIXED_INPUT_ORDER,
    FROZEN_MINILM_COSINE,
    GRAPH_RUNG_INELIGIBLE,
    LADDER_RUNGS,
    LEXICAL_SIMILARITY,
    WIDTH_20_BOUNDED_GRAPH,
    CorrectionBaselineLadder,
    LadderRung,
    build_ladder,
    first_choice_rate,
    group_candidates,
)
from cognitive_os.learning.correction_matrix import FittedMatrix, FittedRow
from cognitive_os.learning.correction_ranking import (
    NUMERIC_FEATURE_NAMES,
    CorrectionFeatureVector,
)

NAMESPACE = UUID("5e2c8a41-9b76-5d03-8f14-3a7e6c2b91d5")
AT = datetime(2026, 8, 2, 13, 0, tzinfo=UTC)
COLUMNS = (
    *NUMERIC_FEATURE_NAMES,
    "query_to_candidate_cosine",
    "missing_value_indicators",
    "declared_verifier_capabilities",
)


def _vector(seed: int, *, cosine: float) -> CorrectionFeatureVector:
    digest = sha256(f"ladder:{seed}".encode()).digest()
    values = tuple(
        (name, cosine if name == "query_to_candidate_cosine" else round((digest[i] + 1) / 256, 6))
        for i, name in enumerate(COLUMNS)
    )
    return CorrectionFeatureVector(
        encoder_version="correction-ranking-v1",
        values=values,
        embedding=tuple(round((digest[index] + 1) / 256, 6) for index in range(8)),
    )


def _fixture(groups: int = 4) -> tuple[FittedMatrix, dict, dict, dict]:
    """`groups` task groups of four candidates; position one is the accepted one every time.

    The cosine channel is made informative on purpose, so the derivation has something to find
    and a test that it found the right rung means something.
    """
    rows: list[FittedRow] = []
    order: dict[str, tuple[str, ...]] = {}
    requirements: dict[str, str] = {}
    deltas: dict[str, str] = {}
    for index in range(groups):
        group = f"group-{index}"
        ids: list[str] = []
        for position in range(4):
            seed = index * 10 + position
            vector = _vector(seed, cosine=0.9 if position == 1 else 0.1)
            candidate_id = uuid5(NAMESPACE, f"candidate:{seed}")
            ids.append(str(candidate_id))
            rows.append(
                FittedRow(
                    candidate_id=candidate_id,
                    task_id=uuid5(NAMESPACE, group),
                    group=group,
                    partition="calibration",
                    vector=vector,
                    accepted=position == 1,
                    sealed_at=AT,
                    outcome_at=AT,
                    observation_id=uuid5(NAMESPACE, f"observation:{seed}"),
                    sealed_feature_hash=vector.content_hash(),
                )
            )
            deltas[str(candidate_id)] = f"diff {group} position {position} rotate the values"
        order[group] = tuple(ids)
        requirements[group] = "rotate the values and return the rotated sequence"
    return FittedMatrix(split="calibration", rows=tuple(rows)), order, requirements, deltas


def _ladder(**kwargs) -> CorrectionBaselineLadder:
    matrix, order, requirements, deltas = _fixture()
    return build_ladder(
        matrix,
        order=order,
        requirement_texts=requirements,
        delta_texts=deltas,
        created_at=AT,
        **kwargs,
    )


class TestTheLadderIsTheFrozenFive:
    def test_every_declared_rung_appears_in_the_frozen_order(self) -> None:
        assert tuple(rung.name for rung in _ladder().rungs) == LADDER_RUNGS

    def test_the_graph_rung_is_ineligible_with_its_reason(self) -> None:
        """A rung that cannot run is recorded as such, never scored at zero."""
        rung = _ladder().rung(WIDTH_20_BOUNDED_GRAPH)

        assert rung.eligible is False
        assert rung.first_choice_rate is None
        assert rung.ineligible_reason == GRAPH_RUNG_INELIGIBLE

    def test_an_ineligible_rung_cannot_carry_a_score(self) -> None:
        with pytest.raises(ValueError, match="cannot carry a score"):
            LadderRung(
                name=WIDTH_20_BOUNDED_GRAPH,
                kind="deterministic",
                eligible=False,
                first_choice_rate="0.4",
                groups_scored=0,
                ineligible_reason="a reason",
            )

    def test_an_ineligible_rung_must_say_why(self) -> None:
        with pytest.raises(ValueError, match="without saying why"):
            LadderRung(
                name=WIDTH_20_BOUNDED_GRAPH,
                kind="deterministic",
                eligible=False,
                groups_scored=0,
            )


class TestTheBaselineIsDerivedRatherThanSupplied:
    def test_the_informative_rung_is_the_one_found(self) -> None:
        ladder = _ladder()

        assert ladder.rung(FROZEN_MINILM_COSINE).first_choice_rate == "1"
        assert ladder.strongest_non_learned_name == FROZEN_MINILM_COSINE
        assert ladder.baseline == Decimal(1)

    def test_naming_a_weaker_rung_as_the_baseline_is_refused(self) -> None:
        ladder = _ladder()
        payload = ladder.model_dump()
        payload.pop("content_hash", None)
        payload["strongest_non_learned_name"] = FIXED_INPUT_ORDER

        with pytest.raises(ValueError, match="derived, never"):
            CorrectionBaselineLadder(**payload)

    def test_understating_the_baseline_rate_is_refused(self) -> None:
        ladder = _ladder()
        payload = ladder.model_dump()
        payload.pop("content_hash", None)
        payload["strongest_non_learned_rate"] = "0.1"

        with pytest.raises(ValueError, match="not the strongest"):
            CorrectionBaselineLadder(**payload)

    def test_a_learned_rung_never_becomes_the_baseline(self) -> None:
        """Excluded by `kind`, not by name, so renaming a learned rung changes nothing."""
        ladder = _ladder(learned={"bounded_cosine_knn": Decimal("1")})

        assert ladder.rung("bounded_cosine_knn").kind == "learned"
        assert ladder.strongest_non_learned_name != "bounded_cosine_knn"

    def test_a_ladder_with_no_eligible_deterministic_rung_has_no_baseline(self) -> None:
        ladder = _ladder()
        payload = ladder.model_dump()
        payload.pop("content_hash", None)
        payload["rungs"] = [
            rung for rung in payload["rungs"] if rung["kind"] == "deterministic" and False
        ] or [
            {
                "name": "bounded_cosine_knn",
                "kind": "learned",
                "eligible": True,
                "first_choice_rate": "1",
                "groups_scored": 4,
                "ineligible_reason": None,
            }
        ]

        with pytest.raises(ValueError, match="no eligible non-learned rung"):
            CorrectionBaselineLadder(**payload)


class TestARungCannotReadTheLabel:
    def test_the_ordering_signature_hands_over_no_verdict(self) -> None:
        """The straw-man guard is structural: a rung receives candidates and an order."""
        matrix, order, requirements, deltas = _fixture()
        groups = group_candidates(
            matrix, order=order, requirement_texts=requirements, delta_texts=deltas
        )
        seen: list[object] = []

        def peeking(group):  # type: ignore[no-untyped-def]
            seen.append(group)
            return group.ordered_candidate_ids

        first_choice_rate(groups, peeking)

        assert seen
        for group in seen:
            assert not hasattr(group, "labels")
            assert not hasattr(group, "verdicts")

    def test_a_rung_scored_on_no_group_is_refused(self) -> None:
        with pytest.raises(ValueError, match="no groups"):
            first_choice_rate((), lambda group: group.ordered_candidate_ids)

    def test_the_lexical_rung_reads_the_texts_rather_than_a_column(self) -> None:
        """Confining the ladder to the encoder's columns would weaken it by accident."""
        rung = _ladder().rung(LEXICAL_SIMILARITY)

        assert rung.eligible is True
        assert rung.groups_scored == 4


class TestTheGroupsCarryTheFrozenOrder:
    def test_an_order_for_a_different_candidate_set_is_refused(self) -> None:
        matrix, order, requirements, deltas = _fixture()
        order["group-0"] = ("not-a-candidate", *order["group-0"][1:])

        with pytest.raises(ValueError, match="different candidate set"):
            group_candidates(
                matrix, order=order, requirement_texts=requirements, delta_texts=deltas
            )
