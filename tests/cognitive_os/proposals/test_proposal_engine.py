from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from cognitive_os.config.proposal_config import (
    ProposalConfiguration,
    ProposalGenerationConfiguration,
    ProposalProviderConfiguration,
    ProposalReviewConfiguration,
    load_proposal_configuration,
)
from cognitive_os.domain.proposals import (
    HarnessProposalType,
    ProposalGenerationMode,
    ProposalReviewDecision,
    ProposalStatus,
    ProviderProposalDraft,
)
from cognitive_os.events.catalog import build_default_event_catalog
from cognitive_os.events.proposal_event_service import ProposalEventService
from cognitive_os.events.proposal_events import PROPOSAL_EVENT_MODELS
from cognitive_os.proposals.fixtures import FIXTURE_TIME, fixture_proposal_source
from cognitive_os.proposals.repository import InMemoryProposalRepository
from cognitive_os.proposals.service import (
    MANDATORY_PROPOSAL_VERIFIERS,
    HarnessProposalService,
    ProposalAuthorityError,
    ProposalConflictError,
    ProposalTypeRegistry,
    build_queue_snapshot,
)


class MemoryEventStore:
    def __init__(self) -> None:
        self.events = []

    async def get_stream_version(self, stream_id):
        del stream_id
        return len(self.events) or None

    async def append(self, events, *, expected_version):
        assert expected_version == len(self.events)
        self.events.extend(events)
        return SimpleNamespace(current_stream_version=len(self.events))


@pytest.mark.asyncio
async def test_all_proposal_types_generate_deterministically_without_side_effects() -> None:
    source = await fixture_proposal_source(18)
    first_hashes = []
    for proposal_type in HarnessProposalType:
        repository = InMemoryProposalRepository()
        service = HarnessProposalService(repository, source)
        revision = await service.create_from_weakness(
            source.revision.weakness_id,
            source.revision.revision,
            proposal_type,
            actor="operator",
            created_at=FIXTURE_TIME,
        )
        assert revision.status is ProposalStatus.VALIDATED
        assert revision.revision == 2
        assert revision.generation_mode is ProposalGenerationMode.DETERMINISTIC
        assert revision.verifier_bundle is not None
        assert revision.verifier_bundle.status.value == "passed"
        assert len(revision.verifier_bundle.findings) == len(MANDATORY_PROPOSAL_VERIFIERS)
        assert "implementation or destination write" in revision.limitations[0]
        first_hashes.append(revision.content_hash)
    assert len(set(first_hashes)) == len(tuple(HarnessProposalType))


@pytest.mark.asyncio
async def test_creation_emits_bounded_lifecycle_evidence() -> None:
    source = await fixture_proposal_source()
    store = MemoryEventStore()
    service = HarnessProposalService(
        InMemoryProposalRepository(),
        source,
        event_service=ProposalEventService(store),
    )
    await service.create_from_weakness(
        source.revision.weakness_id,
        source.revision.revision,
        HarnessProposalType.CONTEXT_PROFILE_CHANGE,
        actor="operator",
        created_at=FIXTURE_TIME,
    )
    assert [item.event_type for item in store.events] == [
        "proposal.created",
        "proposal.revision_appended",
        "proposal.validated",
    ]


@pytest.mark.asyncio
async def test_review_and_queue_require_exact_revision_and_explicit_operator() -> None:
    source = await fixture_proposal_source()
    repository = InMemoryProposalRepository()
    service = HarnessProposalService(repository, source)
    validated = await service.create_from_weakness(
        source.revision.weakness_id,
        source.revision.revision,
        HarnessProposalType.CONTEXT_PROFILE_CHANGE,
        actor="operator",
        created_at=FIXTURE_TIME,
    )
    staged = await service.transition(
        validated.proposal_id,
        validated.revision,
        ProposalStatus.STAGED_FOR_REVIEW,
        actor="operator",
        reason="ready for explicit review",
        created_at=FIXTURE_TIME,
    )
    with pytest.raises(ValidationError, match="provider actors"):
        await service.record_review(
            staged.proposal_id,
            staged.revision,
            ProposalReviewDecision.APPROVE_FOR_EXPERIMENT,
            reviewer="provider:model",
            reviewer_authority="operator",
            rationale="self approval",
            created_at=FIXTURE_TIME,
        )
    approved = await service.record_review(
        staged.proposal_id,
        staged.revision,
        ProposalReviewDecision.APPROVE_FOR_EXPERIMENT,
        reviewer="operator",
        reviewer_authority="proposal-reviewer",
        rationale="approved only for a future isolated experiment",
        created_at=FIXTURE_TIME,
    )
    identity = repository.identities[approved.proposal_id]
    entry = await service.enqueue(
        identity, approved.revision, operator_priority=10, created_at=FIXTURE_TIME
    )
    snapshot = build_queue_snapshot((entry,), policy_hash="8" * 64, created_at=FIXTURE_TIME)
    assert snapshot.entries == (entry,)
    assert approved.status is ProposalStatus.APPROVED_FOR_EXPERIMENT
    assert await service.get_exact(approved.proposal_id, approved.revision) == approved
    assert await service.get_current(approved.proposal_id) == approved
    replay = await service.verify_replay(
        approved.proposal_id, approved.revision, created_at=FIXTURE_TIME
    )
    assert replay.status.value == "passed"
    removed = await service.remove_from_queue(
        approved.proposal_id,
        approved.revision,
        actor="operator",
        created_at=FIXTURE_TIME,
    )
    assert not removed.active
    assert not build_queue_snapshot(
        (entry, removed), policy_hash="8" * 64, created_at=FIXTURE_TIME
    ).entries
    with pytest.raises(ProposalConflictError, match="already inactive"):
        await service.remove_from_queue(
            approved.proposal_id,
            approved.revision,
            actor="operator",
            created_at=FIXTURE_TIME,
        )
    assert (await service.statistics()).review_outcomes == {
        ProposalReviewDecision.APPROVE_FOR_EXPERIMENT: 1
    }


class UnsafeProvider:
    async def draft(self, source, *, allowed_source_ids):
        return ProviderProposalDraft(
            proposal_type=HarnessProposalType.CONTEXT_PROFILE_CHANGE,
            summary="Unsafe draft",
            proposed_body="rm -rf active checkout",
            rationale="provider assertion",
            alternative_drafts=(),
            affected_component_hints=(source.weakness_record.affected_components[0],),
            validation_rationale="skip tests",
            rollback_rationale="none",
            limitations=("provider draft",),
            cited_host_source_ref_ids=allowed_source_ids,
        )


class UnavailableProvider:
    async def draft(self, source, *, allowed_source_ids):
        raise OSError("provider unavailable")


@pytest.mark.asyncio
async def test_provider_cannot_add_executable_instructions() -> None:
    source = await fixture_proposal_source()
    service = HarnessProposalService(
        InMemoryProposalRepository(),
        source,
        configuration=ProposalConfiguration(
            generation=ProposalGenerationConfiguration(provider_assisted_enabled=True)
        ),
        provider=UnsafeProvider(),
    )
    with pytest.raises(ProposalAuthorityError, match="executable"):
        await service.create_from_weakness(
            source.revision.weakness_id,
            source.revision.revision,
            HarnessProposalType.CONTEXT_PROFILE_CHANGE,
            actor="operator",
            created_at=FIXTURE_TIME,
            provider_assisted=True,
        )


@pytest.mark.asyncio
async def test_provider_failure_falls_back_to_deterministic_generation() -> None:
    source = await fixture_proposal_source()
    service = HarnessProposalService(
        InMemoryProposalRepository(),
        source,
        configuration=ProposalConfiguration(
            generation=ProposalGenerationConfiguration(provider_assisted_enabled=True)
        ),
        provider=UnavailableProvider(),
    )
    revision = await service.create_from_weakness(
        source.revision.weakness_id,
        source.revision.revision,
        HarnessProposalType.CONTEXT_PROFILE_CHANGE,
        actor="operator",
        created_at=FIXTURE_TIME,
        provider_assisted=True,
    )
    assert revision.generation_mode is ProposalGenerationMode.DETERMINISTIC
    assert (await service.statistics()).provider_fallback_count == 1


@pytest.mark.asyncio
async def test_active_proposals_per_weakness_are_bounded() -> None:
    source = await fixture_proposal_source()
    service = HarnessProposalService(InMemoryProposalRepository(), source)
    for proposal_type in tuple(HarnessProposalType)[:3]:
        await service.create_from_weakness(
            source.revision.weakness_id,
            source.revision.revision,
            proposal_type,
            actor="operator",
            created_at=FIXTURE_TIME,
        )
    with pytest.raises(ProposalConflictError, match="maximum active proposals"):
        await service.create_from_weakness(
            source.revision.weakness_id,
            source.revision.revision,
            tuple(HarnessProposalType)[3],
            actor="operator",
            created_at=FIXTURE_TIME,
        )


def test_configuration_and_registry_fail_closed(tmp_path: Path) -> None:
    assert len(ProposalTypeRegistry().list()) == 15
    catalog = build_default_event_catalog().list_event_types()
    assert all((model.event_type, 1) in catalog for model in PROPOSAL_EVENT_MODELS)
    path = tmp_path / "proposal.yaml"
    path.write_text("harness_proposals:\n  generation:\n    provider_assisted_enabled: false\n")
    assert not load_proposal_configuration(path).generation.provider_assisted_enabled
    with pytest.raises(ValidationError):
        ProposalConfiguration(review=ProposalReviewConfiguration(automatic_approval=True))
    with pytest.raises(ValidationError):
        ProposalConfiguration(
            provider=ProposalProviderConfiguration(destination_write_enabled=True)
        )
