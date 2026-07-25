"""The two-sided counterfactual, and the difference between impossible and absent.

Settling the `useful` question needed both halves. The contract now refuses `useful` for a
monotone variation, so the class cannot be quietly reported as empty when it was never
reachable; and this variation is genuinely two-sided, so the class is reachable where a
three-valued label is actually wanted.

What the corpus then shows is a *good* property rather than a defect: `useful` stays at zero
because the governed selector never picks a losing skill, so there is nothing to improve on.
That is the system working, and it is a different fact from the one the old tripwire
recorded.
"""

import pytest

from cognitive_os.domain.learned import (
    CounterfactualLabelValue,
    CounterfactualVariation,
    ProvenanceClass,
)
from cognitive_os.domains.fixtures import build_all_cases
from cognitive_os.domains.registry import resolve
from cognitive_os.domains.skill_runner import skill_fixture_bundle
from cognitive_os.learning.replacement import (
    build_replacement_corpus,
    label_case_by_replacement,
)
from cognitive_os.learning.selfplay import SURFACE

CASES = build_all_cases()
PHYSICS = next(case for case in CASES if case.domain.value == "physics")
MATHEMATICS = next(case for case in CASES if case.domain.value == "mathematics")


class TestVariationIsTwoSided:
    def test_replacement_is_not_a_monotone_restriction(self) -> None:
        assert not CounterfactualVariation.SELECTION_REPLACED.monotone_restriction
        assert CounterfactualVariation.SELECTION_FORCED.monotone_restriction
        assert CounterfactualVariation.CANDIDATE_REMOVED.monotone_restriction

    @pytest.mark.asyncio
    async def test_the_corpus_reports_useful_as_structurally_reachable(self) -> None:
        """Reachable is a property of the variation, not of how many were observed."""
        corpus = await build_replacement_corpus(cases=CASES[:4])
        assert corpus.useful_is_reachable

    @pytest.mark.asyncio
    async def test_every_label_compares_against_one_baseline_selection(self) -> None:
        bundle = await skill_fixture_bundle()
        labels = await label_case_by_replacement(MATHEMATICS, bundle)
        assert labels
        assert len({item.determinism_proof for item in labels}) == 1
        for item in labels:
            assert item.surface == SURFACE
            assert item.variation_kind is CounterfactualVariation.SELECTION_REPLACED
            assert item.provenance_class is ProvenanceClass.SELF_PLAY

    @pytest.mark.asyncio
    async def test_the_alternative_is_never_the_baseline_itself(self) -> None:
        """Comparing a choice against itself would manufacture neutral labels."""
        bundle = await skill_fixture_bundle()
        labels = await label_case_by_replacement(PHYSICS, bundle)
        permitted = resolve(PHYSICS.problem_type).skills
        identities = {item.variation_identity for item in labels}
        assert identities
        assert identities < set(permitted), "the baseline's own skill must be excluded"

    @pytest.mark.asyncio
    async def test_labelling_is_reproducible(self) -> None:
        first = await build_replacement_corpus(cases=CASES[:3])
        second = await build_replacement_corpus(cases=CASES[:3])
        assert [item.content_hash for item in first.labels] == [
            item.content_hash for item in second.labels
        ]


class TestMeasuredCorpus:
    @pytest.mark.asyncio
    async def test_an_unselectable_alternative_is_recorded_as_harmful(self) -> None:
        """Forcing a skill the governed path refuses means the task cannot proceed.

        `cross-domain-result-review` requires `generic.exact_value`, which no mathematics
        case emits, so it is not selectable. Dropping such a pair would hide a real
        consequence from the corpus.
        """
        bundle = await skill_fixture_bundle()
        labels = await label_case_by_replacement(MATHEMATICS, bundle)
        review = next(
            item for item in labels if item.variation_identity == "cross-domain-result-review"
        )
        assert review.label is CounterfactualLabelValue.HARMFUL
        assert review.baseline_outcome == "accepted"
        assert review.varied_outcome == "rejected"

    @pytest.mark.asyncio
    async def test_an_equally_capable_alternative_is_neutral(self) -> None:
        """Both physics skills declare `physics.dimension`, so swapping changes nothing."""
        bundle = await skill_fixture_bundle()
        labels = await label_case_by_replacement(PHYSICS, bundle)
        assert all(item.label is CounterfactualLabelValue.NEUTRAL for item in labels)

    @pytest.mark.asyncio
    async def test_useful_stays_absent_because_the_selector_does_not_err(self) -> None:
        """The honest reading of an empty class, distinguished from impossibility.

        `useful` requires the selector to have chosen a skill that fails while an
        alternative succeeds. It does not, so the class is empty — and if this ever stops
        being true, the selector has started making a mistake worth investigating.
        """
        corpus = await build_replacement_corpus()
        assert corpus.useful_is_reachable, "the variation permits it"
        assert corpus.balance.useful == 0, "the selector never picked a loser"
        assert corpus.balance.harmful > 0
        assert corpus.balance.neutral > 0
        assert corpus.cases_without_alternative == ()

    @pytest.mark.asyncio
    async def test_the_corpus_covers_every_case_with_one_alternative_each(self) -> None:
        corpus = await build_replacement_corpus()
        assert corpus.case_count == len(CASES)
        assert len(corpus.labels) == len(CASES)
        assert corpus.balance.total == len(corpus.labels)
