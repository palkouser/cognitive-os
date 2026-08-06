"""S21D4-032: the D4 seal holds what the contracts said it would, and refuses what it must.

The seal is a one-way door: after it, the corpus is spent rather than editable. These tests are
about the three ways a door like that fails to be one -- a role quietly re-derived instead of
carried, a replica counted as an independent decision, and a seal written with the authoring
capability still open.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from cognitive_os.learning.correction_catalogue_d3 import seal_d3_corpus
from cognitive_os.learning.correction_catalogue_d4 import (
    CARRIED_ROLES,
    D4_CASES,
    INVARIANCE_SAMPLE_GROUPS,
    SealedD4Corpus,
    invariance_sample_groups,
    seal_d4_corpus,
)
from cognitive_os.learning.correction_protocol import CorrectionPartition

EVIDENCE = Path(__file__).resolve().parents[3] / "docs/sprints/sprint-21/evidence"
D3_SEALED = EVIDENCE / "sprint-21d3-sealed-manifests.json"


def test_the_seal_is_deterministic() -> None:
    """Same corpora and seeds, same hashes. A seal that moves cannot be restarted against."""
    assert seal_d4_corpus().seal.content_hash == seal_d4_corpus().seal.content_hash


def test_every_role_is_the_size_the_contracts_froze() -> None:
    seal = seal_d4_corpus().seal
    assert seal.fitting_groups == 80
    assert seal.calibration_groups == 100
    assert seal.final_a_groups == 30
    assert seal.final_b_groups == 30
    assert seal.canary_groups == 5
    assert seal.retrieval_source_groups == 60


def test_the_fitting_role_is_the_three_released_partitions() -> None:
    """The contract's composition is ten D2 calibration, fifty D2 training, twenty D3
    calibration. Those are exactly three released partitions, so nothing is chosen here."""
    bundle = seal_d4_corpus()
    d3 = seal_d3_corpus()
    fitting = bundle.groups_of(CorrectionPartition.TRAINING)
    assert len(fitting) == 80
    assert d3.groups_of(CorrectionPartition.CALIBRATION) <= fitting
    assert d3.groups_of(CorrectionPartition.TRAINING) <= fitting


@pytest.mark.parametrize("partition", CARRIED_ROLES)
def test_a_carried_role_is_the_hash_d3_released(partition: CorrectionPartition) -> None:
    """Not merely equal to a re-derivation: equal to the bytes the released evidence carries."""
    bundle = seal_d4_corpus()
    released = json.loads(D3_SEALED.read_text())["catalogues"][partition.value]["content_hash"]
    assert bundle.catalogues[partition].content_hash == released
    assert bundle.reused_from_d3[partition] == released


def test_no_group_is_in_two_roles() -> None:
    bundle = seal_d4_corpus()
    roles = {partition.value: bundle.groups_of(partition) for partition in bundle.catalogues}
    roles["retrieval"] = bundle.retrieval_groups
    names = sorted(roles)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            assert not roles[left] & roles[right], f"{left} and {right} share a group"


def test_the_invariance_sample_adds_no_independent_decision() -> None:
    """The W1 erratum, in the shape the seal has to carry it.

    Forty transformed decisions over twenty groups, and every one of them repeats its source
    group's fitted feature vector. Counting them would count the same decision twice.
    """
    seal = seal_d4_corpus().seal
    assert seal.invariance_transformed_decisions == 40
    assert seal.invariance_independent_decisions == 0


def test_the_promotion_set_reports_both_counts() -> None:
    seal = seal_d4_corpus().seal
    assert seal.promotion_nominal_decisions == 120
    assert seal.promotion_independent_decisions == 60
    assert seal.promotion_nominal_decisions == seal.promotion_independent_decisions * len(D4_CASES)


def test_the_invariance_sample_is_the_first_twenty_of_the_sealed_manifest() -> None:
    """A rule that can be checked against the catalogue afterwards, not a choice made later."""
    bundle = seal_d4_corpus()
    calibration = bundle.catalogues[CorrectionPartition.CALIBRATION]
    sample = invariance_sample_groups(calibration)
    assert len(sample) == INVARIANCE_SAMPLE_GROUPS
    assert list(sample) == [group.repository_group for group in calibration.groups[:20]]
    named = {case.source_group_id for case in bundle.invariance_transformations.cases}
    assert named == set(sample)


def test_both_submanifests_use_the_released_generator() -> None:
    """A D4 restatement of the transformation generator would be a second oracle."""
    bundle = seal_d4_corpus()
    invariance = bundle.invariance_transformations
    promotion = bundle.promotion_transformations
    assert invariance.generator_code_hash == promotion.generator_code_hash
    assert invariance.hard_coded_oracle_hash == promotion.hard_coded_oracle_hash
    for submanifest in (invariance, promotion):
        assert {case.case_name for case in submanifest.cases} == set(D4_CASES)
        assert submanifest.fitted is False


def test_a_seal_carrying_an_outcome_is_refused() -> None:
    seal = seal_d4_corpus().seal
    body = seal.model_dump(mode="json", exclude={"content_hash"})
    body["outcomes_present"] = True
    with pytest.raises(ValidationError, match="carries an outcome"):
        SealedD4Corpus.model_validate(body)


def test_a_seal_leaving_corpus_authoring_open_is_refused() -> None:
    seal = seal_d4_corpus().seal
    body = seal.model_dump(mode="json", exclude={"content_hash"})
    body["corpus_authoring_capability_revoked"] = False
    with pytest.raises(ValidationError, match="closes corpus authoring"):
        SealedD4Corpus.model_validate(body)


def test_a_seal_counting_a_replica_as_independent_is_refused() -> None:
    seal = seal_d4_corpus().seal
    body = seal.model_dump(mode="json", exclude={"content_hash"})
    body["invariance_independent_decisions"] = 40
    with pytest.raises(ValidationError):
        SealedD4Corpus.model_validate(body)


def test_a_promotion_count_that_does_not_halve_is_refused() -> None:
    """Two cases per group means nominal is exactly twice independent; anything else is a
    counting rule nobody wrote down."""
    seal = seal_d4_corpus().seal
    body = seal.model_dump(mode="json", exclude={"content_hash"})
    body["promotion_independent_decisions"] = 120
    with pytest.raises(ValidationError, match="twice its independent"):
        SealedD4Corpus.model_validate(body)


def test_no_catalogue_carries_an_outcome() -> None:
    bundle = seal_d4_corpus()
    for catalogue in bundle.catalogues.values():
        assert catalogue.outcomes_present is False
    assert bundle.retrieval_pool.outcomes_present is False
    assert bundle.retrieval_pool.queries_resolved is False
