"""Narrow persistence and execution ports for governed provider output.

Same discipline as the learned evidence ports: every method exists because one Sprint 21C2
use case needs it, and none exposes arbitrary SQL, an untyped payload write or a direct
state replacement. There is no `save`, no `update` and no `delete` — a governance decision
is corrected by appending a revision, and a port that offered an update would make the
append-only guarantee a convention rather than a shape.

The in-memory and PostgreSQL implementations share one contract suite, so the semantics
below are the specification for both. See ADR 0087.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from cognitive_os.domain.learned_evidence import GovernedOutcomeReference
from cognitive_os.domain.model_requests import ModelProviderRequest
from cognitive_os.domain.provider_output import (
    GovernedExecutionReceipt,
    ProviderOutputIntendedUse,
    ProviderOutputRecord,
    ProviderRetentionDirective,
)


class GovernedModelExecutionPort(Protocol):
    """Ordinary execution plus one explicit governed path.

    `execute_with_receipt` shares the internal provider call with `execute`; it must not
    make a second request. A second call would double the spend, double the provider-side
    retention and produce two model-call event streams for one logical execution.
    """

    async def execute_with_receipt(
        self,
        request: ModelProviderRequest,
        *,
        provider_id: str | None = None,
        directive: ProviderRetentionDirective,
    ) -> GovernedExecutionReceipt: ...


class ProviderOutputRepositoryPort(Protocol):
    """Durable provider-output governance.

    Idempotency is by `idempotency_key`. Replaying the *same* request returns the original
    record. Reusing a key with *different* content raises
    `ProviderOutputConflict.IDEMPOTENCY_KEY_REUSED`, because a retry must never rewrite a
    governance decision.
    """

    async def record_output(self, record: ProviderOutputRecord) -> ProviderOutputRecord:
        """Append one immutable governance revision.

        Revision 1 creates the output identity. A later revision must name the revision it
        supersedes and must follow it; a gap or a fork raises `REVISION_CONFLICT`.
        """
        ...

    async def get_revision(self, revision_id: UUID) -> ProviderOutputRecord | None:
        """One exact revision by its immutable row identity."""
        ...

    async def get_latest(self, provider_output_id: UUID) -> ProviderOutputRecord | None:
        """The highest revision for one stable output ID.

        Derived from the ledger through a bounded index, not from a materialized
        current-state table: a projection would be a second authority.
        """
        ...

    async def revision_history(
        self, provider_output_id: UUID, *, limit: int = 100, offset: int = 0
    ) -> tuple[ProviderOutputRecord, ...]:
        """Ascending revision order, which is the audit order. Bounded pagination."""
        ...

    async def list_eligible(
        self,
        *,
        intended_use: ProviderOutputIntendedUse,
        moment: datetime,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[ProviderOutputRecord, ...]:
        """Latest revisions that may be *newly* selected for the given use at `moment`.

        Fails closed: a superseded, expired, prohibited, unscanned, unverified or
        deletion-obliged record is never returned, and no flag combination overrides that.
        """
        ...

    async def resolve_source(
        self, provider_output_id: UUID, *, surface: str, moment: datetime
    ) -> GovernedOutcomeReference:
        """Turn the latest valid governance revision into a learned intake reference.

        Raises rather than guessing. A missing output, a broken event linkage, a hash that
        does not match the retained artifact, or a prohibited rights decision are each a
        refusal — an intake reference assembled from a record nobody could resolve is a
        governed outcome nobody can trace back.
        """
        ...

    async def count_revisions(self) -> int:
        """Total appended revisions. Health and backup parity read this, nothing else."""
        ...
