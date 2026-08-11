"""The containment contrastive linear ranker — the class the D6 stop's measurement implies.

D4 stopped on `hypothesis_class_bound` and D5 answered it with a class that fits within-group
contrast over the sealed 390-channel representation. D6 varied only the admission rule over
that class's margin and still stopped: no threshold at any coverage satisfies the amended
§2.3 pair, so the binding constraint is the ranker's fresh-corpus error rate, not the bar.
The §4 transfer measurement locates the non-transferring part: the direction's first-choice
rate drops 0.88 → 0.76 across authoring runs while `fixed_input_order` holds at 0.42 on both,
and a scalar-only refit reproduces the same 0.76 — the 384 embedding channels of the
canonical source carry the corpus, not the task. What transfers is structure: the six v2
scalars, and the repair-containment share `repair_containment.py` derives from the group
package itself.

This class fits the same pairwise-contrastive rule D5 froze — every within-group
accepted-minus-rejected difference, one ridge-regularised logistic direction, rank by
projection, confide only in the top-two margin — over a seven-channel relational
representation: the six sealed v2 scalars plus `repair_containment_share`. The solver, the
regulariser, the tie-break and the abstention rule are byte-for-byte the released ones; what
changed is which numbers describe a candidate, and that is exactly the change
`pairwise_contrastive.HYPOTHESIS_CLASS`'s own comment prices: a different feature set is a
different class wearing a new name.

Three boundaries, carried unchanged from the released classes:

**Nothing that answers the question enters the vector.** The six scalars come out of the
sealed v2 feature records unchanged; the containment share reads only pre-outcome sources
published to the solver. No label, verifier output, outcome, identity or requirement-text
relation reaches a channel — the last exclusion is load-bearing, because a requirement
relation is the one channel class that moves under the frozen rename cases.

**Ties break on the baseline, never on identity.**

**Abstention is a real answer**, and admission stays the conformal bar's job: the margin
floor here decides only whether the ranker answers at all, and the operating point over the
margin is derived by `conformal_operating_point.derive_conformal_point` from calibration
evidence, never chosen by this module.

What this module deliberately does not do: it does not freeze a `CorrectionFeatureContractV3`.
The successor sprint's W0 must pre-register the seven-channel allowlist, the class name below
and one alpha before any fresh outcome exists; a contract frozen here, next to the diagnostic
that motivated it, would let the measurement pick its own gate. The class is importable and
fittable so the wave can exercise it; the contract belongs to the pre-registration.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from math import isfinite

from cognitive_os.learning.correction_protocol import FITTED_FEATURE_V2_SCALARS
from cognitive_os.learning.correction_ranking import (
    CorrectionEncodingError,
    CorrectionRanking,
)
from cognitive_os.learning.repair_containment import (
    REPAIR_CONTAINMENT_CHANNEL,
    containment_shares,
)

#: The class identity a pre-registration names. A different channel set, pairing rule,
#: regulariser or solver is a different class wearing this one's name — bump the version.
HYPOTHESIS_CLASS = "containment-contrastive-linear-v1"

#: The relational representation this class is defined over: the six sealed v2 scalars and
#: the group-derived containment share, in this exact order. Not an encoder version — the
#: scalars are read out of sealed v2 records rather than re-encoded, and the share needs no
#: bounds because it lives in [0, 1] by construction.
FITTED_RELATIONAL_CHANNELS: tuple[str, ...] = (
    *FITTED_FEATURE_V2_SCALARS,
    REPAIR_CONTAINMENT_CHANNEL,
)

#: The fitting rule, stated once and stored beside every fitted model.
FIT_RULE = (
    "assemble each candidate's seven relational channels — the six sealed v2 scalars "
    "unchanged, then the repair-containment share computed from the group's baseline and "
    "candidate sources; collect every within-group accepted-minus-rejected channel "
    "difference over the declared fitting groups in sorted group order; fit one linear "
    "direction by ridge-regularised logistic regression on the antisymmetric pair set (no "
    "intercept, zero start, Newton iterations to convergence); rank a group's candidates by "
    "their projection onto the direction with ties broken on the baseline order; the "
    "decision's confidence is the projection margin between the top two candidates"
)


class ContainmentFitError(ValueError):
    """The fitting inputs cannot produce a direction without violating the rule."""


def relational_numbers(
    sealed_scalars_by_candidate: Mapping[str, Sequence[tuple[str, float]]],
    *,
    baseline_source: str,
    sources_by_candidate: Mapping[str, str],
) -> dict[str, tuple[float, ...]]:
    """Each candidate's seven channels, assembled from sealed values and the group package.

    The scalar half is taken from the sealed v2 records by name so a drifted or reordered
    record fails here rather than silently feeding a direction numbers under wrong names.
    """
    if set(sealed_scalars_by_candidate) != set(sources_by_candidate):
        raise CorrectionEncodingError("the sealed records and the group sources disagree")
    shares = containment_shares(baseline_source, sources_by_candidate)
    numbers: dict[str, tuple[float, ...]] = {}
    for candidate_id, values in sealed_scalars_by_candidate.items():
        names = tuple(name for name, _ in values)
        if names != FITTED_FEATURE_V2_SCALARS:
            raise CorrectionEncodingError(
                "a relational vector is assembled from the exact six sealed v2 scalars"
            )
        numbers[candidate_id] = (
            *(float(value) for _, value in values),
            shares[candidate_id],
        )
    return numbers


@dataclass(frozen=True, slots=True)
class RelationalGroup:
    """One fitting group: the frozen order, seven channels and one label per candidate."""

    group: str
    order: tuple[str, ...]
    numbers: Mapping[str, tuple[float, ...]]
    accepted: Mapping[str, bool]

    def __post_init__(self) -> None:
        if set(self.order) != set(self.numbers) or set(self.order) != set(self.accepted):
            raise ContainmentFitError(f"group {self.group!r} names disagree across its parts")
        for candidate_id in self.order:
            if len(self.numbers[candidate_id]) != len(FITTED_RELATIONAL_CHANNELS):
                raise ContainmentFitError(
                    f"group {self.group!r} carries a vector off the relational channel set"
                )


@dataclass(frozen=True, slots=True)
class ContainmentContrastiveModel:
    """One fitted direction, everything it was fitted under, and its sealed identity."""

    channel_names: tuple[str, ...]
    weights: tuple[float, ...]
    regularization: str
    fitted_group_count: int
    fitted_pair_count: int

    def __post_init__(self) -> None:
        if self.channel_names != FITTED_RELATIONAL_CHANNELS:
            raise ContainmentFitError("a direction of this class names the seven channels")
        if len(self.weights) != len(self.channel_names):
            raise ContainmentFitError("a direction names one weight per fitted channel")
        if any(not isfinite(weight) for weight in self.weights):
            raise ContainmentFitError("a fitted direction must be finite")
        if Decimal(self.regularization) <= 0:
            raise ContainmentFitError("the ridge term must be positive; zero is a different class")
        if self.fitted_group_count < 1 or self.fitted_pair_count < 1:
            raise ContainmentFitError("a direction fitted on no pairs is a guess")

    def canonical_bytes(self) -> bytes:
        parts = [HYPOTHESIS_CLASS, self.regularization]
        parts += [f"g={self.fitted_group_count}", f"p={self.fitted_pair_count}"]
        parts += [
            f"{name}={weight:.12g}"
            for name, weight in zip(self.channel_names, self.weights, strict=True)
        ]
        return "\n".join(parts).encode()

    def content_hash(self) -> str:
        return sha256(self.canonical_bytes()).hexdigest()

    def score(self, numbers: Sequence[float]) -> float:
        """The projection of one relational vector onto the direction. Pure Python on
        purpose: inference must not need the fitting extra."""
        if len(numbers) != len(self.weights):
            raise CorrectionEncodingError("candidate and direction dimensions disagree")
        return sum(weight * value for weight, value in zip(self.weights, numbers, strict=True))


def fit_containment_direction(
    groups: Sequence[RelationalGroup],
    *,
    regularization: Decimal,
    max_iterations: int = 60,
    tolerance: float = 1e-8,
) -> ContainmentContrastiveModel:
    """Fit the direction on within-group differences. Fitting only — never at inference.

    The solver is the released one, kept line for line: numpy is imported here rather than
    at module top so a minimal lane can import the ranker for inference without it.
    """
    if regularization <= 0:
        raise ContainmentFitError("the ridge term must be positive; zero is a different class")
    try:
        import numpy
    except ImportError as error:  # pragma: no cover - exercised only in minimal lanes
        raise ContainmentFitError(
            "fitting requires numpy; install the 'semantic-graph' extra"
        ) from error

    differences: list[tuple[float, ...]] = []
    counted_groups = 0
    for group in sorted(groups, key=lambda item: item.group):
        accepted = [item for item in group.order if group.accepted[item]]
        rejected = [item for item in group.order if not group.accepted[item]]
        if not accepted or not rejected:
            raise ContainmentFitError(
                "every fitting group must carry at least one accepted and one rejected "
                "candidate; a one-sided group contributes no within-group contrast"
            )
        counted_groups += 1
        for winner in accepted:
            for loser in rejected:
                differences.append(
                    tuple(
                        left - right
                        for left, right in zip(
                            group.numbers[winner], group.numbers[loser], strict=True
                        )
                    )
                )
    if not differences:
        raise ContainmentFitError("no fitting group was given")

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

    return ContainmentContrastiveModel(
        channel_names=FITTED_RELATIONAL_CHANNELS,
        weights=tuple(float(item) for item in weights),
        regularization=str(regularization),
        fitted_group_count=counted_groups,
        fitted_pair_count=len(differences),
    )


class ContainmentContrastiveRanker:
    """Rank one group by projection onto a fitted direction; confide only in the margin."""

    component_id = "learned.containment.correction_ranking"
    surface = "experience.correction_ranking"

    def __init__(
        self,
        model: ContainmentContrastiveModel,
        *,
        margin_floor: Decimal = Decimal("0"),
    ) -> None:
        if margin_floor < 0:
            raise ValueError("a negative margin floor admits decisions the model disowns")
        self._model = model
        self._margin_floor = margin_floor

    @property
    def model(self) -> ContainmentContrastiveModel:
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
        numbers_by_candidate: Mapping[str, Sequence[float]],
        *,
        baseline_order: Sequence[str],
    ) -> CorrectionRanking:
        """Order `baseline_order` by projection, or abstain below the margin floor.

        `confidence` carries the margin, not an acceptance probability, exactly as the
        released ranker's does: the operating-point derivation treats a confidence as an
        opaque ordered score, which is the only property the margin needs.
        """
        if set(baseline_order) != set(numbers_by_candidate):
            raise CorrectionEncodingError("the baseline order and the candidate set disagree")
        if len(baseline_order) < 2:
            raise CorrectionEncodingError("a ranking needs at least two candidates")

        scores = {
            candidate_id: self._model.score(numbers_by_candidate[candidate_id])
            for candidate_id in baseline_order
        }
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
