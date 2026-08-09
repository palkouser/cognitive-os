"""The pairwise contrastive linear ranker — the hypothesis class D4's stop asked for.

S21D4-039 stopped with `hypothesis_class_bound`: the frozen k-NN ranks above the strongest
deterministic baseline everywhere and cannot separate its own errors anywhere. Its confidence
is the top candidate's absolute neighbourhood acceptance mass, and a correction-ranking
decision is not an absolute question. The four candidates of a group are deliberate
near-clones, so every one of them sits in roughly the same neighbourhood and the score that
decides admission barely moves between a right ordering and a wrong one. Zero-error coverage
was exactly zero at both volumes because the signal admission reads carries almost no
information about the only thing that can be wrong: the within-group order.

This class fits the within-group question directly. Every fitting group contributes its
accepted-minus-rejected feature differences, a single linear direction is fitted on those
differences by ridge-regularised logistic regression, candidates are ranked by their
projection onto the direction, and the decision's confidence is the **margin** — the
projection gap between the top two candidates. A small margin says the model itself cannot
tell its first choice from its runner-up, which is precisely the decision a selective ranker
must decline.

Three boundaries, inherited from the released ranker rather than invented here:

**Nothing that answers the question enters the vector.** The class fits on
`CorrectionFeatureVector.fitted_numbers` — the sealed v2 channels, unchanged. No new encoder,
no new channel, no re-embedding.

**Ties break on the baseline, never on identity.** Equal projections keep the deterministic
order the campaign froze, exactly as `CorrectionKnn.rank` does.

**Abstention is a real answer.** Below the margin floor the ranker declines and the caller
runs the deterministic order. The floor itself is an operating point derived by
`derive_zero_error_point` from calibration evidence, never chosen by this module.

The fit is deterministic by construction — Newton iterations on a strictly convex objective
from a zero start, no sampling, no data-order dependence (the pair set is built in sorted
group order) — but bit-identity across BLAS builds is not assumed: a fitted model is sealed
by `content_hash` and consumers compare hashes rather than refitting, the same discipline
W2-D9 forced on the MiniLM vectors.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from math import isfinite

from cognitive_os.learning.correction_ranking import (
    CorrectionEncodingError,
    CorrectionRanking,
    Exemplar,
)

#: The class identity a pre-registration names. A different feature set, pairing rule,
#: regulariser or solver is a different class wearing this one's name — bump the version.
HYPOTHESIS_CLASS = "pairwise-contrastive-linear-v1"

#: The fitting rule, stated once and stored beside every fitted model. §3.4 of the D4
#: backlog permits recommending a class on the measured residual; this sentence is the class.
FIT_RULE = (
    "collect every within-group accepted-minus-rejected difference of fitted feature vectors "
    "over the declared fitting groups in sorted group order; fit one linear direction by "
    "ridge-regularised logistic regression on the antisymmetric pair set (no intercept, zero "
    "start, Newton iterations to convergence); rank a group's candidates by their projection "
    "onto the direction with ties broken on the baseline order; the decision's confidence is "
    "the projection margin between the top two candidates"
)


class PairwiseFitError(ValueError):
    """The fitting inputs cannot produce a direction without violating the rule."""


@dataclass(frozen=True, slots=True)
class PairwiseContrastiveModel:
    """One fitted direction, everything it was fitted under, and its sealed identity."""

    encoder_version: str
    feature_names: tuple[str, ...]
    weights: tuple[float, ...]
    regularization: str
    fitted_group_count: int
    fitted_pair_count: int

    def __post_init__(self) -> None:
        if len(self.weights) != len(self.feature_names):
            raise PairwiseFitError("a direction names one weight per fitted feature")
        if not self.weights:
            raise PairwiseFitError("an empty direction ranks nothing")
        if any(not isfinite(weight) for weight in self.weights):
            raise PairwiseFitError("a fitted direction must be finite")
        if Decimal(self.regularization) <= 0:
            raise PairwiseFitError("the ridge term must be positive; zero is a different class")
        if self.fitted_group_count < 1 or self.fitted_pair_count < 1:
            raise PairwiseFitError("a direction fitted on no pairs is a guess")

    def canonical_bytes(self) -> bytes:
        parts = [HYPOTHESIS_CLASS, self.encoder_version, self.regularization]
        parts += [f"g={self.fitted_group_count}", f"p={self.fitted_pair_count}"]
        parts += [
            f"{name}={weight:.12g}"
            for name, weight in zip(self.feature_names, self.weights, strict=True)
        ]
        return "\n".join(parts).encode()

    def content_hash(self) -> str:
        return sha256(self.canonical_bytes()).hexdigest()

    def score(self, numbers: Sequence[float]) -> float:
        """The projection of one fitted vector onto the direction. Pure Python on purpose:
        inference must not need the fitting extra."""
        if len(numbers) != len(self.weights):
            raise CorrectionEncodingError("candidate and direction dimensions disagree")
        return sum(weight * value for weight, value in zip(self.weights, numbers, strict=True))


def fit_pairwise_direction(
    groups: Sequence[Sequence[Exemplar]],
    *,
    regularization: Decimal,
    max_iterations: int = 60,
    tolerance: float = 1e-8,
) -> PairwiseContrastiveModel:
    """Fit the direction on within-group differences. Fitting only — never at inference.

    numpy comes from the `semantic-graph` extra the learned lanes already install; it is
    imported here rather than at module top so that importing the ranker for inference or
    collection in a minimal lane cannot fail on it, which is the lesson W7-F2 cost a CI
    round trip to learn.
    """
    if regularization <= 0:
        raise PairwiseFitError("the ridge term must be positive; zero is a different class")
    try:
        import numpy
    except ImportError as error:  # pragma: no cover - exercised only in minimal lanes
        raise PairwiseFitError(
            "fitting requires numpy; install the 'semantic-graph' extra"
        ) from error

    encoder_version: str | None = None
    feature_names: tuple[str, ...] | None = None
    differences: list[tuple[float, ...]] = []
    counted_groups = 0
    for group in groups:
        accepted = [item for item in group if item.accepted]
        rejected = [item for item in group if not item.accepted]
        if not accepted or not rejected:
            raise PairwiseFitError(
                "every fitting group must carry at least one accepted and one rejected "
                "candidate; a one-sided group contributes no within-group contrast"
            )
        counted_groups += 1
        for item in (*accepted, *rejected):
            if encoder_version is None:
                encoder_version = item.vector.encoder_version
                feature_names = item.vector.fitted_names
            elif (
                item.vector.encoder_version != encoder_version
                or item.vector.fitted_names != feature_names
            ):
                raise CorrectionEncodingError("fitting exemplars were encoded differently")
        for winner in accepted:
            for loser in rejected:
                differences.append(
                    tuple(
                        left - right
                        for left, right in zip(
                            winner.vector.fitted_numbers,
                            loser.vector.fitted_numbers,
                            strict=True,
                        )
                    )
                )
    if not differences or encoder_version is None or feature_names is None:
        raise PairwiseFitError("no fitting group was given")

    matrix = numpy.array(differences, dtype=numpy.float64)
    stacked = numpy.vstack([matrix, -matrix])
    labels = numpy.hstack([numpy.ones(len(matrix)), numpy.zeros(len(matrix))])
    ridge = float(regularization)
    count = len(labels)
    weights = numpy.zeros(stacked.shape[1])
    for _ in range(max_iterations):
        probability = 1.0 / (1.0 + numpy.exp(-stacked @ weights))
        gradient = stacked.T @ (probability - labels) / count + ridge * weights / count
        curvature = probability * (1.0 - probability)
        hessian = (stacked * curvature[:, None]).T @ stacked / count + (
            ridge * numpy.eye(stacked.shape[1]) / count
        )
        step = numpy.linalg.solve(hessian, gradient)
        weights -= step
        if float(numpy.linalg.norm(step)) < tolerance:
            break

    return PairwiseContrastiveModel(
        encoder_version=encoder_version,
        feature_names=feature_names,
        weights=tuple(float(item) for item in weights),
        regularization=str(regularization),
        fitted_group_count=counted_groups,
        fitted_pair_count=len(differences),
    )


class PairwiseContrastiveRanker:
    """Rank one group by projection onto a fitted direction; confide only in the margin."""

    component_id = "learned.pairwise.correction_ranking"
    surface = "experience.correction_ranking"

    def __init__(
        self,
        model: PairwiseContrastiveModel,
        *,
        margin_floor: Decimal = Decimal("0"),
    ) -> None:
        if margin_floor < 0:
            raise ValueError("a negative margin floor admits decisions the model disowns")
        self._model = model
        self._margin_floor = margin_floor

    @property
    def model(self) -> PairwiseContrastiveModel:
        return self._model

    @property
    def margin_floor(self) -> Decimal:
        return self._margin_floor

    @property
    def settings(self) -> dict[str, object]:
        return {
            "hypothesis_class": HYPOTHESIS_CLASS,
            "model_hash": self._model.content_hash(),
            "regularization": self._model.regularization,
            "margin_floor": str(self._margin_floor),
        }

    def rank(
        self,
        candidates: Mapping[str, object],
        *,
        baseline_order: Sequence[str],
    ) -> CorrectionRanking:
        """Order `baseline_order` by projection, or abstain below the margin floor.

        `confidence` carries the margin, not an acceptance probability. The two are
        different quantities and the operating-point derivation treats a confidence as an
        opaque ordered score, which is the only property the margin needs.
        """
        if set(baseline_order) != set(candidates):
            raise CorrectionEncodingError("the baseline order and the candidate set disagree")
        if len(baseline_order) < 2:
            raise CorrectionEncodingError("a ranking needs at least two candidates")

        scores: dict[str, float] = {}
        for candidate_id in baseline_order:
            vector = candidates[candidate_id]
            if getattr(vector, "encoder_version", None) != self._model.encoder_version or (
                getattr(vector, "fitted_names", None) != self._model.feature_names
            ):
                raise CorrectionEncodingError("candidate and direction were encoded differently")
            scores[candidate_id] = self._model.score(vector.fitted_numbers)  # type: ignore[attr-defined]

        position = {candidate_id: index for index, candidate_id in enumerate(baseline_order)}
        ordered = tuple(sorted(baseline_order, key=lambda key: (-scores[key], position[key])))
        margin = Decimal(str(round(scores[ordered[0]] - scores[ordered[1]], 6)))
        if margin < self._margin_floor:
            return CorrectionRanking(
                ordered_candidate_ids=tuple(baseline_order),
                confidence=Decimal("0"),
                abstained=True,
                reason="below_margin_floor",
                explanations={},
            )
        return CorrectionRanking(
            ordered_candidate_ids=ordered,
            confidence=margin,
            abstained=False,
            reason="ranked",
            explanations={},
        )
