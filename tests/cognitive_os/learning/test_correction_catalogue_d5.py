"""S21D5-023: the D5 seal holds what the contracts said it would, and refuses what it must.

D5's seal inherits D4's failure modes -- a role quietly re-derived instead of carried, a replica
counted as an independent decision, a seal written with the authoring capability still open --
and adds two of its own, both from the volume arm.

A volume point that does not land on a whole group puts three of a group's candidates in the
exemplar set and the fourth in the evaluation, then calls the difference a volume effect. And a
retrieval pool that is D4's spent one measures recall of an answer that has already been read.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from cognitive_os.learning.correction_catalogue_d4 import seal_d4_corpus
from cognitive_os.learning.correction_catalogue_d5 import (
    CARRIED_ROLES,
    D5_CASES,
    INVARIANCE_SAMPLE_GROUPS,
    SealedD5Corpus,
    d5_invariance_sample_groups,
    seal_d5_corpus,
)
from cognitive_os.learning.correction_protocol import CorrectionPartition

EVIDENCE = Path(__file__).resolve().parents[3] / "docs/sprints/sprint-21/evidence"
D4_SEALED = EVIDENCE / "sprint-21d4-sealed-manifests.json"


def test_the_seal_is_deterministic() -> None:
    """Same corpora and seeds, same hashes. A seal that moves cannot be restarted against."""
    assert seal_d5_corpus().seal.content_hash == seal_d5_corpus().seal.content_hash


def test_every_role_is_the_size_the_contracts_froze() -> None:
    seal = seal_d5_corpus().seal
    assert seal.fitting_groups == 180
    assert seal.calibration_groups == 100
    assert seal.final_a_groups == 30
    assert seal.final_b_groups == 30
    assert seal.canary_groups == 5
    assert seal.retrieval_source_groups == 60


def test_the_fitting_role_is_d4s_two_spent_partitions() -> None:
    """S21D5-011's composition is 80 D4 fitting plus 100 D4 calibration groups. Those are two
    released partitions, so nothing is chosen here and nothing is authored."""
    fitting = seal_d5_corpus().groups_of(CorrectionPartition.TRAINING)
    d4 = seal_d4_corpus()
    assert len(fitting) == 180
    assert d4.groups_of(CorrectionPartition.TRAINING) <= fitting
    assert d4.groups_of(CorrectionPartition.CALIBRATION) <= fitting


def test_the_fitting_pool_is_re_interleaved_rather_than_concatenated() -> None:
    """Concatenating the two partitions would put D4's calibration groups entirely after D4's
    fitting ones, and the 320-outcome volume point would then read one sprint's corpus."""
    catalogue = seal_d5_corpus().catalogues[CorrectionPartition.TRAINING]
    first_eighty = {group.repository_group for group in catalogue.groups[:80]}
    d4 = seal_d4_corpus()
    assert first_eighty & d4.groups_of(CorrectionPartition.TRAINING)
    assert first_eighty & d4.groups_of(CorrectionPartition.CALIBRATION)


@pytest.mark.parametrize("partition", CARRIED_ROLES)
def test_a_protected_role_is_the_hash_d4_released(
    partition: CorrectionPartition,
) -> None:
    """Not merely equal to a re-derivation: equal to the bytes the released evidence carries."""
    bundle = seal_d5_corpus()
    released = json.loads(D4_SEALED.read_text())["catalogues"][partition.value]["content_hash"]
    assert bundle.catalogues[partition].content_hash == released
    assert bundle.reused_from_d4[partition] == released


def test_no_group_is_in_two_roles() -> None:
    bundle = seal_d5_corpus()
    roles = {partition.value: bundle.groups_of(partition) for partition in bundle.catalogues}
    roles["retrieval"] = bundle.retrieval_groups
    names = sorted(roles)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            assert not roles[left] & roles[right], f"{left} and {right} share a group"


def test_the_retrieval_pool_is_not_the_one_d4_spent() -> None:
    bundle = seal_d5_corpus()
    d4 = seal_d4_corpus()
    assert bundle.retrieval_pool.content_hash != d4.retrieval_pool.content_hash
    assert not bundle.retrieval_groups & d4.retrieval_groups


def test_the_invariance_sample_adds_no_independent_decision() -> None:
    seal = seal_d5_corpus().seal
    assert seal.invariance_transformed_decisions == 40
    assert seal.invariance_independent_decisions == 0


def test_the_promotion_set_reports_both_counts() -> None:
    seal = seal_d5_corpus().seal
    assert seal.promotion_nominal_decisions == 120
    assert seal.promotion_independent_decisions == 60
    assert seal.promotion_nominal_decisions == seal.promotion_independent_decisions * len(D5_CASES)


def test_the_promotion_cases_do_not_collide_with_d4s() -> None:
    """Same sixty groups and the same two released cases, so the seed is all that separates the
    two sets of case identities. If it did not, D5 would be re-scoring D4's promotion set."""
    d5 = {case.case_id for case in seal_d5_corpus().promotion_transformations.cases}
    d4 = {case.case_id for case in seal_d4_corpus().promotion_transformations.cases}
    assert len(d5) == len(d4) == 120
    assert not d5 & d4


def test_the_invariance_sample_is_the_first_twenty_of_the_sealed_manifest() -> None:
    """A rule that can be checked against the catalogue afterwards, not a choice made later."""
    bundle = seal_d5_corpus()
    calibration = bundle.catalogues[CorrectionPartition.CALIBRATION]
    sample = d5_invariance_sample_groups()
    assert len(sample) == INVARIANCE_SAMPLE_GROUPS
    assert list(sample) == [group.repository_group for group in calibration.groups[:20]]
    assert {case.source_group_id for case in bundle.invariance_transformations.cases} == set(sample)


def test_both_submanifests_use_the_released_generator() -> None:
    """A D5 restatement of the transformation generator would be a second oracle."""
    bundle = seal_d5_corpus()
    invariance = bundle.invariance_transformations
    promotion = bundle.promotion_transformations
    assert invariance.generator_code_hash == promotion.generator_code_hash
    assert invariance.hard_coded_oracle_hash == promotion.hard_coded_oracle_hash
    for submanifest in (invariance, promotion):
        assert {case.case_name for case in submanifest.cases} == set(D5_CASES)
        assert submanifest.fitted is False


def _body_without(field: str, value: object) -> dict[str, object]:
    body = seal_d5_corpus().seal.model_dump(mode="json", exclude={"content_hash"})
    body[field] = value
    return body


def test_a_seal_carrying_an_outcome_is_refused() -> None:
    with pytest.raises(ValidationError, match="carries an outcome"):
        SealedD5Corpus.model_validate(_body_without("outcomes_present", True))


def test_a_seal_leaving_corpus_authoring_open_is_refused() -> None:
    with pytest.raises(ValidationError, match="closes corpus authoring"):
        SealedD5Corpus.model_validate(_body_without("corpus_authoring_capability_revoked", False))


def test_a_seal_counting_a_replica_as_independent_is_refused() -> None:
    with pytest.raises(ValidationError):
        SealedD5Corpus.model_validate(_body_without("invariance_independent_decisions", 40))


def test_a_promotion_count_that_does_not_halve_is_refused() -> None:
    with pytest.raises(ValidationError, match="twice its independent"):
        SealedD5Corpus.model_validate(_body_without("promotion_independent_decisions", 120))


def test_a_volume_point_inside_a_group_is_refused() -> None:
    """322 outcomes is eighty groups and half of an eighty-first."""
    with pytest.raises(ValidationError, match="whole group"):
        SealedD5Corpus.model_validate(_body_without("volume_points", [322, 720]))


def test_a_top_volume_point_short_of_the_pool_is_refused() -> None:
    """A ladder whose top rung is not the whole fitting pool measures a span nobody declared."""
    with pytest.raises(ValidationError, match="whole fitting pool"):
        SealedD5Corpus.model_validate(_body_without("volume_points", [320, 640]))


def test_a_seal_re_reading_the_spent_retrieval_pool_is_refused() -> None:
    seal = seal_d5_corpus().seal
    with pytest.raises(ValidationError, match="pool D4 already read"):
        SealedD5Corpus.model_validate(
            _body_without("spent_retrieval_pool_hash", seal.retrieval_pool_hash)
        )


def test_no_catalogue_carries_an_outcome() -> None:
    bundle = seal_d5_corpus()
    for catalogue in bundle.catalogues.values():
        assert catalogue.outcomes_present is False
    assert bundle.retrieval_pool.outcomes_present is False
    assert bundle.retrieval_pool.queries_resolved is False
