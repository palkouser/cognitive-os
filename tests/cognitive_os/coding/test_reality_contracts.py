"""S21C3-010 and S21C3-011: what the reality contracts refuse to represent."""

from __future__ import annotations

from uuid import uuid4

import pytest

from cognitive_os.domain.coding import CodingOutcomeStatus
from cognitive_os.domain.reality import (
    PUBLIC_REALITY_CONTRACTS,
    CorrectionTrajectoryManifest,
    RealityCampaignManifest,
    RealityCandidateManifest,
    RealityCandidateSource,
    RealityCandidateStrategy,
    RealityCountBreakdown,
    RealityOutcomeReference,
    RealityRunIdentity,
    RealityRunKind,
    RealityStrategyFamily,
    RealityTaskManifest,
    RealityTaskProjection,
)

from .reality_fixtures import (
    FIXTURE_TIME,
    candidate_manifest,
    digest,
    task_manifest,
)

CONTROL_FIELD_NAMES = frozenset(
    {
        "hidden_verifier_bundle_hash",
        "hidden_verifier_bundle_artifact_id",
        "control_material_manifest_hash",
        "baseline_failure_reason",
        "expected_baseline",
        "golden_patch",
        "solution_hash",
    }
)


def test_provider_projection_has_no_field_that_could_hold_the_answer() -> None:
    """The isolation is structural, not a filter someone has to remember to apply."""
    assert not CONTROL_FIELD_NAMES & set(RealityTaskProjection.model_fields)
    assert RealityTaskProjection.model_config["extra"] == "forbid"


def test_projection_serializes_without_any_control_value() -> None:
    task = task_manifest()
    serialized = task.projection.model_dump_json()

    for value in (
        task.hidden_verifier_bundle_hash,
        task.control_material_manifest_hash,
        task.baseline_failure_reason,
        str(task.hidden_verifier_bundle_artifact_id),
    ):
        assert value not in serialized


def test_manifest_refuses_a_bundle_that_is_also_a_visible_file() -> None:
    task = task_manifest()
    fields = task.model_dump(exclude={"content_hash"})
    fields["hidden_verifier_bundle_hash"] = task.projection.files[0].file_hash

    with pytest.raises(ValueError, match="present in provider-visible content"):
        RealityTaskManifest(**fields)


def test_manifest_refuses_a_projection_from_another_task() -> None:
    task = task_manifest()
    other = task_manifest()
    fields = task.model_dump(exclude={"content_hash"})
    fields["projection"] = other.projection.model_dump()

    with pytest.raises(ValueError, match="belongs to a different task"):
        RealityTaskManifest(**fields)


def test_sealed_hash_detects_mutation() -> None:
    task = task_manifest()
    fields = task.model_dump()
    fields["repository_group"] = "moved-to-another-group"

    with pytest.raises(ValueError, match="hash mismatch"):
        RealityTaskManifest(**fields)


def test_every_public_reality_contract_seals_its_own_hash() -> None:
    for model in PUBLIC_REALITY_CONTRACTS:
        assert "content_hash" in model.model_fields, model.__name__


@pytest.mark.parametrize(
    ("strategy", "family"),
    (
        (RealityCandidateStrategy.INCOMPLETE_A, RealityStrategyFamily.INCORRECT),
        (RealityCandidateStrategy.INCOMPLETE_B, RealityStrategyFamily.INCORRECT),
        (RealityCandidateStrategy.CORRECT_NARROW, RealityStrategyFamily.CORRECT),
        (RealityCandidateStrategy.CORRECT_ROBUST, RealityStrategyFamily.CORRECT),
        (RealityCandidateStrategy.PROVIDER_PROPOSED, RealityStrategyFamily.UNDECLARED),
    ),
)
def test_provider_strategy_declares_no_expected_correctness(
    strategy: RealityCandidateStrategy, family: RealityStrategyFamily
) -> None:
    assert strategy.family is family


def test_offline_candidate_cannot_carry_provider_identity() -> None:
    task = task_manifest()

    with pytest.raises(ValueError, match="cannot carry provider identity"):
        candidate_manifest(task, provider_id="openrouter")


def test_provider_candidate_cannot_declare_an_offline_strategy() -> None:
    task = task_manifest()

    with pytest.raises(ValueError, match="cannot declare an offline strategy"):
        candidate_manifest(
            task,
            RealityCandidateStrategy.CORRECT_NARROW,
            source=RealityCandidateSource.OPENROUTER,
            provider_id="openrouter",
        )


def _outcome_reference(**overrides: object) -> RealityOutcomeReference:
    task = task_manifest()
    fields: dict[str, object] = {
        "task_run_id": uuid4(),
        "run_kind": RealityRunKind.CANDIDATE,
        "task_id": task.task_id,
        "task_manifest_hash": task.content_hash,
        "candidate_id": uuid4(),
        "strategy": RealityCandidateStrategy.INCOMPLETE_A,
        "outcome_hash": digest("outcome"),
        "outcome_artifact_id": uuid4(),
        "outcome_artifact_hash": digest("outcome"),
        "hidden_evidence_artifact_id": uuid4(),
        "hidden_evidence_hash": digest("evidence"),
        "final_status": CodingOutcomeStatus.FAILED,
        "hidden_verification_passed": False,
        "source_event_id": uuid4(),
        "occurred_at": FIXTURE_TIME,
    }
    fields.update(overrides)
    return RealityOutcomeReference(**fields)  # type: ignore[arg-type]


def test_declared_correct_candidate_that_failed_is_a_corpus_defect() -> None:
    with pytest.raises(ValueError, match="declared correct but failed"):
        _outcome_reference(strategy=RealityCandidateStrategy.CORRECT_NARROW)


def test_declared_incomplete_candidate_that_passed_is_a_corpus_defect() -> None:
    with pytest.raises(ValueError, match="declared incomplete but passed"):
        _outcome_reference(
            strategy=RealityCandidateStrategy.INCOMPLETE_A,
            hidden_verification_passed=True,
            final_status=CodingOutcomeStatus.FAILED,
        )


def test_baseline_that_passed_hidden_verification_is_refused() -> None:
    with pytest.raises(ValueError, match="not a repair task"):
        _outcome_reference(
            run_kind=RealityRunKind.BASELINE,
            candidate_id=None,
            strategy=None,
            hidden_verification_passed=True,
        )


def test_provider_proposed_outcome_may_pass_or_fail() -> None:
    for passed in (True, False):
        reference = _outcome_reference(
            strategy=RealityCandidateStrategy.PROVIDER_PROPOSED,
            hidden_verification_passed=passed,
            final_status=CodingOutcomeStatus.ACCEPTED if passed else CodingOutcomeStatus.FAILED,
        )
        assert reference.hidden_verification_passed is passed


def test_trajectory_must_run_from_a_failure_to_a_correction() -> None:
    with pytest.raises(ValueError, match="must start from a declared failure"):
        CorrectionTrajectoryManifest(
            trajectory_id=uuid4(),
            task_id=uuid4(),
            incorrect_strategy=RealityCandidateStrategy.CORRECT_NARROW,
            correct_strategy=RealityCandidateStrategy.CORRECT_ROBUST,
            ordered_outcome_event_ids=(uuid4(), uuid4(), uuid4()),
            ordered_outcome_hashes=(digest("a"), digest("b"), digest("c")),
            created_at=FIXTURE_TIME,
        )


def test_trajectory_cannot_reuse_one_outcome_as_two_steps() -> None:
    repeated = uuid4()

    with pytest.raises(ValueError, match="cannot reuse an outcome event"):
        CorrectionTrajectoryManifest(
            trajectory_id=uuid4(),
            task_id=uuid4(),
            incorrect_strategy=RealityCandidateStrategy.INCOMPLETE_A,
            correct_strategy=RealityCandidateStrategy.CORRECT_NARROW,
            ordered_outcome_event_ids=(repeated, repeated, uuid4()),
            ordered_outcome_hashes=(digest("a"), digest("b"), digest("c")),
            created_at=FIXTURE_TIME,
        )


def _run_identity(task: RealityTaskManifest, **overrides: object) -> RealityRunIdentity:
    fields: dict[str, object] = {
        "task_id": task.task_id,
        "task_manifest_hash": task.content_hash,
        "run_kind": RealityRunKind.BASELINE,
        "source": RealityCandidateSource.BASELINE,
        "generator_profile_id": "reality.tasks",
        "verifier_profile_hash": digest("verifier profile"),
        "campaign_version": 1,
    }
    fields.update(overrides)
    return RealityRunIdentity(**fields)  # type: ignore[arg-type]


def test_run_identity_changes_when_any_determining_input_changes() -> None:
    task = task_manifest()
    baseline = _run_identity(task)

    assert baseline.key != _run_identity(task, campaign_version=2).key
    assert baseline.key != _run_identity(task, verifier_profile_hash=digest("other")).key
    assert baseline.key != _run_identity(task, generator_profile_id="reality.other").key
    assert baseline.key == _run_identity(task).key


def test_campaign_with_provider_runs_requires_the_live_opt_in() -> None:
    task = task_manifest()
    candidate = candidate_manifest(
        task,
        RealityCandidateStrategy.PROVIDER_PROPOSED,
        source=RealityCandidateSource.OPENROUTER,
        provider_id="openrouter",
    )
    provider_run = _run_identity(
        task,
        run_kind=RealityRunKind.CANDIDATE,
        candidate_id=candidate.candidate_id,
        strategy=RealityCandidateStrategy.PROVIDER_PROPOSED,
        source=RealityCandidateSource.OPENROUTER,
    )

    with pytest.raises(ValueError, match="must declare the live opt-in"):
        RealityCampaignManifest(
            campaign_id=uuid4(),
            campaign_version=1,
            planned_runs=(provider_run,),
            verifier_profile_hash=digest("verifier profile"),
            created_at=FIXTURE_TIME,
        )


def test_campaign_cannot_plan_the_same_run_twice() -> None:
    task = task_manifest()
    identity = _run_identity(task)

    with pytest.raises(ValueError, match="same run identity twice"):
        RealityCampaignManifest(
            campaign_id=uuid4(),
            campaign_version=1,
            planned_runs=(identity, identity),
            verifier_profile_hash=digest("verifier profile"),
            created_at=FIXTURE_TIME,
        )


def test_a_breakdown_cannot_report_more_than_its_denominator() -> None:
    with pytest.raises(ValueError, match="cannot exceed its denominator"):
        RealityCountBreakdown(dimension="provider", value="openrouter", numerator=6, denominator=5)


def test_candidate_manifest_carries_no_expected_result() -> None:
    """A selector reading candidates must not be able to read the label off them."""
    forbidden = {"expected_result", "passes_hidden", "hidden_verification_passed", "is_correct"}

    assert not forbidden & set(RealityCandidateManifest.model_fields)
