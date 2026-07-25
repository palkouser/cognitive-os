"""Sprint 21A: the self-play counterfactual labelling harness."""

import pytest

from cognitive_os.domain.learned import (
    CounterfactualLabelValue,
    CounterfactualVariation,
    ProvenanceClass,
)
from cognitive_os.domains.fixtures import build_all_cases
from cognitive_os.learning.selfplay import (
    SURFACE,
    balance_of,
    build_corpus,
    label_case,
    skill_candidates,
)

CASES = build_all_cases()


@pytest.mark.asyncio
async def test_every_seed_skill_is_a_candidate_with_its_declared_capabilities() -> None:
    candidates = await skill_candidates()
    assert len(candidates) == 19
    names = [item.canonical_name for item in candidates]
    assert names == sorted(names), "candidate order must be deterministic"
    declared = {item.canonical_name: item.declared_capabilities for item in candidates}
    assert declared["exact-arithmetic-decomposition"] == ("mathematics.exact_arithmetic",)
    assert declared["evidence-collection"] == ()


@pytest.mark.asyncio
async def test_labels_are_causal_and_bound_to_their_baseline() -> None:
    candidates = await skill_candidates()
    labels = await label_case(CASES[0], candidates)
    assert len(labels) == len(candidates)
    proofs = {item.determinism_proof for item in labels}
    assert len(proofs) == 1, "every label compares against one baseline run"
    for item in labels:
        assert item.surface == SURFACE
        assert item.variation_kind is CounterfactualVariation.SELECTION_FORCED
        assert item.provenance_class is ProvenanceClass.SELF_PLAY
        # The contract's own validator already enforces this; asserting it here
        # keeps the harness honest if the contract is ever relaxed.
        unchanged = item.baseline_outcome == item.varied_outcome
        assert (item.label is CounterfactualLabelValue.NEUTRAL) is unchanged


@pytest.mark.asyncio
async def test_labelling_is_reproducible() -> None:
    candidates = await skill_candidates()
    first = await label_case(CASES[0], candidates)
    second = await label_case(CASES[0], candidates)
    assert [item.content_hash for item in first] == [item.content_hash for item in second]


@pytest.mark.asyncio
async def test_a_matching_and_a_mismatched_capability_get_different_labels() -> None:
    """The signal the surface exists for: a declared verifier that never runs."""
    case = next(item for item in CASES if item.problem_type == "long-multiplication")
    candidates = await skill_candidates()
    labels = {item.variation_identity: item.label for item in await label_case(case, candidates)}
    assert labels["exact-arithmetic-decomposition"] is CounterfactualLabelValue.NEUTRAL
    # Declared, applicable, ties on specificity — and never exercised here.
    assert labels["symbolic-equivalence-checking"] is CounterfactualLabelValue.HARMFUL


@pytest.mark.asyncio
async def test_a_bounded_corpus_is_not_degenerate() -> None:
    corpus = await build_corpus(case_limit=3)
    assert corpus.case_count == 3
    assert corpus.candidate_count == 19
    assert len(corpus.labels) == 3 * 19
    assert corpus.run_count == 3 * 20
    assert not corpus.balance.degenerate, "a single-class corpus carries no signal"
    assert corpus.balance.total == len(corpus.labels)


@pytest.mark.asyncio
async def test_useful_is_unreachable_while_the_baseline_always_succeeds() -> None:
    """An honest property of this corpus, asserted so a future change is noticed.

    Every fixture case is accepted at baseline, so forcing a candidate can only
    leave the outcome unchanged or break it. The three-valued label is therefore
    binary in practice here. A corpus whose baseline can fail would reach
    `USEFUL`, and this test is the tripwire that says so.
    """
    corpus = await build_corpus(case_limit=5)
    assert corpus.balance.useful == 0
    assert corpus.balance.neutral > 0
    assert corpus.balance.harmful > 0


def test_balance_of_an_empty_label_set_is_not_degenerate() -> None:
    assert balance_of(()).degenerate is False
    assert balance_of(()).total == 0
