"""Narrow persistence ports for durable learned evidence.

Deliberately not a generic CRUD repository. Every method exists because one Sprint 21C1
use case needs it, and none exposes arbitrary SQL, untyped payload writes, or direct
state replacement — a `save(row)` method would let a caller overwrite the projection
without appending history, which is exactly the authority inversion ADR 0086 forbids.

The in-memory and PostgreSQL implementations share one contract suite, so the semantics
below are the specification for both.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from cognitive_os.domain.learned import LearnedComponentState
from cognitive_os.domain.learned_evidence import (
    LearnedAccessRecord,
    LearnedActivationApproval,
    LearnedActivationReceipt,
    LearnedArtifactLineage,
    LearnedComponentRevisionRecord,
    LearnedEvidenceKind,
    LearnedEvidenceRecord,
    LearnedObservationRecord,
    LearnedProjectionRow,
    LearnedReplayResult,
    ObservationStatus,
)


class LearnedEvidenceRepositoryPort(Protocol):
    """Durable learned state.

    Every mutation is atomic over: validate expected revision, append one immutable
    history row, update the projection, return a hash-bound receipt.

    Idempotency is by `idempotency_key`. Replaying the *same* request returns the
    original record rather than appending a second one. Reusing a key with *different*
    content raises `LearnedRepositoryConflict.IDEMPOTENCY_KEY_REUSED` — silently
    accepting it would let a retry rewrite history.
    """

    async def register_component(
        self,
        *,
        revision: LearnedComponentRevisionRecord,
        descriptor_version: str,
    ) -> LearnedComponentRevisionRecord:
        """Append revision 1 and create the projection row.

        Raises `IDEMPOTENCY_KEY_REUSED` if the key is known with different content.
        """
        ...

    async def advance_component(
        self,
        *,
        revision: LearnedComponentRevisionRecord,
        expected_revision: int,
    ) -> LearnedComponentRevisionRecord:
        """Compare-and-swap one lifecycle step.

        Raises `STALE_REVISION` when the projection has moved, `ILLEGAL_TRANSITION` when
        the registry policy refuses the state change, and `SURFACE_ALREADY_ACTIVE` when
        the step would give one surface two active components.
        """
        ...

    async def get_component(self, component_id: str) -> LearnedProjectionRow | None: ...

    async def list_components(
        self,
        *,
        surface: str | None = None,
        state: LearnedComponentState | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[LearnedProjectionRow, ...]:
        """Bounded listing. `limit` is capped by the implementation, never unbounded."""
        ...

    async def component_history(
        self, component_id: str, *, limit: int = 100, offset: int = 0
    ) -> tuple[LearnedComponentRevisionRecord, ...]:
        """History in ascending revision order, which is the replay order."""
        ...

    async def active_component_for(self, surface: str) -> LearnedProjectionRow | None:
        """At most one, enforced by the service and by a partial unique index."""
        ...

    async def record_artifact_lineage(
        self, lineage: LearnedArtifactLineage
    ) -> LearnedArtifactLineage:
        """Append verified lineage. The caller must have verified the observed hash."""
        ...

    async def get_artifact_lineage(self, lineage_id: UUID) -> LearnedArtifactLineage | None: ...

    async def record_evidence(self, evidence: LearnedEvidenceRecord) -> LearnedEvidenceRecord:
        """Append one typed evidence record. Unknown kinds fail before reaching here."""
        ...

    async def list_evidence(
        self,
        *,
        component_id: str | None = None,
        evidence_kind: LearnedEvidenceKind | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[LearnedEvidenceRecord, ...]: ...

    async def record_observation(
        self, observation: LearnedObservationRecord
    ) -> LearnedObservationRecord:
        """Append one intake decision, idempotent on `idempotency_key`."""
        ...

    async def list_observations(
        self,
        *,
        surface: str | None = None,
        status: ObservationStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[LearnedObservationRecord, ...]: ...

    async def record_approval(
        self, approval: LearnedActivationApproval
    ) -> LearnedActivationApproval:
        """Append an activation approval. Self-approval fails in the contract."""
        ...

    async def get_approval(self, approval_id: UUID) -> LearnedActivationApproval | None: ...

    async def record_activation(
        self, receipt: LearnedActivationReceipt
    ) -> LearnedActivationReceipt:
        """Append an activation, disable or rollback receipt."""
        ...

    async def get_activation_receipt(self, receipt_id: UUID) -> LearnedActivationReceipt | None: ...

    async def latest_activation_for(self, surface: str) -> LearnedActivationReceipt | None:
        """The head of the activation chain, which a rollback must name."""
        ...

    async def record_access(self, access: LearnedAccessRecord) -> LearnedAccessRecord: ...

    async def replay(self) -> LearnedReplayResult:
        """Rebuild every projection from history and compare. Mutates nothing.

        Fails closed on a missing revision, a broken predecessor, an illegal transition
        or a hash mismatch, and reports each as a named failure.
        """
        ...
