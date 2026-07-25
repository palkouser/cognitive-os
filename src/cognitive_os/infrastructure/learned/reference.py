"""Reference learned components: the seam's own proof that it fits more than one shape.

Neither of these is a useful model. They exist because a seam validated against a
single implementation is shaped to that implementation: two components with
different capability classes, artifact formats, explanation kinds, and abstention
behaviour keep the boundary honest.

`AlwaysAbstainingRanker` is the shape a real Tier A component will have — a ranking
component with neighbour explanations that abstains below a confidence floor.
`ConstantClassifier` is deliberately different: discriminative, joblib-backed,
feature-attribution explanations, and it never abstains, which is exactly why the
registry must refuse to activate it.
"""

from __future__ import annotations

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


@dataclass(frozen=True, slots=True)
class ReferenceHealth:
    available: bool
    reason: str


class AlwaysAbstainingRanker:
    """A ranking component that always abstains, so the baseline always decides."""

    component_id = "reference.ranker.abstaining"

    @property
    def descriptor(self) -> LearnedComponentDescriptor:
        return LearnedComponentDescriptor(
            component_id=self.component_id,
            version="1",
            surface="skill.selection",
            tier=LearnedComponentTier.NON_PARAMETRIC,
            capability_class=LearnedCapabilityClass.RANKING,
            resource_class=LearnedResourceClass.CPU,
            required_extra=None,
            artifact_format=LearnedArtifactFormat.NONE,
            supports_abstention=True,
            explanation_kind=LearnedExplanationKind.NEIGHBOURS,
            deterministic_baseline="skills.selection.specificity_scope_statistics",
            declared_limitations=(
                "reference component: abstains unconditionally and learns nothing",
            ),
        )

    async def health_check(self) -> ReferenceHealth:
        return ReferenceHealth(available=True, reason="reference component is always available")

    async def predict(self, situation: SituationVector) -> LearnedPrediction:
        return LearnedPrediction(
            prediction_id=uuid5(NAMESPACE_URL, f"{self.component_id}:{situation.content_hash}"),
            component_id=self.component_id,
            situation=situation,
            confidence=Decimal(0),
            abstained=True,
            explanation=("no stored experience, so the deterministic baseline decides",),
            created_at=FIXTURE_TIME,
        )


class ConstantClassifier:
    """A differently shaped component that never abstains, so it is unpromotable."""

    component_id = "reference.classifier.constant"

    @property
    def descriptor(self) -> LearnedComponentDescriptor:
        return LearnedComponentDescriptor(
            component_id=self.component_id,
            version="1",
            surface="acceptance.prediction",
            tier=LearnedComponentTier.INCREMENTAL_PARAMETRIC,
            capability_class=LearnedCapabilityClass.DISCRIMINATIVE,
            resource_class=LearnedResourceClass.CPU_PREFERRED,
            required_extra="learned-baseline",
            artifact_format=LearnedArtifactFormat.JOBLIB,
            supports_abstention=False,
            explanation_kind=LearnedExplanationKind.FEATURE_ATTRIBUTION,
            deterministic_baseline="acceptance.always_verify",
            declared_limitations=("reference component: predicts one constant and cannot abstain",),
        )

    async def health_check(self) -> ReferenceHealth:
        return ReferenceHealth(available=True, reason="reference component is always available")

    async def predict(self, situation: SituationVector) -> LearnedPrediction:
        return LearnedPrediction(
            prediction_id=uuid5(NAMESPACE_URL, f"{self.component_id}:{situation.content_hash}"),
            component_id=self.component_id,
            situation=situation,
            prediction="accepted",
            confidence=Decimal("0.5"),
            abstained=False,
            explanation=("constant prediction; no feature contributed",),
            created_at=FIXTURE_TIME,
        )
