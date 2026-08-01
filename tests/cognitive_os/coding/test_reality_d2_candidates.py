"""S21D2-021: candidate identity that does not answer the question the ranker is asked.

Three separate leaks close here, and they are separate because closing one does not close
the others:

* the C3 recipe *names* predict the label — measured, without exception, on all 120 D1
  correction-ranking examples — so D2 generates under outcome-neutral recipes instead;
* the candidate *ID* is a uuid5 over the recipe name, so it re-encodes what the name said
  even after the name is hidden;
* the runner *sorted* candidates by recipe name, so a deterministically shuffled manifest
  order was discarded before anything could act on it.

Plus the recording-order defect: the reference that enforces these rules used to be built
after the authoritative event was already appended.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from cognitive_os.coding.outcome_recording import CodingOutcomeRecorder
from cognitive_os.coding.reality_candidates import (
    candidate_id_for,
    opaque_candidate_id,
    shuffled_recipe_positions,
)
from cognitive_os.domain.reality import (
    D2_NEUTRAL_RECIPES,
    LABEL_PREDICTING_STRATEGIES,
    RealityCandidateStrategy,
    RealityRunKind,
    RealityStrategyFamily,
    validate_recorded_run_invariants,
)
from cognitive_os.events.coding_event_service import CodingEventService
from cognitive_os.events.memory_store import MemoryEventStore

from .reality_fixtures import (
    InMemoryArtifactStore,
    candidate_manifest,
    coding_outcome,
    hidden_evidence,
    task_manifest,
)

TASK = UUID(int=1)
OTHER_TASK = UUID(int=2)
RECIPES = tuple(sorted(D2_NEUTRAL_RECIPES, key=lambda item: item.value))


class TestTheD2RecipesMakeNoClaim:
    def test_there_are_four_of_them(self) -> None:
        assert len(D2_NEUTRAL_RECIPES) == 4

    @pytest.mark.parametrize("recipe", sorted(D2_NEUTRAL_RECIPES, key=lambda item: item.value))
    def test_every_d2_recipe_is_undeclared(self, recipe: RealityCandidateStrategy) -> None:
        """`UNDECLARED` is what lets a contradicting verifier result be a label, not a defect."""
        assert recipe.family is RealityStrategyFamily.UNDECLARED

    def test_no_d2_recipe_name_carries_an_outcome_claim(self) -> None:
        for recipe in D2_NEUTRAL_RECIPES:
            assert "correct" not in recipe.value
            assert "incomplete" not in recipe.value

    def test_the_c3_family_is_named_so_a_d2_campaign_can_refuse_it(self) -> None:
        assert {
            RealityCandidateStrategy.INCOMPLETE_A,
            RealityCandidateStrategy.INCOMPLETE_B,
            RealityCandidateStrategy.CORRECT_NARROW,
            RealityCandidateStrategy.CORRECT_ROBUST,
        } == LABEL_PREDICTING_STRATEGIES

    def test_the_two_sets_do_not_overlap(self) -> None:
        assert not D2_NEUTRAL_RECIPES & LABEL_PREDICTING_STRATEGIES


class TestOpaqueIdentityDoesNotEncodeTheRecipe:
    def test_the_c3_identity_is_derivable_from_the_recipe(self) -> None:
        """The property the D2 identity exists to remove, stated so the change is visible."""
        assert candidate_id_for(TASK, RealityCandidateStrategy.CORRECT_NARROW) == candidate_id_for(
            TASK, RealityCandidateStrategy.CORRECT_NARROW
        )

    def test_the_d2_identity_depends_on_position_rather_than_recipe(self) -> None:
        first = opaque_candidate_id(TASK, campaign_seed=7, position=0)
        second = opaque_candidate_id(TASK, campaign_seed=7, position=1)

        assert first != second
        assert first == opaque_candidate_id(TASK, campaign_seed=7, position=0)

    def test_a_different_seed_gives_a_different_identity(self) -> None:
        assert opaque_candidate_id(TASK, campaign_seed=7, position=0) != opaque_candidate_id(
            TASK, campaign_seed=8, position=0
        )

    def test_a_different_task_gives_a_different_identity(self) -> None:
        assert opaque_candidate_id(TASK, campaign_seed=7, position=0) != opaque_candidate_id(
            OTHER_TASK, campaign_seed=7, position=0
        )

    def test_no_d2_identity_collides_with_a_c3_one(self) -> None:
        opaque = {opaque_candidate_id(TASK, campaign_seed=7, position=i) for i in range(4)}
        legacy = {candidate_id_for(TASK, recipe) for recipe in RealityCandidateStrategy}

        assert not opaque & legacy

    def test_a_negative_position_is_refused(self) -> None:
        with pytest.raises(ValueError, match="zero-based index"):
            opaque_candidate_id(TASK, campaign_seed=7, position=-1)


class TestTheShuffleIsReplayableAndNotConstant:
    def test_the_same_task_and_seed_replay_exactly(self) -> None:
        assert shuffled_recipe_positions(TASK, RECIPES, campaign_seed=7) == (
            shuffled_recipe_positions(TASK, RECIPES, campaign_seed=7)
        )

    def test_two_tasks_in_one_campaign_shuffle_differently(self) -> None:
        """Otherwise position zero carries a constant prior across the whole corpus."""
        assert shuffled_recipe_positions(TASK, RECIPES, campaign_seed=7) != (
            shuffled_recipe_positions(OTHER_TASK, RECIPES, campaign_seed=7)
        )

    def test_the_shuffle_is_a_permutation_and_loses_nothing(self) -> None:
        shuffled = shuffled_recipe_positions(TASK, RECIPES, campaign_seed=7)

        assert sorted(shuffled, key=lambda item: item.value) == list(RECIPES)

    def test_a_repeated_recipe_is_refused(self) -> None:
        with pytest.raises(ValueError, match="same recipe twice"):
            shuffled_recipe_positions(TASK, (RECIPES[0], RECIPES[0]), campaign_seed=7)


class TestTheSharedValidatorRunsBeforeAnythingIsWritten:
    def test_a_well_formed_candidate_run_passes(self) -> None:
        validate_recorded_run_invariants(
            run_kind=RealityRunKind.CANDIDATE,
            candidate_id=UUID(int=9),
            strategy=RealityCandidateStrategy.RECIPE_ALPHA,
            hidden_verification_passed=True,
        )

    def test_a_baseline_that_passed_is_refused(self) -> None:
        with pytest.raises(ValueError, match="not a repair task"):
            validate_recorded_run_invariants(
                run_kind=RealityRunKind.BASELINE,
                candidate_id=None,
                strategy=None,
                hidden_verification_passed=True,
            )

    def test_a_baseline_carrying_a_candidate_is_refused(self) -> None:
        with pytest.raises(ValueError, match="baseline run has no candidate"):
            validate_recorded_run_invariants(
                run_kind=RealityRunKind.BASELINE,
                candidate_id=UUID(int=9),
                strategy=None,
                hidden_verification_passed=False,
            )

    def test_a_candidate_without_an_identity_is_refused(self) -> None:
        with pytest.raises(ValueError, match="must name its candidate"):
            validate_recorded_run_invariants(
                run_kind=RealityRunKind.CANDIDATE,
                candidate_id=None,
                strategy=None,
                hidden_verification_passed=False,
            )

    def test_a_declared_correct_c3_candidate_that_failed_is_still_refused(self) -> None:
        """C3's corpus contract is unchanged: its recipes still have to keep their promise."""
        with pytest.raises(ValueError, match="declared correct but failed"):
            validate_recorded_run_invariants(
                run_kind=RealityRunKind.CANDIDATE,
                candidate_id=UUID(int=9),
                strategy=RealityCandidateStrategy.CORRECT_NARROW,
                hidden_verification_passed=False,
            )

    def test_a_declared_incomplete_c3_candidate_that_passed_is_still_refused(self) -> None:
        with pytest.raises(ValueError, match="declared incomplete but passed"):
            validate_recorded_run_invariants(
                run_kind=RealityRunKind.CANDIDATE,
                candidate_id=UUID(int=9),
                strategy=RealityCandidateStrategy.INCOMPLETE_A,
                hidden_verification_passed=True,
            )

    @pytest.mark.parametrize("passed", [True, False])
    def test_a_d2_recipe_is_valid_whatever_the_verifier_said(self, passed: bool) -> None:
        """The point of the neutral recipes: the corpus cannot contradict its own verifier."""
        validate_recorded_run_invariants(
            run_kind=RealityRunKind.CANDIDATE,
            candidate_id=UUID(int=9),
            strategy=RealityCandidateStrategy.RECIPE_DELTA,
            hidden_verification_passed=passed,
        )


class TestARefusalLeavesNoAuthoritativeEvent:
    """The F6 defect end to end: refusing after the append leaves an unresolvable event."""

    @pytest.mark.asyncio
    async def test_a_violating_candidate_appends_nothing_and_writes_nothing(self) -> None:
        artifacts = InMemoryArtifactStore()
        store = MemoryEventStore()
        recorder = CodingOutcomeRecorder(artifacts, CodingEventService(store), store)
        task = task_manifest()
        task_run_id = uuid4()

        with pytest.raises(ValueError, match="declared correct but failed"):
            await recorder.record(
                outcome=coding_outcome(task_run_id=task_run_id),
                task=task,
                # CORRECT_NARROW promises the verifier will pass; the fixture fails it.
                evidence=hidden_evidence(task=task, task_run_id=task_run_id),
                candidate=candidate_manifest(task, RealityCandidateStrategy.CORRECT_NARROW),
                correlation_id=task_run_id,
            )

        assert await store.get_stream_version(task_run_id) in (None, 0)
        assert not artifacts._data, "a refusal must not leave artifact bytes behind"

    @pytest.mark.asyncio
    async def test_a_neutral_d2_recipe_records_either_verdict(self) -> None:
        artifacts = InMemoryArtifactStore()
        store = MemoryEventStore()
        recorder = CodingOutcomeRecorder(artifacts, CodingEventService(store), store)
        task = task_manifest()
        task_run_id = uuid4()

        recorded = await recorder.record(
            outcome=coding_outcome(task_run_id=task_run_id),
            task=task,
            evidence=hidden_evidence(task=task, task_run_id=task_run_id),
            candidate=candidate_manifest(task, RealityCandidateStrategy.RECIPE_ALPHA),
            correlation_id=task_run_id,
        )

        assert recorded.reference.strategy is RealityCandidateStrategy.RECIPE_ALPHA
        assert recorded.reference.hidden_verification_passed is False
