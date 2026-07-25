"""Sprint 21A: the self-play counterfactual labelling harness."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from cognitive_os.domain.learned import (
    CounterfactualLabel,
    CounterfactualLabelValue,
    CounterfactualVariation,
    ProvenanceClass,
)
from cognitive_os.domains.fixtures import FIXTURE_TIME, build_all_cases
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
async def test_this_variation_is_monotone_so_useful_is_impossible_not_merely_absent() -> None:
    """Replaces a tripwire that was watching for something that could not happen.

    The earlier version asserted `useful == 0` and explained it as a property of the
    fixtures: every baseline is accepted, so forcing a candidate can only break things.
    Measurement in 21B showed the stronger fact. `SELECTION_FORCED` *adds* a required
    capability, which only ever adds a conjunct to the acceptance criterion, so a rejected
    baseline can never be repaired by it. No corpus could produce `useful` here, and a
    tripwire watching for the impossible would never have fired.

    The impossibility is now in the contract, so this test asserts that instead — and
    `learning/replacement.py` provides the two-sided variation for the cases where a
    three-valued label is genuinely wanted.
    """
    corpus = await build_corpus(case_limit=5)
    assert corpus.balance.useful == 0
    assert corpus.balance.neutral > 0
    assert corpus.balance.harmful > 0
    assert CounterfactualVariation.SELECTION_FORCED.monotone_restriction
    assert all(
        label.variation_kind is CounterfactualVariation.SELECTION_FORCED for label in corpus.labels
    )


def test_a_monotone_variation_cannot_be_recorded_as_useful() -> None:
    """The impossibility is a type error now, not a corpus observation."""
    with pytest.raises(ValidationError, match="cannot yield a useful label"):
        CounterfactualLabel(
            label_id=uuid4(),
            surface=SURFACE,
            case_id="domain-truth-table",
            variation_kind=CounterfactualVariation.SELECTION_FORCED,
            variation_identity="logic-formalization",
            baseline_outcome="rejected",
            varied_outcome="accepted",
            label=CounterfactualLabelValue.USEFUL,
            determinism_proof="d" * 64,
            provenance_class=ProvenanceClass.SELF_PLAY,
            created_at=FIXTURE_TIME,
        )


def test_the_two_sided_variation_accepts_a_useful_label() -> None:
    """`SELECTION_REPLACED` is two-sided, so all three classes are representable."""
    label = CounterfactualLabel(
        label_id=uuid4(),
        surface=SURFACE,
        case_id="domain-truth-table",
        variation_kind=CounterfactualVariation.SELECTION_REPLACED,
        variation_identity="constraint-solving",
        baseline_outcome="rejected",
        varied_outcome="accepted",
        label=CounterfactualLabelValue.USEFUL,
        determinism_proof="d" * 64,
        provenance_class=ProvenanceClass.SELF_PLAY,
        created_at=FIXTURE_TIME,
    )
    assert label.label is CounterfactualLabelValue.USEFUL
    assert not label.variation_kind.monotone_restriction


def test_balance_of_an_empty_label_set_is_not_degenerate() -> None:
    assert balance_of(()).degenerate is False
    assert balance_of(()).total == 0
