"""Dependency-light append-only proposal repository."""

from typing import TypeVar
from uuid import UUID

from cognitive_os.domain.proposals import (
    HarnessProposalIdentity,
    HarnessProposalRevision,
    ProposalAccessRecord,
    ProposalQueueEntry,
    ProposalReview,
    ProposalRunManifest,
    ProposalSourceSnapshot,
    ProposalStatus,
)

from .service import ProposalConflictError

Key = TypeVar("Key")
Value = TypeVar("Value")


class InMemoryProposalRepository:
    def __init__(self) -> None:
        self.identities: dict[UUID, HarnessProposalIdentity] = {}
        self.revisions: dict[tuple[UUID, int], HarnessProposalRevision] = {}
        self.sources: dict[UUID, ProposalSourceSnapshot] = {}
        self.reviews: dict[UUID, ProposalReview] = {}
        self.queue: dict[UUID, ProposalQueueEntry] = {}
        self.accesses: dict[UUID, ProposalAccessRecord] = {}
        self.manifests: dict[tuple[UUID, int], ProposalRunManifest] = {}

    async def create(
        self, identity: HarnessProposalIdentity, revision: HarnessProposalRevision
    ) -> None:
        if revision.proposal_id != identity.proposal_id or revision.revision != 1:
            raise ProposalConflictError("invalid initial proposal revision")
        self._immutable(self.identities, identity.proposal_id, identity)
        self._immutable(self.revisions, (identity.proposal_id, 1), revision)

    async def get_identity(self, proposal_id: UUID) -> HarnessProposalIdentity | None:
        return self.identities.get(proposal_id)

    async def append(self, revision: HarnessProposalRevision, *, expected_revision: int) -> None:
        current = await self.get_current(revision.proposal_id)
        if current is None or current.revision != expected_revision:
            raise ProposalConflictError("proposal revision compare-and-set failed")
        if revision.revision != expected_revision + 1:
            raise ProposalConflictError("proposal revision is not contiguous")
        self._immutable(self.revisions, (revision.proposal_id, revision.revision), revision)

    async def get_exact(self, proposal_id: UUID, revision: int) -> HarnessProposalRevision | None:
        return self.revisions.get((proposal_id, revision))

    async def get_current(self, proposal_id: UUID) -> HarnessProposalRevision | None:
        values = [item for (identity, _), item in self.revisions.items() if identity == proposal_id]
        return max(values, key=lambda item: item.revision, default=None)

    async def find_active_signature(self, signature: str) -> HarnessProposalRevision | None:
        return next(
            (
                item
                for item in await self.list_current()
                if item.proposal_signature == signature
                and item.status
                not in {
                    ProposalStatus.REJECTED,
                    ProposalStatus.RETRACTED,
                    ProposalStatus.SUPERSEDED,
                }
            ),
            None,
        )

    async def record_source(self, snapshot: ProposalSourceSnapshot) -> None:
        self._immutable(self.sources, snapshot.proposal_id, snapshot)

    async def record_review(self, review: ProposalReview) -> None:
        self._immutable(self.reviews, review.review_id, review)

    async def list_reviews(self) -> tuple[ProposalReview, ...]:
        return tuple(self.reviews[key] for key in sorted(self.reviews, key=str))

    async def record_queue(self, entry: ProposalQueueEntry) -> None:
        self._immutable(self.queue, entry.queue_entry_id, entry)

    async def list_queue(self) -> tuple[ProposalQueueEntry, ...]:
        return tuple(self.queue[key] for key in sorted(self.queue, key=str))

    async def record_access(self, access: ProposalAccessRecord) -> None:
        self._immutable(self.accesses, access.access_id, access)

    async def record_manifest(self, manifest: ProposalRunManifest) -> None:
        self._immutable(
            self.manifests,
            (manifest.proposal_id, manifest.proposal_revision),
            manifest,
        )

    async def list_current(self) -> tuple[HarnessProposalRevision, ...]:
        proposal_ids = sorted(self.identities, key=str)
        values = [await self.get_current(proposal_id) for proposal_id in proposal_ids]
        return tuple(item for item in values if item is not None)

    @staticmethod
    def _immutable(store: dict[Key, Value], key: Key, value: Value) -> None:
        existing = store.get(key)
        if existing is not None and existing != value:
            raise ProposalConflictError("immutable proposal record changed")
        store[key] = value
