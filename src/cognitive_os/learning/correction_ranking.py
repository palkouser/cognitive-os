"""The correction-ranking encoder and the bounded k-NN that ranks with it.

S21D2-040 and S21D2-043. One module, because they are one decision: what a candidate looks
like before it runs, and how similar candidates that already ran are turned into an ordering.

Three properties do the real work, and none of them is about accuracy.

**Nothing that answers the question enters the vector.** The encoder takes provenance and
features as separate arguments and only ever emits the features, so an identity cannot reach
the fitted matrix by being passed to the wrong parameter. Names are checked against
`CorrectionFeatureContract`, which refuses by absence rather than by denylist.

**Ties break on the baseline, never on identity.** Two candidates with equal scores keep the
deterministic order the campaign already froze. Breaking ties on candidate ID would make the
ranker's output depend on a value it is forbidden to see.

**Abstention is a real answer.** Below the similarity floor, the neighbour-agreement floor or
the confidence floor, the ranker declines and the caller runs the deterministic order. An
abstention is a fallback, never a changed decision and never a correct prediction.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from math import sqrt

from cognitive_os.learning.correction_protocol import CorrectionFeatureContract

#: The bounded numeric features, in the fixed order the artifact records them. Adding one is a
#: new encoder version, because an exemplar fitted under a different order is a different
#: exemplar wearing the same numbers.
NUMERIC_FEATURE_NAMES: tuple[str, ...] = (
    "changed_file_count",
    "hunk_count",
    "added_line_count",
    "removed_line_count",
    "ast_node_count",
    "graph_node_count",
    "graph_edge_count",
    "graph_path_length",
)

ENCODER_VERSION = "correction-ranking-v1"


class CorrectionEncodingError(ValueError):
    """The inputs cannot be encoded without violating the feature contract."""


@dataclass(frozen=True, slots=True)
class CandidateProvenance:
    """Identity. Recorded in manifests and lineage; never passed to the encoder's output.

    A separate object rather than fields on the feature input, because the boundary that
    matters is the one a careless edit could cross. Merging them would make a leak a typo.
    """

    candidate_id: str
    task_id: str
    group: str
    recipe: str


@dataclass(frozen=True, slots=True)
class CorrectionFeatureInput:
    """Everything the encoder may legitimately see, all of it available before execution."""

    problem_domain: str
    declared_problem_type: str
    task_requirement_embedding: tuple[float, ...]
    candidate_delta_embedding: tuple[float, ...]
    changed_file_count: int
    hunk_count: int
    added_line_count: int
    removed_line_count: int
    ast_node_count: int
    graph_node_count: int
    graph_edge_count: int
    graph_path_length: int
    declared_verifier_capabilities: tuple[str, ...] = ()
    #: Names whose source was absent. Explicit, so a missing count is distinguishable from a
    #: zero count — they mean different things and a model that conflates them is guessing.
    missing: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class NumericBounds:
    """Clip-and-scale parameters, fitted on training only and stored in the artifact.

    Fitting them on anything wider would let calibration or holdout statistics reach the
    encoder, which is a leak that no feature-name check would ever catch.
    """

    lower: Mapping[str, float]
    upper: Mapping[str, float]

    @classmethod
    def from_training(cls, rows: Sequence[Mapping[str, float]]) -> NumericBounds:
        if not rows:
            raise CorrectionEncodingError("numeric bounds cannot be fitted on an empty corpus")
        lower = {name: min(row[name] for row in rows) for name in NUMERIC_FEATURE_NAMES}
        upper = {name: max(row[name] for row in rows) for name in NUMERIC_FEATURE_NAMES}
        return cls(lower=lower, upper=upper)

    def scale(self, name: str, value: float) -> float:
        """Clip into the training range, then map to [0, 1]. A constant feature maps to 0."""
        low, high = self.lower[name], self.upper[name]
        clipped = min(max(float(value), low), high)
        return 0.0 if high == low else (clipped - low) / (high - low)

    def canonical(self) -> dict[str, dict[str, float]]:
        return {
            "lower": {name: self.lower[name] for name in NUMERIC_FEATURE_NAMES},
            "upper": {name: self.upper[name] for name in NUMERIC_FEATURE_NAMES},
        }


@dataclass(frozen=True, slots=True)
class CorrectionFeatureVector:
    """One encoded candidate. Carries no identity, by construction rather than by review."""

    encoder_version: str
    #: `(name, value)` in a fixed order, so two vectors are comparable elementwise.
    values: tuple[tuple[str, float], ...]
    #: The two normalised text channels, weighted explicitly so a raw count cannot dominate.
    embedding: tuple[float, ...]

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self.values)

    @property
    def numbers(self) -> tuple[float, ...]:
        return tuple(value for _, value in self.values)

    def canonical_bytes(self) -> bytes:
        parts = [self.encoder_version]
        parts += [f"{name}={value:.6f}" for name, value in self.values]
        parts += [f"e{index}={value:.6f}" for index, value in enumerate(self.embedding)]
        return "\n".join(parts).encode()

    def content_hash(self) -> str:
        return sha256(self.canonical_bytes()).hexdigest()


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise CorrectionEncodingError("cannot compare vectors of different dimension")
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm = sqrt(sum(a * a for a in left)) * sqrt(sum(b * b for b in right))
    return dot / norm if norm else 0.0


class CorrectionEncoder:
    """Turns a task and one candidate into the vector the ranker may fit on."""

    version = ENCODER_VERSION

    def __init__(
        self,
        bounds: NumericBounds,
        *,
        contract: CorrectionFeatureContract | None = None,
    ) -> None:
        self._bounds = bounds
        self._contract = contract or CorrectionFeatureContract()

    def encode(self, features: CorrectionFeatureInput) -> CorrectionFeatureVector:
        """Encode one candidate. `CandidateProvenance` is deliberately not a parameter."""
        raw = {name: float(getattr(features, name)) for name in NUMERIC_FEATURE_NAMES}
        values: list[tuple[str, float]] = [
            (name, self._bounds.scale(name, raw[name])) for name in NUMERIC_FEATURE_NAMES
        ]
        values.append(
            (
                "query_to_candidate_cosine",
                _cosine(features.task_requirement_embedding, features.candidate_delta_embedding),
            )
        )
        # Missing-value indicators are features in their own right, not silent defaults.
        values.append(("missing_value_indicators", float(len(features.missing))))
        values.append(
            ("declared_verifier_capabilities", float(len(features.declared_verifier_capabilities)))
        )

        for name, _ in values:
            if self._contract.rejects(name):
                raise CorrectionEncodingError(
                    f"{name!r} is not on the fitted-feature allowlist for "
                    f"{self._contract.encoder_version}"
                )

        return CorrectionFeatureVector(
            encoder_version=self.version,
            values=tuple(values),
            embedding=tuple(features.candidate_delta_embedding),
        )


@dataclass(frozen=True, slots=True)
class Exemplar:
    """One fitted training example: what it looked like, and what the verifier said."""

    vector: CorrectionFeatureVector
    accepted: bool


@dataclass(frozen=True, slots=True)
class NeighbourExplanation:
    similarity: float
    accepted: bool


@dataclass(frozen=True, slots=True)
class CorrectionRanking:
    """An ordering, or a refusal to produce one.

    `abstained` is not a failure mode: it is the answer the contract asks for when the
    evidence is too thin, and the caller runs the deterministic order instead.
    """

    ordered_candidate_ids: tuple[str, ...]
    confidence: Decimal
    abstained: bool
    reason: str
    explanations: Mapping[str, tuple[NeighbourExplanation, ...]]

    @property
    def first_choice(self) -> str | None:
        return self.ordered_candidate_ids[0] if self.ordered_candidate_ids else None


class CorrectionKnn:
    """Bounded cosine k-NN over frozen exemplars. Pure Python, no default dependency."""

    component_id = "learned.knn.correction_ranking"
    surface = "experience.correction_ranking"

    def __init__(
        self,
        exemplars: Sequence[Exemplar] = (),
        *,
        k: int = 5,
        embedding_weight: Decimal = Decimal("0.7"),
        similarity_floor: Decimal = Decimal("0.30"),
        agreement_floor: Decimal = Decimal("0.60"),
        confidence_floor: Decimal = Decimal("0.55"),
    ) -> None:
        if k < 1:
            raise ValueError("k must be at least 1")
        for name, value in (
            ("embedding_weight", embedding_weight),
            ("similarity_floor", similarity_floor),
            ("agreement_floor", agreement_floor),
            ("confidence_floor", confidence_floor),
        ):
            if not Decimal("0") <= value <= Decimal("1"):
                raise ValueError(f"{name} must be a proportion in [0, 1]")
        self._exemplars = tuple(exemplars)
        self._k = k
        self._embedding_weight = float(embedding_weight)
        self._similarity_floor = similarity_floor
        self._agreement_floor = agreement_floor
        self._confidence_floor = confidence_floor

    @property
    def size(self) -> int:
        return len(self._exemplars)

    @property
    def k(self) -> int:
        return self._k

    @property
    def embedding_weight(self) -> Decimal:
        return Decimal(str(self._embedding_weight))

    @property
    def similarity_floor(self) -> Decimal:
        return self._similarity_floor

    @property
    def agreement_floor(self) -> Decimal:
        return self._agreement_floor

    @property
    def confidence_floor(self) -> Decimal:
        return self._confidence_floor

    @property
    def settings(self) -> dict[str, object]:
        return {
            "k": self._k,
            "embedding_weight": str(self._embedding_weight),
            "similarity_floor": str(self._similarity_floor),
            "agreement_floor": str(self._agreement_floor),
            "confidence_floor": str(self._confidence_floor),
        }

    def _score(
        self, vector: CorrectionFeatureVector
    ) -> tuple[float, tuple[NeighbourExplanation, ...]]:
        """Acceptance probability from the k nearest exemplars, plus why."""
        scored = sorted(
            ((self._similarity(vector, item.vector), item.accepted) for item in self._exemplars),
            key=lambda pair: -pair[0],
        )[: self._k]
        if not scored:
            return 0.0, ()
        explanations = tuple(
            NeighbourExplanation(similarity=similarity, accepted=accepted)
            for similarity, accepted in scored
        )
        weight = sum(similarity for similarity, _ in scored)
        if weight <= 0:
            return 0.0, explanations
        positive = sum(similarity for similarity, accepted in scored if accepted)
        return positive / weight, explanations

    def _similarity(self, left: CorrectionFeatureVector, right: CorrectionFeatureVector) -> float:
        """Two channels, explicitly weighted, so raw counts cannot dominate the embedding.

        §4.4 requires the weighting to be frozen before calibration rather than emerging from
        whatever scale the counts happen to have.
        """
        if left.names != right.names:
            raise CorrectionEncodingError("exemplar and query were encoded differently")
        text = _cosine(left.embedding, right.embedding)
        static = _cosine(left.numbers, right.numbers)
        return self._embedding_weight * text + (1.0 - self._embedding_weight) * static

    def rank(
        self,
        candidates: Mapping[str, CorrectionFeatureVector],
        *,
        baseline_order: Sequence[str],
    ) -> CorrectionRanking:
        """Order `baseline_order` by predicted acceptance, or abstain and leave it alone.

        `baseline_order` is both the tie-break and the fallback. Ties broken on candidate ID
        would make the output depend on a value the ranker may not see; ties broken on
        insertion order would make it depend on how the caller built a dict.
        """
        if set(baseline_order) != set(candidates):
            raise CorrectionEncodingError("the baseline order and the candidate set disagree")
        if not self._exemplars:
            return self._abstain(baseline_order, "no_exemplars", {})

        position = {candidate_id: index for index, candidate_id in enumerate(baseline_order)}
        scores: dict[str, float] = {}
        explanations: dict[str, tuple[NeighbourExplanation, ...]] = {}
        best_similarity = 0.0
        for candidate_id in baseline_order:
            score, neighbours = self._score(candidates[candidate_id])
            scores[candidate_id] = score
            explanations[candidate_id] = neighbours
            best_similarity = max(
                best_similarity, max((item.similarity for item in neighbours), default=0.0)
            )

        if Decimal(str(best_similarity)) < self._similarity_floor:
            return self._abstain(baseline_order, "below_similarity_floor", explanations)

        top = explanations[max(scores, key=lambda key: (scores[key], -position[key]))]
        if top:
            majority = max(
                sum(1 for item in top if item.accepted), sum(1 for item in top if not item.accepted)
            )
            if Decimal(majority) / Decimal(len(top)) < self._agreement_floor:
                return self._abstain(baseline_order, "neighbours_disagree", explanations)

        ordered = tuple(sorted(baseline_order, key=lambda key: (-scores[key], position[key])))
        confidence = Decimal(str(round(scores[ordered[0]], 6)))
        if confidence < self._confidence_floor:
            return self._abstain(baseline_order, "below_confidence_floor", explanations)
        return CorrectionRanking(
            ordered_candidate_ids=ordered,
            confidence=confidence,
            abstained=False,
            reason="ranked",
            explanations=explanations,
        )

    @staticmethod
    def _abstain(
        baseline_order: Sequence[str],
        reason: str,
        explanations: Mapping[str, tuple[NeighbourExplanation, ...]],
    ) -> CorrectionRanking:
        return CorrectionRanking(
            ordered_candidate_ids=tuple(baseline_order),
            confidence=Decimal("0"),
            abstained=True,
            reason=reason,
            explanations=explanations,
        )
