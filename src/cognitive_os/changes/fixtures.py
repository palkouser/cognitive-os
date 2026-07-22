"""Credential-free deterministic controlled-change fixtures."""

from uuid import UUID

from cognitive_os.domain.proposals import (
    HarnessProposalIdentity,
    HarnessProposalRevision,
    HarnessProposalType,
    ProposalReview,
    ProposalReviewDecision,
    ProposalStatus,
)
from cognitive_os.proposals.fixtures import FIXTURE_TIME, fixture_proposal_source
from cognitive_os.proposals.repository import InMemoryProposalRepository
from cognitive_os.proposals.service import HarnessProposalService


class FixtureApprovedProposalSource:
    def __init__(
        self,
        repository: InMemoryProposalRepository,
        artifact_hashes: tuple[str, ...],
    ) -> None:
        self.repository = repository
        self.artifact_hashes = frozenset(artifact_hashes)

    async def get_proposal_identity(self, proposal_id: UUID) -> HarnessProposalIdentity | None:
        return self.repository.identities.get(proposal_id)

    async def get_exact_proposal(
        self, proposal_id: UUID, revision: int
    ) -> HarnessProposalRevision | None:
        return await self.repository.get_exact(proposal_id, revision)

    async def list_proposal_reviews(
        self, proposal_id: UUID, revision: int
    ) -> tuple[ProposalReview, ...]:
        return tuple(
            item
            for item in await self.repository.list_reviews()
            if item.proposal_id == proposal_id and item.proposal_revision == revision
        )

    async def artifact_exists(self, content_hash: str) -> bool:
        return content_hash in self.artifact_hashes


async def fixture_approved_proposal(
    proposal_type: HarnessProposalType = HarnessProposalType.SOURCE_CODE_CHANGE,
) -> tuple[FixtureApprovedProposalSource, HarnessProposalRevision]:
    weakness = await fixture_proposal_source()
    repository = InMemoryProposalRepository()
    service = HarnessProposalService(repository, weakness)
    validated = await service.create_from_weakness(
        weakness.revision.weakness_id,
        weakness.revision.revision,
        proposal_type,
        actor="proposal-author",
        created_at=FIXTURE_TIME,
    )
    staged = await service.transition(
        validated.proposal_id,
        validated.revision,
        ProposalStatus.STAGED_FOR_REVIEW,
        actor="proposal-author",
        reason="ready for isolated experiment review",
        created_at=FIXTURE_TIME,
    )
    approved = await service.record_review(
        staged.proposal_id,
        staged.revision,
        ProposalReviewDecision.APPROVE_FOR_EXPERIMENT,
        reviewer="proposal-reviewer",
        reviewer_authority="proposal-review",
        rationale="approved only for exact isolated experiment",
        created_at=FIXTURE_TIME,
    )
    return FixtureApprovedProposalSource(repository, approved.artifact_refs), approved
