"""S21D2-040 and S21D2-043: the encoder and the ranker, tested on what they refuse.

Accuracy is not the property under test here and cannot be: the corpus does not exist yet.
What is testable now is the shape of the thing — that identity cannot reach a vector, that
ties fall back to the frozen baseline rather than to a candidate ID, that abstention is a
first-class answer rather than a zero score, and that the same inputs produce the same bytes.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from cognitive_os.learning.correction_protocol import (
    FITTED_FEATURE_DENYLIST,
    CorrectionFeatureContract,
)
from cognitive_os.learning.correction_ranking import (
    NUMERIC_FEATURE_NAMES,
    CorrectionEncoder,
    CorrectionEncodingError,
    CorrectionFeatureInput,
    CorrectionKnn,
    Exemplar,
    NumericBounds,
)

EMBEDDING_DIMENSION = 4


def _bounds() -> NumericBounds:
    return NumericBounds(
        lower=dict.fromkeys(NUMERIC_FEATURE_NAMES, 0.0),
        upper=dict.fromkeys(NUMERIC_FEATURE_NAMES, 100.0),
    )


def _features(**overrides: object) -> CorrectionFeatureInput:
    fields: dict[str, object] = {
        "problem_domain": "coding",
        "declared_problem_type": "repair",
        "task_requirement_embedding": (1.0, 0.0, 0.0, 0.0),
        "candidate_delta_embedding": (1.0, 0.0, 0.0, 0.0),
        "changed_file_count": 1,
        "hunk_count": 1,
        "added_line_count": 4,
        "removed_line_count": 2,
        "ast_node_count": 20,
        "graph_node_count": 6,
        "graph_edge_count": 5,
        "graph_path_length": 3,
    }
    fields.update(overrides)
    return CorrectionFeatureInput(**fields)  # type: ignore[arg-type]


def _vector(encoder: CorrectionEncoder, embedding: tuple[float, ...], **overrides: object):
    return encoder.encode(_features(candidate_delta_embedding=embedding, **overrides))


class TestTheEncoderEmitsOnlyAllowedFields:
    def test_no_emitted_name_is_on_the_denylist(self) -> None:
        vector = CorrectionEncoder(_bounds()).encode(_features())

        assert not set(vector.names) & set(FITTED_FEATURE_DENYLIST)

    def test_every_emitted_name_is_on_the_allowlist(self) -> None:
        contract = CorrectionFeatureContract()
        vector = CorrectionEncoder(_bounds()).encode(_features())

        assert not any(contract.rejects(name) for name in vector.names)

    def test_a_contract_that_forbids_an_emitted_field_refuses_the_encoding(self) -> None:
        """The check is executable, not a comment: narrow the contract and encoding fails."""
        narrow = CorrectionFeatureContract(allowlist=("problem_domain",))
        encoder = CorrectionEncoder(_bounds(), contract=narrow)

        with pytest.raises(CorrectionEncodingError, match="not on the fitted-feature allowlist"):
            encoder.encode(_features())

    def test_identical_inputs_produce_identical_bytes(self) -> None:
        encoder = CorrectionEncoder(_bounds())

        assert (
            encoder.encode(_features()).content_hash() == encoder.encode(_features()).content_hash()
        )

    def test_a_different_candidate_produces_different_bytes(self) -> None:
        encoder = CorrectionEncoder(_bounds())

        assert (
            encoder.encode(_features()).content_hash()
            != encoder.encode(_features(hunk_count=9)).content_hash()
        )

    def test_missing_values_are_counted_rather_than_defaulted(self) -> None:
        encoder = CorrectionEncoder(_bounds())
        present = dict(encoder.encode(_features()).values)
        absent = dict(encoder.encode(_features(missing=("ast_node_count",))).values)

        assert present["missing_value_indicators"] == 0.0
        assert absent["missing_value_indicators"] == 1.0


class TestNumericBoundsComeFromTrainingOnly:
    def test_bounds_cannot_be_fitted_on_nothing(self) -> None:
        with pytest.raises(CorrectionEncodingError, match="empty corpus"):
            NumericBounds.from_training([])

    def test_a_value_above_the_training_range_is_clipped(self) -> None:
        bounds = NumericBounds.from_training([dict.fromkeys(NUMERIC_FEATURE_NAMES, 10.0)])

        assert bounds.scale("hunk_count", 10_000) == 0.0

    def test_scaling_maps_the_training_range_onto_the_unit_interval(self) -> None:
        bounds = NumericBounds(
            lower=dict.fromkeys(NUMERIC_FEATURE_NAMES, 0.0),
            upper=dict.fromkeys(NUMERIC_FEATURE_NAMES, 10.0),
        )

        assert bounds.scale("hunk_count", 5) == 0.5

    def test_the_parameters_are_serialisable_for_the_artifact(self) -> None:
        canonical = _bounds().canonical()

        assert set(canonical["lower"]) == set(NUMERIC_FEATURE_NAMES)
        assert set(canonical["upper"]) == set(NUMERIC_FEATURE_NAMES)


class TestTheRankerAbstainsRatherThanGuessing:
    def test_no_exemplars_means_abstention_and_the_baseline_order(self) -> None:
        encoder = CorrectionEncoder(_bounds())
        candidates = {"a": _vector(encoder, (1.0, 0.0, 0.0, 0.0))}

        ranking = CorrectionKnn().rank(candidates, baseline_order=("a",))

        assert ranking.abstained
        assert ranking.reason == "no_exemplars"
        assert ranking.ordered_candidate_ids == ("a",)

    def test_a_query_far_from_every_exemplar_abstains(self) -> None:
        encoder = CorrectionEncoder(_bounds())
        exemplar = Exemplar(vector=_vector(encoder, (1.0, 0.0, 0.0, 0.0)), accepted=True)
        ranker = CorrectionKnn([exemplar], similarity_floor=Decimal("0.99"))
        candidates = {"a": _vector(encoder, (0.0, 0.0, 0.0, 1.0))}

        ranking = ranker.rank(candidates, baseline_order=("a",))

        assert ranking.abstained
        assert ranking.reason == "below_similarity_floor"

    def test_an_abstention_carries_zero_confidence(self) -> None:
        encoder = CorrectionEncoder(_bounds())
        candidates = {"a": _vector(encoder, (1.0, 0.0, 0.0, 0.0))}

        ranking = CorrectionKnn().rank(candidates, baseline_order=("a",))

        assert ranking.confidence == Decimal("0")
        assert ranking.first_choice == "a"

    def test_a_confident_ranking_is_not_an_abstention(self) -> None:
        encoder = CorrectionEncoder(_bounds())
        accepted = _vector(encoder, (1.0, 0.0, 0.0, 0.0))
        ranker = CorrectionKnn(
            [Exemplar(vector=accepted, accepted=True)],
            k=1,
            similarity_floor=Decimal("0"),
            agreement_floor=Decimal("0"),
            confidence_floor=Decimal("0"),
        )

        ranking = ranker.rank({"a": accepted}, baseline_order=("a",))

        assert not ranking.abstained
        assert ranking.reason == "ranked"


class TestTiesFallBackToTheFrozenBaseline:
    def test_identical_candidates_keep_the_baseline_order(self) -> None:
        """Not candidate-ID order: the ranker may not see identity, so it may not sort by it."""
        encoder = CorrectionEncoder(_bounds())
        same = _vector(encoder, (1.0, 0.0, 0.0, 0.0))
        ranker = CorrectionKnn(
            [Exemplar(vector=same, accepted=True)],
            k=1,
            similarity_floor=Decimal("0"),
            agreement_floor=Decimal("0"),
            confidence_floor=Decimal("0"),
        )
        candidates = {"z": same, "a": same, "m": same}

        forward = ranker.rank(candidates, baseline_order=("z", "a", "m"))
        reversed_baseline = ranker.rank(candidates, baseline_order=("m", "a", "z"))

        assert forward.ordered_candidate_ids == ("z", "a", "m")
        assert reversed_baseline.ordered_candidate_ids == ("m", "a", "z")

    def test_a_baseline_order_that_disagrees_with_the_candidates_is_refused(self) -> None:
        encoder = CorrectionEncoder(_bounds())

        with pytest.raises(CorrectionEncodingError, match="disagree"):
            CorrectionKnn().rank(
                {"a": _vector(encoder, (1.0, 0.0, 0.0, 0.0))}, baseline_order=("a", "b")
            )

    def test_ranking_is_deterministic_across_repeated_calls(self) -> None:
        encoder = CorrectionEncoder(_bounds())
        near = _vector(encoder, (1.0, 0.0, 0.0, 0.0))
        far = _vector(encoder, (0.0, 1.0, 0.0, 0.0))
        ranker = CorrectionKnn(
            [Exemplar(vector=near, accepted=True), Exemplar(vector=far, accepted=False)],
            k=2,
            similarity_floor=Decimal("0"),
            agreement_floor=Decimal("0"),
            confidence_floor=Decimal("0"),
        )
        candidates = {"first": near, "second": far}

        first = ranker.rank(candidates, baseline_order=("first", "second"))
        second = ranker.rank(candidates, baseline_order=("first", "second"))

        assert first.ordered_candidate_ids == second.ordered_candidate_ids
        assert first.confidence == second.confidence


class TestTheRankerIsBoundedAndDeclaresItself:
    def test_its_settings_are_reportable_for_the_artifact(self) -> None:
        settings = CorrectionKnn(k=7).settings

        assert settings["k"] == 7
        assert "embedding_weight" in settings
        assert "similarity_floor" in settings

    @pytest.mark.parametrize("k", [0, -1])
    def test_a_nonsense_k_is_refused(self, k: int) -> None:
        with pytest.raises(ValueError, match="k must be at least 1"):
            CorrectionKnn(k=k)

    @pytest.mark.parametrize(
        "field", ["embedding_weight", "similarity_floor", "agreement_floor", "confidence_floor"]
    )
    def test_a_threshold_outside_the_unit_interval_is_refused(self, field: str) -> None:
        with pytest.raises(ValueError, match="proportion"):
            CorrectionKnn(**{field: Decimal("1.5")})  # type: ignore[arg-type]

    def test_exemplars_are_immutable_once_given(self) -> None:
        encoder = CorrectionEncoder(_bounds())
        exemplars = [Exemplar(vector=_vector(encoder, (1.0, 0.0, 0.0, 0.0)), accepted=True)]
        ranker = CorrectionKnn(exemplars)
        exemplars.clear()

        assert ranker.size == 1

    def test_comparing_differently_encoded_vectors_is_refused(self) -> None:
        """A silent dimension mismatch would make similarity meaningless rather than wrong."""
        encoder = CorrectionEncoder(_bounds())
        narrow = CorrectionEncoder(_bounds()).encode(_features())
        broken = narrow.__class__(
            encoder_version=narrow.encoder_version,
            values=narrow.values[:-1],
            embedding=narrow.embedding,
        )
        ranker = CorrectionKnn([Exemplar(vector=broken, accepted=True)])

        with pytest.raises(CorrectionEncodingError, match="encoded differently"):
            ranker.rank({"a": encoder.encode(_features())}, baseline_order=("a",))
