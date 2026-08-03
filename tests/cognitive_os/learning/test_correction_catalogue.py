"""S21D2-022 (seal), -026, -027, -028: what the sealed catalogues must be true of.

Sealing is a one-way door, so these tests are the last place a counting or placement mistake
can be caught cheaply. The one that earns its runtime is the replay: it executes the variant
each slot points at and checks the verdict against what the slot declared. Nothing else
catches a wrong recipe-to-position composition, and a wrong composition would mislabel the
whole campaign while every hash still looked stable.
"""

from __future__ import annotations

import itertools
import os
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

import pytest
from pydantic import ValidationError

from cognitive_os.coding.reality_candidates import candidate_id_for
from cognitive_os.coding.reality_task_specs import TASK_SPECS
from cognitive_os.config.learned_config import LearnedPersistenceConfiguration
from cognitive_os.domain.reality import D2_NEUTRAL_RECIPES, RealityCandidateStrategy
from cognitive_os.learning.correction_catalogue import (
    CANDIDATES_PER_GROUP,
    PARTITION_GENERATOR_PATH,
    PARTITION_GROUP_FLOOR,
    PARTITION_SEED,
    CatalogueGroup,
    CatalogueSlot,
    SealedCorpusBundle,
    SealedPartitionCatalogue,
    corpus_entries,
    seal_corpus,
)
from cognitive_os.learning.correction_protocol import (
    FITTED_FEATURE_ALLOWLIST,
    PARTITION_CORPUS_ROLE,
    PARTITION_PROVENANCE,
    CorrectionCampaignMode,
    CorrectionPartition,
)

EVALUATION_PARTITIONS = (
    CorrectionPartition.FINAL_A,
    CorrectionPartition.FINAL_B,
    CorrectionPartition.CANARY,
)


@pytest.fixture(scope="session")
def bundle() -> SealedCorpusBundle:
    return seal_corpus()


def _execute(job: tuple[str, str, str, str]) -> tuple[str, bool]:
    key, module, text, test_source = job
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / f"{module}.py").write_text(text, encoding="utf-8")
        (root / f"test_{module}.py").write_text(test_source, encoding="utf-8")
        completed = subprocess.run(  # fixed argv, no shell, throwaway directory
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                f"test_{module}.py",
            ],
            cwd=root,
            capture_output=True,
            text=True,
        )
        return key, completed.returncode == 0


@pytest.fixture(scope="session")
def replay(bundle: SealedCorpusBundle) -> Iterator[dict[str, bool]]:
    """Execute the hidden verifier against the variant every sealed slot points at."""
    from concurrent.futures import ThreadPoolExecutor

    entries = {entry.template_id: entry for entry in corpus_entries()}
    jobs: list[tuple[str, str, str, str]] = []
    for partition, catalogue in bundle.catalogues.items():
        for group in catalogue.groups:
            entry = entries[group.template_id]
            for slot in group.slots:
                jobs.append(
                    (
                        f"{partition.value}|{group.template_id}|{slot.position}",
                        entry.module,
                        entry.module_text(slot.variant_index),
                        entry.hidden_verifier_source,
                    )
                )
    with ThreadPoolExecutor(max_workers=min(32, (os.cpu_count() or 4) * 2)) as pool:
        yield dict(pool.map(_execute, jobs))


class TestTheDealMeetsTheContractItWasSizedFor:
    def test_the_seal_reaches_both_group_floors(self, bundle: SealedCorpusBundle) -> None:
        assert bundle.seal.distinct_groups == 125
        assert bundle.seal.new_groups_relative_to_d1 == 95
        assert bundle.seal.candidate_slots == 500

    def test_every_partition_meets_its_own_floor(self, bundle: SealedCorpusBundle) -> None:
        for partition, catalogue in bundle.catalogues.items():
            assert len(catalogue.groups) >= PARTITION_GROUP_FLOOR[partition]

    def test_no_group_is_in_two_partitions(self, bundle: SealedCorpusBundle) -> None:
        """The pairwise disjointness matrix, as ten assertions rather than a table."""
        for left, right in itertools.combinations(CorrectionPartition, 2):
            assert not bundle.groups_of(left) & bundle.groups_of(right), (
                f"{left.value} and {right.value} share a group"
            )

    def test_every_group_is_claimed_exactly_once(self, bundle: SealedCorpusBundle) -> None:
        claimed = Counter(
            group.repository_group
            for catalogue in bundle.catalogues.values()
            for group in catalogue.groups
        )
        assert set(claimed.values()) == {1}
        assert len(claimed) == len(corpus_entries())


class TestInheritedGroupsAreConfinedAndStripped:
    def test_every_inherited_group_is_in_training(self, bundle: SealedCorpusBundle) -> None:
        """A prior public task in an evaluation partition would be a published answer."""
        for partition, catalogue in bundle.catalogues.items():
            inherited = [group for group in catalogue.groups if group.inherited_from_d1]
            if partition is CorrectionPartition.TRAINING:
                assert len(inherited) == len(TASK_SPECS)
            else:
                assert inherited == []

    def test_calibration_carries_no_inherited_group(self, bundle: SealedCorpusBundle) -> None:
        """S21D2-024 names calibration separately, so it is asserted separately."""
        calibration = bundle.catalogues[CorrectionPartition.CALIBRATION]
        assert not any(group.inherited_from_d1 for group in calibration.groups)

    def test_an_inherited_task_does_not_bring_its_c3_candidate_identity(
        self, bundle: SealedCorpusBundle
    ) -> None:
        """C3 candidate IDs encode the recipe; reusing them would restore the oracle."""
        training = bundle.catalogues[CorrectionPartition.TRAINING]
        c3_derived = {
            candidate_id_for(group.task_id, strategy)
            for group in training.groups
            if group.inherited_from_d1
            for strategy in RealityCandidateStrategy
        }
        sealed = {slot.candidate_id for group in training.groups for slot in group.slots}

        assert not sealed & c3_derived

    def test_an_inherited_group_carries_a_neutral_recipe(self, bundle: SealedCorpusBundle) -> None:
        training = bundle.catalogues[CorrectionPartition.TRAINING]
        recipes = {
            slot.recipe
            for group in training.groups
            if group.inherited_from_d1
            for slot in group.slots
        }

        assert recipes == {recipe.value for recipe in D2_NEUTRAL_RECIPES}


class TestBatchBIsGeneratedIndependently:
    def test_the_two_final_batches_use_different_seeds(self) -> None:
        assert (
            PARTITION_SEED[CorrectionPartition.FINAL_A]
            != PARTITION_SEED[CorrectionPartition.FINAL_B]
        )

    def test_the_two_final_batches_record_different_paths(self) -> None:
        assert (
            PARTITION_GENERATOR_PATH[CorrectionPartition.FINAL_A]
            != PARTITION_GENERATOR_PATH[CorrectionPartition.FINAL_B]
        )

    def test_no_candidate_identity_is_shared_by_any_two_partitions(
        self, bundle: SealedCorpusBundle
    ) -> None:
        seen: dict[str, CorrectionPartition] = {}
        for partition, catalogue in bundle.catalogues.items():
            for group in catalogue.groups:
                for slot in group.slots:
                    previous = seen.setdefault(str(slot.candidate_id), partition)
                    assert previous is partition

        assert len(seen) == 500

    def test_the_two_final_batches_are_comparably_composed(
        self, bundle: SealedCorpusBundle
    ) -> None:
        """B is a confirmation set, so it should look like A without being drawn with it."""

        def families(partition: CorrectionPartition) -> Counter[str]:
            return Counter(group.family for group in bundle.catalogues[partition].groups)

        assert families(CorrectionPartition.FINAL_A) == families(CorrectionPartition.FINAL_B)


class TestTheCataloguesAreSealedAndOutcomeFree:
    def test_each_catalogue_resolves_to_its_declared_role(self, bundle: SealedCorpusBundle) -> None:
        for partition, catalogue in bundle.catalogues.items():
            assert catalogue.provenance == PARTITION_PROVENANCE[partition]
            assert catalogue.corpus_role == PARTITION_CORPUS_ROLE[partition]
            assert catalogue.outcomes_present is False

    def test_only_the_canary_stops_at_the_first_acceptance(
        self, bundle: SealedCorpusBundle
    ) -> None:
        for partition, catalogue in bundle.catalogues.items():
            expected = (
                CorrectionCampaignMode.STOP_ON_FIRST_ACCEPTED
                if partition is CorrectionPartition.CANARY
                else CorrectionCampaignMode.LABEL_ALL
            )
            assert catalogue.mode is expected

    def test_a_catalogue_that_claims_an_outcome_is_refused(
        self, bundle: SealedCorpusBundle
    ) -> None:
        catalogue = bundle.catalogues[CorrectionPartition.FINAL_A]
        with pytest.raises(ValidationError):
            SealedPartitionCatalogue(
                **catalogue.model_dump(exclude={"content_hash", "outcomes_present"}),
                outcomes_present=True,
            )

    def test_a_catalogue_cannot_carry_an_outcome_field_at_all(
        self, bundle: SealedCorpusBundle
    ) -> None:
        """extra='forbid' is what makes 'outcome-free' structural rather than a convention."""
        slot = bundle.catalogues[CorrectionPartition.CANARY].groups[0].slots[0]
        with pytest.raises(ValidationError):
            CatalogueSlot(**slot.model_dump(exclude={"content_hash"}), verifier_status="accepted")

    def test_sealing_twice_produces_the_same_hashes(self, bundle: SealedCorpusBundle) -> None:
        again = seal_corpus()
        assert again.seal.content_hash == bundle.seal.content_hash
        for partition, catalogue in bundle.catalogues.items():
            assert again.catalogues[partition].content_hash == catalogue.content_hash

    def test_a_group_with_a_repeated_position_is_refused(self, bundle: SealedCorpusBundle) -> None:
        group = bundle.catalogues[CorrectionPartition.CANARY].groups[0]
        slots = list(group.model_dump(exclude={"content_hash"})["slots"])
        slots[1]["position"] = slots[0]["position"]
        with pytest.raises(ValidationError):
            CatalogueGroup(**{**group.model_dump(exclude={"content_hash"}), "slots": slots})


class TestFittingCannotReachTheHoldout:
    def test_the_seal_exposes_only_hashes_for_the_final_partitions(
        self, bundle: SealedCorpusBundle
    ) -> None:
        """S21D2-026: fitting receives the manifest hash and no holdout root or artifact port."""
        serialized = bundle.seal.model_dump_json()
        for partition in EVALUATION_PARTITIONS:
            for group in bundle.catalogues[partition].groups:
                assert group.repository_group not in serialized
                assert str(group.task_id) not in serialized
                for slot in group.slots:
                    assert str(slot.candidate_id) not in serialized

    def test_the_seal_still_binds_every_partition_by_hash(self, bundle: SealedCorpusBundle) -> None:
        sealed = dict(bundle.seal.catalogue_hashes)
        for partition, catalogue in bundle.catalogues.items():
            assert sealed[partition] == catalogue.content_hash

    def test_no_catalogue_field_can_be_fitted(self) -> None:
        """The feature contract rejects by absence, so this is the guarantee that matters."""
        names = set(CatalogueSlot.model_fields) | set(CatalogueGroup.model_fields)
        assert not names & set(FITTED_FEATURE_ALLOWLIST)


class TestTheOodSubmanifestsAreHashBound:
    def test_the_calibration_precheck_is_bound_to_the_calibration_catalogue(
        self, bundle: SealedCorpusBundle
    ) -> None:
        calibration = bundle.catalogues[CorrectionPartition.CALIBRATION]
        assert bundle.calibration_ood.source_catalogue_hashes == (calibration.content_hash,)
        assert set(bundle.calibration_ood.repository_groups) == bundle.groups_of(
            CorrectionPartition.CALIBRATION
        )

    def test_the_promotion_set_is_bound_to_both_final_catalogues(
        self, bundle: SealedCorpusBundle
    ) -> None:
        assert bundle.promotion_ood.source_catalogue_hashes == (
            bundle.catalogues[CorrectionPartition.FINAL_A].content_hash,
            bundle.catalogues[CorrectionPartition.FINAL_B].content_hash,
        )

    def test_the_promotion_set_meets_both_declared_floors(self, bundle: SealedCorpusBundle) -> None:
        """At least 100 future ranker decisions across at least ten final groups."""
        promotion = bundle.promotion_ood
        assert len(promotion.repository_groups) >= 10
        assert len(promotion.repository_groups) * CANDIDATES_PER_GROUP >= 100
        assert promotion.minimum_future_decisions >= 100

    def test_the_two_submanifests_are_separate(self, bundle: SealedCorpusBundle) -> None:
        """The promotion set stays untouched while the calibration one is resolved."""
        assert bundle.calibration_ood.content_hash != bundle.promotion_ood.content_hash
        assert not set(bundle.calibration_ood.repository_groups) & set(
            bundle.promotion_ood.repository_groups
        )


class TestTheCanaryIsRoutedAndSwitchable:
    def test_the_routing_policy_names_the_sealed_canary_manifest(
        self, bundle: SealedCorpusBundle
    ) -> None:
        canary = bundle.catalogues[CorrectionPartition.CANARY]
        assert bundle.canary_routing.canary_manifest_hash == canary.content_hash
        assert set(bundle.canary_routing.routed_groups) == bundle.groups_of(
            CorrectionPartition.CANARY
        )

    def test_the_configuration_accepts_the_sealed_routing_pair(
        self, bundle: SealedCorpusBundle
    ) -> None:
        config = LearnedPersistenceConfiguration(
            correction_ranking_groups=bundle.canary_routing.routed_groups,
            correction_ranking_manifest_hash=bundle.canary_routing.canary_manifest_hash,
        )

        assert config.correction_ranking_manifest_hash == bundle.canary_routing.canary_manifest_hash

    def test_the_kill_switch_is_off_by_default(self) -> None:
        """Emptying the routed set is the switch, and the shipped state is already empty."""
        shipped = LearnedPersistenceConfiguration()

        assert shipped.correction_ranking_groups == ()
        assert shipped.correction_ranking_manifest_hash == ""

    def test_routing_a_group_without_its_manifest_is_refused(
        self, bundle: SealedCorpusBundle
    ) -> None:
        with pytest.raises(ValidationError):
            LearnedPersistenceConfiguration(
                correction_ranking_groups=bundle.canary_routing.routed_groups
            )


class TestTheVerifierReplayAgreesWithEverySealedSlot:
    def test_every_slot_produces_the_verdict_its_variant_declares(
        self, bundle: SealedCorpusBundle, replay: dict[str, bool]
    ) -> None:
        """The only check that catches a wrong recipe-to-position composition."""
        entries = {entry.template_id: entry for entry in corpus_entries()}
        for partition, catalogue in bundle.catalogues.items():
            for group in catalogue.groups:
                declared = entries[group.template_id].repairs_contract
                for slot in group.slots:
                    key = f"{partition.value}|{group.template_id}|{slot.position}"
                    assert replay[key] is declared[slot.variant_index], key

    def test_exactly_half_of_every_partition_is_accepted(
        self, bundle: SealedCorpusBundle, replay: dict[str, bool]
    ) -> None:
        """The 2-of-4 balance is what fixes the label-blind baseline at 0.5000."""
        for partition, catalogue in bundle.catalogues.items():
            keys = [key for key in replay if key.startswith(f"{partition.value}|")]
            assert sum(replay[key] for key in keys) * 2 == catalogue.candidate_slots

    def test_the_recipe_does_not_predict_the_verdict_at_any_sealed_position(
        self, replay: dict[str, bool], bundle: SealedCorpusBundle
    ) -> None:
        """The C3 oracle, checked where it would actually bite: on the sealed slots."""
        totals: Counter[str] = Counter()
        accepted: Counter[str] = Counter()
        for partition, catalogue in bundle.catalogues.items():
            for group in catalogue.groups:
                for slot in group.slots:
                    key = f"{partition.value}|{group.template_id}|{slot.position}"
                    totals[slot.recipe] += 1
                    accepted[slot.recipe] += int(replay[key])

        for recipe, total in totals.items():
            rate = accepted[recipe] / total
            assert 0.3 < rate < 0.7, f"{recipe} is accepted {rate:.0%} of the time"

    def test_the_position_does_not_predict_the_verdict_either(
        self, replay: dict[str, bool], bundle: SealedCorpusBundle
    ) -> None:
        """Opaque candidate identity is worth nothing if slot zero is always the answer."""
        totals: Counter[int] = Counter()
        accepted: Counter[int] = Counter()
        for partition, catalogue in bundle.catalogues.items():
            for group in catalogue.groups:
                for slot in group.slots:
                    key = f"{partition.value}|{group.template_id}|{slot.position}"
                    totals[slot.position] += 1
                    accepted[slot.position] += int(replay[key])

        for position, total in totals.items():
            rate = accepted[position] / total
            assert 0.3 < rate < 0.7, f"position {position} is accepted {rate:.0%} of the time"
