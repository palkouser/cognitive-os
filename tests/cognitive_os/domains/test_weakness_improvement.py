"""A real cross-domain capability gap is mined, proposed, and experimented on."""

import pytest

from cognitive_os.domain.changes import (
    ChangeSurfaceTier,
    IsolationKind,
    PromotionDecision,
    PromotionMode,
)
from cognitive_os.domain.proposals import ProposalStatus
from cognitive_os.domain.weakness import (
    MiningRunStatus,
    WeaknessConfidenceLevel,
    WeaknessSeverity,
    WeaknessStatus,
)
from cognitive_os.domains.improvement import (
    PROPOSAL_TYPE,
    propose_from_domain_weakness,
    run_isolated_experiment,
)
from cognitive_os.domains.runner import run_case_controlled
from cognitive_os.domains.weakness import (
    FAILURE_CODE,
    IRRATIONAL_ROOT_PROBES,
    WEAKNESS_TYPE,
    DomainWeaknessError,
    confirm_domain_weakness,
    mine_domain_weaknesses,
    observe_probes,
    probe_case,
)
from cognitive_os.events.memory_store import MemoryEventStore

# ------------------------------------------------- The weakness is real, not staged


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case_id", "inputs"), IRRATIONAL_ROOT_PROBES, ids=[item[0] for item in IRRATIONAL_ROOT_PROBES]
)
async def test_each_probe_is_a_legitimate_case_the_harness_cannot_solve(
    case_id: str, inputs: dict[str, int]
) -> None:
    case = probe_case(case_id, inputs)
    # The registry accepts the task class: nothing about this case is malformed.
    assert case.problem_type == "polynomial-equation"
    assert case.problem.formal_inputs == inputs
    assert case.plan.forbidden_operations
    store = MemoryEventStore()
    run = await run_case_controlled(case, store=store)
    # It fails, and it fails with recorded evidence rather than an escaped exception.
    assert not run.accepted
    assert "tool_call.failed" in store.event_types()
    assert "controller.acceptance_decision_recorded" in store.event_types()


@pytest.mark.asyncio
async def test_a_failing_tool_still_records_a_full_audit_trail() -> None:
    """Regression: the executor must report an outcome, never raise past the Controller."""
    case = probe_case(*IRRATIONAL_ROOT_PROBES[0])
    store = MemoryEventStore()
    run = await run_case_controlled(case, store=store)
    events = store.event_types()
    for required in (
        "tool_call.requested",
        "tool_call.authorized",
        "tool_call.started",
        "tool_call.failed",
        "execution_step.failed",
        "verifier.completed",
        "controller.acceptance_decision_recorded",
    ):
        assert required in events, required
    assert not run.accepted
    assert run.tool_calls >= 1


@pytest.mark.asyncio
async def test_probes_that_stop_failing_invalidate_the_miner() -> None:
    """If the gap is ever closed, mining must refuse rather than report a stale weakness."""
    observations = await observe_probes()
    assert len(observations) == len(IRRATIONAL_ROOT_PROBES)
    assert all(item.is_capability_gap for item in observations)


# ------------------------------------------------------------------- Mining (S20-052)


@pytest.mark.asyncio
async def test_mining_groups_the_probes_into_one_weakness() -> None:
    outcome = await mine_domain_weaknesses()
    assert outcome.result.status is MiningRunStatus.COMPLETED
    manifest = outcome.result.manifest
    assert manifest is not None
    assert manifest.summary.signal_count == len(IRRATIONAL_ROOT_PROBES)
    assert manifest.summary.weakness_count == 1
    assert manifest.summary.group_count == 1


@pytest.mark.asyncio
async def test_every_signal_cites_the_run_that_produced_it() -> None:
    outcome = await mine_domain_weaknesses()
    recorded = {item.task_run_id for item in outcome.observations}
    signals = tuple(outcome.repository.signals.values())
    assert {item.task_run_id for item in signals} == recorded
    for signal in signals:
        assert signal.weakness_type is WEAKNESS_TYPE
        assert signal.failure_code == FAILURE_CODE
        assert signal.severity is WeaknessSeverity.MEDIUM
        assert signal.confidence is WeaknessConfidenceLevel.VERIFIED
        # Non-shadow authoritative evidence, and an authority that owns the outcome.
        assert any(item.authoritative and not item.shadow for item in signal.source_refs)
        assert any(item.outcome_authority for item in signal.source_refs)
        assert signal.limitations


@pytest.mark.asyncio
async def test_mining_is_deterministic_and_diagnostic_only() -> None:
    first = await mine_domain_weaknesses()
    second = await mine_domain_weaknesses()
    assert first.result.manifest == second.result.manifest
    # Mining diagnoses; it never proposes.
    revisions = first.repository.revisions.values()
    assert revisions
    assert all("proposal" not in item.description.lower() for item in revisions)


@pytest.mark.asyncio
async def test_confirmation_is_an_explicit_operator_act() -> None:
    source = await confirm_domain_weakness()
    assert source.revision.status is WeaknessStatus.CONFIRMED
    assert source.revision.affected_components == ("domains.solve",)
    # The queue entry must reference the exact confirmed revision.
    assert source.queue.weakness_revision_hash == source.revision.content_hash
    assert source.evidence.reproduction.status.value == "reproducible"


# ------------------------------------------------------------------ Proposal (S20-053)


@pytest.mark.asyncio
async def test_a_proposal_is_generated_from_the_confirmed_weakness() -> None:
    outcome = await propose_from_domain_weakness()
    proposal = outcome.proposal
    assert proposal.status is ProposalStatus.APPROVED_FOR_EXPERIMENT
    assert proposal.change_specification.change_surface == PROPOSAL_TYPE.value
    snapshot = proposal.source_snapshot
    assert snapshot.weakness_id == outcome.weakness.revision.weakness_id
    assert snapshot.weakness_revision == outcome.weakness.revision.revision
    assert snapshot.weakness_record.content_hash == outcome.weakness.revision.content_hash
    # The engine produced its own analysis; the domain package supplied none of it.
    assert proposal.minimality_assessment is not None
    assert proposal.risk_assessment is not None
    assert proposal.validation_plan is not None
    assert proposal.rollback_plan is not None


@pytest.mark.asyncio
async def test_the_proposal_names_no_provider_prose() -> None:
    outcome = await propose_from_domain_weakness()
    assert outcome.proposal.generation_mode.value != "provider_assisted"


@pytest.mark.asyncio
async def test_the_proposal_scope_is_narrow() -> None:
    outcome = await propose_from_domain_weakness()
    specification = outcome.proposal.change_specification
    assert len(specification.allowed_files) == 1
    assert specification.forbidden_surfaces


# ------------------------------------------------------- Controlled change (S20-054)


@pytest.mark.asyncio
async def test_the_experiment_runs_in_isolation() -> None:
    outcome = await run_isolated_experiment()
    isolation = outcome.isolation
    assert isolation.isolation_kind is IsolationKind.DECLARATIVE_COPY
    assert isolation.network_policy == "disabled"
    assert isolation.allowed_repository_paths
    # The active checkout is pinned to the declared baseline and not mutated.
    assert isolation.baseline_commit == isolation.active_state_protection_snapshot.repository_commit
    assert isolation.worktree_path_reference.startswith("workspace://")


@pytest.mark.asyncio
async def test_a_tool_definition_change_cannot_be_promoted_automatically() -> None:
    outcome = await run_isolated_experiment()
    assert outcome.experiment.change_surface_tier is ChangeSurfaceTier.TIER_3_CRITICAL
    assert outcome.promotion_mode is PromotionMode.MANUAL_REVIEW_ONLY
    assert outcome.promotion_is_manual
    assert outcome.assessment.decision is PromotionDecision.REQUIRES_MANUAL_REVIEW
    assert outcome.assessment.approval_requirements


@pytest.mark.asyncio
async def test_the_experiment_is_evaluated_against_the_engines_own_matrix() -> None:
    outcome = await run_isolated_experiment()
    assert outcome.matrix.execution_order
    assert len(outcome.comparison.case_results) == len(outcome.matrix.execution_order)
    assert not outcome.comparison.hard_failure_codes
    # The assessment carries the exact comparison it judged, not a restated summary.
    assert outcome.assessment.regression_comparison == outcome.comparison
    assert outcome.assessment.measured_benefit.sample_count == len(outcome.matrix.execution_order)


@pytest.mark.asyncio
async def test_the_cycle_is_deterministic() -> None:
    first = await run_isolated_experiment()
    second = await run_isolated_experiment()
    assert first.experiment.content_hash == second.experiment.content_hash
    assert first.isolation.content_hash == second.isolation.content_hash
    assert first.assessment.content_hash == second.assessment.content_hash


def test_the_miner_declares_its_own_staleness_error() -> None:
    assert issubclass(DomainWeaknessError, RuntimeError)
