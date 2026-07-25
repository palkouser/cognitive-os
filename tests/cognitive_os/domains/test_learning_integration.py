"""Governed domain runs feed the learning plane through the services that own it."""

import pytest

from cognitive_os.domain.corpus import CorpusUsageRight
from cognitive_os.domain.experience import (
    ExperienceCandidateType,
    ExperienceStepStatus,
    TrajectoryCompleteness,
)
from cognitive_os.domain.memory import (
    MemoryScopeType,
    MemoryType,
)
from cognitive_os.domains.fixtures import build_all_cases, wrong_answer_for
from cognitive_os.domains.learning import (
    DomainLearningError,
    build_compilation,
    compile_run,
    corpus_request,
    domain_memory_policy,
    ingest_run,
    project_run,
    run_case_with_learning,
    terminal_acceptance_decision,
)
from cognitive_os.domains.runner import run_case_controlled
from cognitive_os.events.memory_store import MemoryEventStore
from cognitive_os.verification.factory import build_builtin_registry

ALL_CASES = build_all_cases()
SAMPLE = (ALL_CASES[0], ALL_CASES[20], ALL_CASES[40])
REGISTRY_HASH = build_builtin_registry().snapshot()


async def _recorded(case: object, *, wrong: bool = False) -> MemoryEventStore:
    store = MemoryEventStore()
    await run_case_controlled(
        case,  # type: ignore[arg-type]
        candidate_override=wrong_answer_for(case) if wrong else None,  # type: ignore[arg-type]
        store=store,
    )
    return store


# ----------------------------------------------------- Experience compilation


@pytest.mark.asyncio
@pytest.mark.parametrize("case", SAMPLE, ids=lambda item: item.case_id)
async def test_accepted_runs_compile_complete(case: object) -> None:
    store = await _recorded(case)
    result = await compile_run(case, store)  # type: ignore[arg-type]
    assert result.decision.decision.value == "completed"
    assert result.trajectory.completeness is TrajectoryCompleteness.COMPLETE
    assert result.snapshot.terminal_state == "accepted"
    assert not result.trajectory.gaps and not result.trajectory.conflicts


@pytest.mark.asyncio
async def test_every_timeline_entry_is_one_recorded_event() -> None:
    store = await _recorded(ALL_CASES[0])
    result = await compile_run(ALL_CASES[0], store)
    recorded_ids = {item.envelope.event_id for item in store.stored_events()}
    recorded_hashes = {item.envelope.payload_hash for item in store.stored_events()}
    assert len(result.trajectory.entries) == len(store.stored_events())
    for entry in result.trajectory.entries:
        assert entry.timeline_entry_id in recorded_ids
        assert all(evidence in recorded_hashes for evidence in entry.evidence_refs)


@pytest.mark.asyncio
async def test_rejected_runs_compile_as_failure_evidence() -> None:
    store = await _recorded(ALL_CASES[0], wrong=True)
    result = await compile_run(ALL_CASES[0], store)
    assert result.snapshot.terminal_state == "rejected"
    kinds = {item.candidate_type for item in result.candidates}
    assert ExperienceCandidateType.FAILURE_PATTERN in kinds
    assert ExperienceCandidateType.NEGATIVE_EXAMPLE in kinds
    assert result.analysis.failed_branches
    failed_verifiers = [
        entry
        for entry in result.trajectory.entries
        if entry.event_type == "verifier.completed" and entry.status is ExperienceStepStatus.FAILED
    ]
    assert failed_verifiers, "a failed verification must be recorded as a failed step"


@pytest.mark.asyncio
async def test_compilation_identity_follows_the_evidence() -> None:
    first_store = await _recorded(ALL_CASES[0])
    second_store = await _recorded(ALL_CASES[0], wrong=True)
    first, _sources, _profiles = build_compilation(ALL_CASES[0], first_store)
    again, _sources, _profiles = build_compilation(ALL_CASES[0], first_store)
    other, _sources, _profiles = build_compilation(ALL_CASES[0], second_store)
    assert first.compilation_id == again.compilation_id
    assert first.compilation_id != other.compilation_id


@pytest.mark.asyncio
async def test_a_run_without_events_cannot_be_compiled() -> None:
    with pytest.raises(DomainLearningError):
        build_compilation(ALL_CASES[0], MemoryEventStore())


@pytest.mark.asyncio
async def test_repaired_runs_keep_every_acceptance_decision_in_the_timeline() -> None:
    store = await _recorded(ALL_CASES[0], wrong=True)
    decisions = [
        item for item in store.event_types() if item == "controller.acceptance_decision_recorded"
    ]
    assert len(decisions) >= 2, "the repair cycle records a decision per attempt"
    assert terminal_acceptance_decision(store)["decision"] == "rejected"
    result = await compile_run(ALL_CASES[0], store)
    recorded_decisions = [
        entry
        for entry in result.trajectory.entries
        if entry.event_type == "controller.acceptance_decision_recorded"
    ]
    assert len(recorded_decisions) == len(decisions)


# --------------------------------------------------------------- Memory Plane


@pytest.mark.asyncio
async def test_runs_project_into_grounded_typed_memories() -> None:
    store = await _recorded(ALL_CASES[0])
    summary, verification = project_run(ALL_CASES[0], store, REGISTRY_HASH)
    assert summary.review_status == "accepted"
    assert "domains.checker@1" in verification.required_passed
    assert not verification.required_failed


@pytest.mark.asyncio
async def test_rejected_runs_are_not_laundered_into_accepted_memories() -> None:
    store = await _recorded(ALL_CASES[0], wrong=True)
    summary, verification = project_run(ALL_CASES[0], store, REGISTRY_HASH)
    assert summary.review_status == "rejected"
    assert "domains.checker@1" in verification.required_failed


def test_the_domain_memory_policy_is_least_privilege() -> None:
    policy = domain_memory_policy()
    assert policy.allowed_types == frozenset(
        {MemoryType.TASK_SUMMARY, MemoryType.VERIFICATION_SUMMARY}
    )
    assert MemoryScopeType.GLOBAL not in policy.allowed_scopes
    assert not policy.allow_provider_creator


# ------------------------------------------------------- End-to-end ingestion


@pytest.mark.asyncio
@pytest.mark.parametrize("case", SAMPLE, ids=lambda item: item.case_id)
async def test_the_whole_learning_plane_ingests_a_governed_run(case: object) -> None:
    run, result = await run_case_with_learning(case)  # type: ignore[arg-type]
    assert run.accepted
    assert result.compilation.decision.decision.value == "completed"
    assert len(result.memory_ids) == 2
    assert result.observation_count == 4 and result.claim_count == 4
    assert result.corpus_item_count >= 1


@pytest.mark.asyncio
async def test_ingestion_is_idempotent_per_recorded_trajectory() -> None:
    store = await _recorded(ALL_CASES[0])
    first = await ingest_run(ALL_CASES[0], store, registry_snapshot_hash=REGISTRY_HASH)
    second = await ingest_run(ALL_CASES[0], store, registry_snapshot_hash=REGISTRY_HASH)
    assert first.memory_ids == second.memory_ids
    assert first.compilation.manifest == second.compilation.manifest
    # A separate execution records different timestamps and identities: it is a
    # different trajectory and must not collide with the first one's evidence.
    other = await ingest_run(
        ALL_CASES[0],
        await _recorded(ALL_CASES[0]),
        registry_snapshot_hash=REGISTRY_HASH,
    )
    assert other.compilation.manifest.compilation_id != first.compilation.manifest.compilation_id


@pytest.mark.asyncio
async def test_corpus_declarations_grant_only_what_provenance_grants() -> None:
    _run, result = await run_case_with_learning(ALL_CASES[0])
    assert result.corpus_candidates
    for candidate in result.corpus_candidates:
        request, _source = corpus_request(ALL_CASES[0], candidate)
        assert request.usage_rights[CorpusUsageRight.MODEL_TRAINING] is None
        assert request.usage_rights[CorpusUsageRight.COMMERCIAL_USE] is None
        assert request.license_identifiers == (ALL_CASES[0].licence_and_source.licence,)
        assert (
            request.usage_rights[CorpusUsageRight.REDISTRIBUTION]
            == ALL_CASES[0].licence_and_source.redistributable
        )


@pytest.mark.asyncio
async def test_rejected_runs_yield_a_negative_corpus_example() -> None:
    run, result = await run_case_with_learning(
        ALL_CASES[0], candidate_override=wrong_answer_for(ALL_CASES[0])
    )
    assert not run.accepted
    kinds = {item.candidate_type for item in result.corpus_candidates}
    assert ExperienceCandidateType.NEGATIVE_EXAMPLE in kinds
    assert result.corpus_item_count >= 2
