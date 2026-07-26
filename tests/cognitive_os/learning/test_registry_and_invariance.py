"""Sprint 21A: the extension seam's registry and its defining invariance gate."""

import pytest

from cognitive_os.domain.learned import LearnedComponentState
from cognitive_os.domains.fixtures import build_all_cases
from cognitive_os.infrastructure.learned.reference import (
    AlwaysAbstainingRanker,
    ConstantClassifier,
)
from cognitive_os.learning.invariance import decision_digest, verify_invariance
from cognitive_os.learning.registry import (
    LearnedComponentRegistry,
    LearnedComponentRegistryError,
)

CASES = build_all_cases()
#: A bounded prefix: the gate's property does not depend on corpus size, and the
#: full sweep belongs in the benchmark suite rather than in a unit test.
SAMPLE = CASES[:4]


def registry_with(*components: object) -> LearnedComponentRegistry:
    registry = LearnedComponentRegistry()
    for component in components:
        registry.register(component)  # type: ignore[arg-type]
    return registry


class TestRegistry:
    def test_a_frozen_registry_refuses_new_components(self) -> None:
        registry = registry_with(AlwaysAbstainingRanker())
        registry.freeze()
        assert registry.frozen
        with pytest.raises(LearnedComponentRegistryError, match="frozen"):
            registry.register(ConstantClassifier())

    def test_duplicate_registration_is_refused(self) -> None:
        registry = registry_with(AlwaysAbstainingRanker())
        with pytest.raises(LearnedComponentRegistryError, match="duplicate"):
            registry.register(AlwaysAbstainingRanker())

    def test_an_unknown_component_is_refused(self) -> None:
        with pytest.raises(LearnedComponentRegistryError, match="unknown"):
            LearnedComponentRegistry().state("nope")

    def test_absence_is_a_first_class_state(self) -> None:
        """The normal case: no component, and the deterministic path is unchanged."""
        registry = LearnedComponentRegistry()
        registry.freeze()
        assert registry.component_ids() == ()
        assert registry.active_for("skill.selection") is None

    def test_lifecycle_follows_the_declared_transitions(self) -> None:
        component = AlwaysAbstainingRanker()
        registry = registry_with(component)
        assert registry.state(component.component_id) is LearnedComponentState.REGISTERED
        registry.transition(component.component_id, LearnedComponentState.SHADOW)
        registry.transition(component.component_id, LearnedComponentState.VERIFIED)
        registry.transition(component.component_id, LearnedComponentState.ACTIVE)
        assert registry.active_for("skill.selection") is component

    def test_skipping_shadow_is_refused(self) -> None:
        component = AlwaysAbstainingRanker()
        registry = registry_with(component)
        with pytest.raises(LearnedComponentRegistryError, match="illegal"):
            registry.transition(component.component_id, LearnedComponentState.ACTIVE)

    def test_retraction_is_terminal(self) -> None:
        component = AlwaysAbstainingRanker()
        registry = registry_with(component)
        registry.transition(component.component_id, LearnedComponentState.RETRACTED)
        with pytest.raises(LearnedComponentRegistryError, match="illegal"):
            registry.transition(component.component_id, LearnedComponentState.SHADOW)

    def test_a_component_that_cannot_abstain_cannot_be_activated(self) -> None:
        component = ConstantClassifier()
        registry = registry_with(component)
        registry.transition(component.component_id, LearnedComponentState.SHADOW)
        registry.transition(component.component_id, LearnedComponentState.VERIFIED)
        with pytest.raises(LearnedComponentRegistryError, match="cannot abstain"):
            registry.transition(component.component_id, LearnedComponentState.ACTIVE)

    def test_two_differently_shaped_components_share_the_seam(self) -> None:
        """A seam proven by one implementation is shaped to that implementation."""
        ranker, classifier = AlwaysAbstainingRanker(), ConstantClassifier()
        registry = registry_with(ranker, classifier)
        registry.freeze()
        assert registry.component_ids() == (
            "reference.classifier.constant",
            "reference.ranker.abstaining",
        )
        first, second = ranker.descriptor, classifier.descriptor
        assert first.capability_class is not second.capability_class
        assert first.artifact_format is not second.artifact_format
        assert first.explanation_kind is not second.explanation_kind
        assert first.supports_abstention is not second.supports_abstention
        assert first.surface != second.surface


class TestMandatoryPathInvariance:
    @pytest.mark.asyncio
    async def test_the_deterministic_digest_is_reproducible(self) -> None:
        assert await decision_digest(SAMPLE) == await decision_digest(SAMPLE)

    @pytest.mark.asyncio
    async def test_the_digest_distinguishes_different_case_sets(self) -> None:
        assert await decision_digest(SAMPLE) != await decision_digest(SAMPLE[:2])

    @pytest.mark.asyncio
    async def test_a_component_cannot_alter_the_deterministic_path(self) -> None:
        component = AlwaysAbstainingRanker()
        registry = registry_with(component)
        record = await verify_invariance(component.component_id, registry, cases=SAMPLE)
        assert record.identical, "absent, disabled, and abstaining must decide identically"
        assert record.case_count == len(SAMPLE)

    @pytest.mark.asyncio
    async def test_the_gate_drives_the_real_lifecycle(self) -> None:
        """A component that cannot be disabled must fail the gate, not pass a mock."""
        component = AlwaysAbstainingRanker()
        registry = registry_with(component)
        registry.transition(component.component_id, LearnedComponentState.RETRACTED)
        with pytest.raises(LearnedComponentRegistryError, match="illegal"):
            await verify_invariance(component.component_id, registry, cases=SAMPLE)

    @pytest.mark.asyncio
    async def test_an_empty_case_set_is_refused(self) -> None:
        component = AlwaysAbstainingRanker()
        with pytest.raises(ValueError, match="at least one case"):
            await verify_invariance(component.component_id, registry_with(component), cases=())
