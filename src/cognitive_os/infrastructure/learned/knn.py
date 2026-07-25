"""Tier A: weighted k-nearest-neighbour over stored counterfactual experience.

First in the plan's trial order, because catastrophic forgetting is impossible by
construction: learning is an append, so nothing is overwritten and nothing can be
destroyed. The k neighbours are the explanation, so interpretability is free.

Needs no optional extra. Similarity is Jaccard overlap over the categorical situation
encoding, computed in pure Python — 969 stored labels compare in microseconds, and
adding `numpy` to the core dependency set to avoid a set intersection would be a poor
trade.

**Two honest limitations, both measured rather than supposed.**

On the skill-selection corpus this component reaches 1.000 on a group-aware split while
the majority class reaches 0.567. That looks like a decisive win and is not one: the
correct deterministic rule also reaches 1.000, so the component ties a two-line subset
test. `BaselineLadder` exists to make that visible.

Held out one domain at a time it reaches only 0.737, and at the default threshold it
answers confidently while being wrong, because Jaccard overlap stays high on
`problem_type` and `candidate` even when the capability vocabulary is completely
disjoint. `neighbour_agreement` is therefore part of confidence, not just distance —
distance alone cannot see that its neighbours disagree.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from cognitive_os.domain.learned import (
    LearnedArtifactFormat,
    LearnedCapabilityClass,
    LearnedComponentDescriptor,
    LearnedComponentTier,
    LearnedExplanationKind,
    LearnedPrediction,
    LearnedResourceClass,
    SituationVector,
)
from cognitive_os.domains.fixtures import FIXTURE_TIME
from cognitive_os.learning.features import categorical_pairs

#: Below this similarity there is no neighbourhood, so there is nothing to vote.
DEFAULT_SIMILARITY_FLOOR = Decimal("0.50")

#: Confidence combines similarity with how much the neighbours agreed. Pure distance
#: cannot detect an out-of-distribution query whose neighbours are split.
DEFAULT_CONFIDENCE_FLOOR = Decimal("0.50")


@dataclass(frozen=True, slots=True)
class StoredExperience:
    """One remembered outcome. Append-only by construction."""

    situation: SituationVector
    label: str


@dataclass(frozen=True, slots=True)
class KnnHealth:
    available: bool
    reason: str


@dataclass(frozen=True, slots=True)
class Neighbour:
    label: str
    similarity: Decimal


class ExperienceKnn:
    """Non-parametric component: remember, then vote."""

    component_id = "learned.knn.skill_selection"

    def __init__(
        self,
        experience: tuple[StoredExperience, ...] = (),
        *,
        k: int = 3,
        similarity_floor: Decimal = DEFAULT_SIMILARITY_FLOOR,
        confidence_floor: Decimal = DEFAULT_CONFIDENCE_FLOOR,
    ) -> None:
        if k < 1:
            raise ValueError("k must be at least 1")
        self._experience = experience
        self._k = k
        self._similarity_floor = similarity_floor
        self._confidence_floor = confidence_floor

    def remember(self, *items: StoredExperience) -> ExperienceKnn:
        """Return a component with more experience; never mutates what is stored.

        Revision is an append, exactly as Sprint 10's bitemporal claim semantics treat a
        corrected belief. This is the property that makes forgetting structurally
        impossible for this tier.
        """
        return ExperienceKnn(
            self._experience + items,
            k=self._k,
            similarity_floor=self._similarity_floor,
            confidence_floor=self._confidence_floor,
        )

    @property
    def size(self) -> int:
        return len(self._experience)

    @property
    def descriptor(self) -> LearnedComponentDescriptor:
        return LearnedComponentDescriptor(
            component_id=self.component_id,
            version="1",
            surface="skill.selection",
            tier=LearnedComponentTier.NON_PARAMETRIC,
            capability_class=LearnedCapabilityClass.DISCRIMINATIVE,
            resource_class=LearnedResourceClass.CPU,
            required_extra=None,
            artifact_format=LearnedArtifactFormat.NONE,
            supports_abstention=True,
            explanation_kind=LearnedExplanationKind.NEIGHBOURS,
            deterministic_baseline="skills.selection.requirements_available",
            declared_limitations=(
                "ties the deterministic requirements-available rule on this corpus rather "
                "than beating it: measured 1.000 against the same 1.000",
                "reaches only 0.737 on a held-out domain, because the capability vocabulary "
                "of an unseen domain never appears in stored experience",
            ),
        )

    async def health_check(self) -> KnnHealth:
        if not self._experience:
            return KnnHealth(available=False, reason="no stored experience yet")
        return KnnHealth(available=True, reason=f"{self.size} stored outcomes")

    def neighbours(self, situation: SituationVector) -> tuple[Neighbour, ...]:
        probe = categorical_pairs(situation)
        if not probe:
            return ()
        scored = [
            Neighbour(
                label=item.label,
                similarity=Decimal(len(probe & categorical_pairs(item.situation)))
                / Decimal(len(probe)),
            )
            for item in self._experience
        ]
        # Sorted by similarity, then by label so equal neighbours order deterministically.
        scored.sort(key=lambda item: (-item.similarity, item.label))
        return tuple(scored[: self._k])

    def _vote(self, neighbours: tuple[Neighbour, ...]) -> tuple[str, Decimal, Decimal]:
        votes = Counter(item.label for item in neighbours)
        winner, count = votes.most_common(1)[0]
        agreement = Decimal(count) / Decimal(len(neighbours))
        return winner, agreement, neighbours[0].similarity

    async def predict(self, situation: SituationVector) -> LearnedPrediction:
        prediction_id = uuid5(
            NAMESPACE_URL, f"{self.component_id}:{situation.content_hash}:{self.size}"
        )
        neighbours = self.neighbours(situation)
        top = neighbours[0].similarity if neighbours else Decimal(0)
        if not neighbours or top < self._similarity_floor:
            return LearnedPrediction(
                prediction_id=prediction_id,
                component_id=self.component_id,
                situation=situation,
                confidence=Decimal(0),
                abstained=True,
                explanation=(
                    f"nearest stored experience scored {top}, below the {self._similarity_floor} "
                    "floor, so the deterministic path decides",
                ),
                created_at=FIXTURE_TIME,
            )
        winner, agreement, similarity = self._vote(neighbours)
        confidence = similarity * agreement
        if confidence < self._confidence_floor:
            return LearnedPrediction(
                prediction_id=prediction_id,
                component_id=self.component_id,
                situation=situation,
                confidence=confidence,
                abstained=True,
                explanation=(
                    f"{len(neighbours)} neighbours agreed only {agreement} at similarity "
                    f"{similarity}, so the deterministic path decides",
                ),
                created_at=FIXTURE_TIME,
            )
        return LearnedPrediction(
            prediction_id=prediction_id,
            component_id=self.component_id,
            situation=situation,
            prediction=winner,
            confidence=confidence,
            abstained=False,
            explanation=tuple(
                f"neighbour {item.label} at similarity {item.similarity}" for item in neighbours
            ),
            created_at=FIXTURE_TIME,
        )
