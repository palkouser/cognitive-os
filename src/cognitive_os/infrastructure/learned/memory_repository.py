"""Deterministic in-memory learned evidence repository.

The reference implementation of `LearnedEvidenceRepositoryPort`, and the specification
the PostgreSQL implementation is held to: both are exercised by one shared contract
suite, so a behavioural difference between them is a test failure rather than a
production surprise.

It is a faithful model, not a convenient one. History is append-only, the projection is
written separately from the ledger exactly as the SQL functions do, and `replay()`
rebuilds the projection from history and compares. Deriving the projection on read
instead would make replay tautological — it would agree by construction, and the one
integrity check that matters would prove nothing.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

from cognitive_os.domain.common import utc_now
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
    LearnedRepositoryConflict,
    LearnedRepositoryError,
    ObservationStatus,
)
from cognitive_os.learning.registry import durable_transition_is_legal

#: The largest page any listing will return, whatever the caller asks for. An unbounded
#: listing is a denial-of-service surface on a store that only ever grows.
MAX_PAGE_SIZE = 500


class InMemoryLearnedEvidenceRepository:
    """Append-only learned evidence held in process. Loses everything on exit."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._revisions: dict[str, list[LearnedComponentRevisionRecord]] = {}
        self._projection: dict[str, LearnedProjectionRow] = {}
        self._descriptor_versions: dict[str, str] = {}
        self._lineages: dict[UUID, LearnedArtifactLineage] = {}
        self._evidence: list[LearnedEvidenceRecord] = []
        self._observations: list[LearnedObservationRecord] = []
        self._approvals: dict[UUID, LearnedActivationApproval] = {}
        self._receipts: list[LearnedActivationReceipt] = []
        self._accesses: list[LearnedAccessRecord] = []
        self._revision_keys: dict[str, LearnedComponentRevisionRecord] = {}
        self._observation_keys: dict[str, LearnedObservationRecord] = {}

    # ----------------------------------------------------------------- lifecycle

    async def register_component(
        self,
        *,
        revision: LearnedComponentRevisionRecord,
        descriptor_version: str,
    ) -> LearnedComponentRevisionRecord:
        async with self._lock:
            replayed = self._replayed_revision(revision)
            if replayed is not None:
                return replayed
            if revision.component_id in self._projection:
                raise LearnedRepositoryError(
                    LearnedRepositoryConflict.ILLEGAL_TRANSITION,
                    f"{revision.component_id} is already registered",
                )
            if revision.revision != 1:
                raise LearnedRepositoryError(
                    LearnedRepositoryConflict.ILLEGAL_TRANSITION,
                    "registration must be revision 1",
                )
            now = utc_now()
            self._revisions[revision.component_id] = [revision]
            self._revision_keys[revision.idempotency_key] = revision
            self._descriptor_versions[revision.component_id] = descriptor_version
            self._projection[revision.component_id] = LearnedProjectionRow(
                component_id=revision.component_id,
                surface=revision.surface,
                descriptor_version=descriptor_version,
                current_revision=revision.revision,
                current_state=revision.state_after,
                descriptor_hash=revision.descriptor_hash,
                artifact_lineage_id=revision.artifact_lineage_id,
                created_at=now,
                updated_at=now,
            )
            return revision

    async def advance_component(
        self,
        *,
        revision: LearnedComponentRevisionRecord,
        expected_revision: int,
    ) -> LearnedComponentRevisionRecord:
        async with self._lock:
            return self._advance_locked(revision, expected_revision)

    async def record_activation_step(
        self,
        *,
        revision: LearnedComponentRevisionRecord,
        expected_revision: int,
        receipt: LearnedActivationReceipt,
    ) -> tuple[LearnedComponentRevisionRecord, LearnedActivationReceipt]:
        """Both appends under one lock, so neither can land without the other."""
        async with self._lock:
            replayed = self._replayed_revision(revision)
            if replayed is not None:
                stored_receipt = self._find_receipt(receipt.receipt_id)
                if stored_receipt is None:  # pragma: no cover - one lock, one outcome
                    raise LearnedRepositoryError(
                        LearnedRepositoryConflict.INTEGRITY_FAILURE,
                        f"revision {replayed.revision} of {replayed.component_id} was "
                        "replayed but its activation receipt is missing",
                    )
                return replayed, stored_receipt
            stored_revision = self._advance_locked(revision, expected_revision)
            self._receipts.append(receipt)
            return stored_revision, receipt

    def _advance_locked(
        self, revision: LearnedComponentRevisionRecord, expected_revision: int
    ) -> LearnedComponentRevisionRecord:
        replayed = self._replayed_revision(revision)
        if replayed is not None:
            return replayed
        current = self._projection.get(revision.component_id)
        if current is None:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.NOT_FOUND,
                f"unknown learned component: {revision.component_id}",
            )
        if current.current_revision != expected_revision:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.STALE_REVISION,
                f"{revision.component_id}: expected revision {expected_revision}, "
                f"found {current.current_revision}",
            )
        if revision.revision != current.current_revision + 1:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.STALE_REVISION,
                f"{revision.component_id}: revision {revision.revision} does not follow "
                f"{current.current_revision}",
            )
        if revision.state_before is not current.current_state:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.STALE_REVISION,
                f"{revision.component_id}: the projection holds "
                f"{current.current_state.value}, the request claims "
                f"{revision.state_before.value if revision.state_before else 'nothing'}",
            )
        if not durable_transition_is_legal(
            current.current_state,
            revision.state_after,
            rollback_target_revision=revision.rollback_target_revision,
        ):
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.ILLEGAL_TRANSITION,
                f"{revision.component_id}: {current.current_state.value} -> "
                f"{revision.state_after.value}",
            )
        if revision.state_after is LearnedComponentState.ACTIVE:
            holder = self._active_for(revision.surface)
            if holder is not None and holder.component_id != revision.component_id:
                raise LearnedRepositoryError(
                    LearnedRepositoryConflict.SURFACE_ALREADY_ACTIVE,
                    f"surface {revision.surface!r} is held by {holder.component_id}",
                )

        self._revisions[revision.component_id].append(revision)
        self._revision_keys[revision.idempotency_key] = revision
        # Constructed rather than `model_copy`-ed: `model_copy` skips validators, so the
        # copied row would keep the old content hash while carrying new field values.
        self._projection[revision.component_id] = LearnedProjectionRow(
            component_id=current.component_id,
            surface=current.surface,
            descriptor_version=current.descriptor_version,
            current_revision=revision.revision,
            current_state=revision.state_after,
            descriptor_hash=revision.descriptor_hash,
            artifact_lineage_id=revision.artifact_lineage_id or current.artifact_lineage_id,
            created_at=current.created_at,
            updated_at=utc_now(),
        )
        return revision

    def _replayed_revision(
        self, revision: LearnedComponentRevisionRecord
    ) -> LearnedComponentRevisionRecord | None:
        """The record a repeated idempotency key already produced, if it is the same one.

        Same key, same content: return the original, so a retry is free. Same key,
        different content: refuse, because accepting it would let a retry rewrite
        history under the guise of idempotency.
        """
        known = self._revision_keys.get(revision.idempotency_key)
        if known is None:
            return None
        if known.content_hash != revision.content_hash:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.IDEMPOTENCY_KEY_REUSED,
                f"idempotency key {revision.idempotency_key!r} was used for a different "
                "learned revision",
            )
        return known

    async def get_component(self, component_id: str) -> LearnedProjectionRow | None:
        return self._projection.get(component_id)

    async def list_components(
        self,
        *,
        surface: str | None = None,
        state: LearnedComponentState | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[LearnedProjectionRow, ...]:
        rows = [
            row
            for row in sorted(self._projection.values(), key=lambda item: item.component_id)
            if (surface is None or row.surface == surface)
            and (state is None or row.current_state is state)
        ]
        return _page(rows, limit=limit, offset=offset)

    async def component_history(
        self, component_id: str, *, limit: int = 100, offset: int = 0
    ) -> tuple[LearnedComponentRevisionRecord, ...]:
        history = sorted(self._revisions.get(component_id, ()), key=lambda item: item.revision)
        return _page(history, limit=limit, offset=offset)

    async def active_component_for(self, surface: str) -> LearnedProjectionRow | None:
        return self._active_for(surface)

    def _active_for(self, surface: str) -> LearnedProjectionRow | None:
        active = [
            row
            for row in sorted(self._projection.values(), key=lambda item: item.component_id)
            if row.surface == surface and row.current_state is LearnedComponentState.ACTIVE
        ]
        if len(active) > 1:  # pragma: no cover - prevented on write; asserted by replay
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.INTEGRITY_FAILURE,
                f"surface {surface!r} has {len(active)} active components",
            )
        return active[0] if active else None

    # ------------------------------------------------------------------- lineage

    async def record_artifact_lineage(
        self, lineage: LearnedArtifactLineage
    ) -> LearnedArtifactLineage:
        async with self._lock:
            known = self._lineages.get(lineage.lineage_id)
            if known is not None:
                return _same_or_conflict(known, lineage, "artifact lineage")
            self._lineages[lineage.lineage_id] = lineage
            return lineage

    async def get_artifact_lineage(self, lineage_id: UUID) -> LearnedArtifactLineage | None:
        return self._lineages.get(lineage_id)

    # ------------------------------------------------------------------ evidence

    async def record_evidence(self, evidence: LearnedEvidenceRecord) -> LearnedEvidenceRecord:
        async with self._lock:
            known = next(
                (item for item in self._evidence if item.evidence_id == evidence.evidence_id),
                None,
            )
            if known is not None:
                return _same_or_conflict(known, evidence, "evidence record")
            self._evidence.append(evidence)
            return evidence

    async def list_evidence(
        self,
        *,
        component_id: str | None = None,
        evidence_kind: LearnedEvidenceKind | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[LearnedEvidenceRecord, ...]:
        rows = [
            item
            for item in self._evidence
            if (component_id is None or item.component_id == component_id)
            and (evidence_kind is None or item.evidence_kind is evidence_kind)
        ]
        return _page(rows, limit=limit, offset=offset)

    # -------------------------------------------------------------------- intake

    async def record_observation(
        self, observation: LearnedObservationRecord
    ) -> LearnedObservationRecord:
        async with self._lock:
            known = self._observation_keys.get(observation.idempotency_key)
            if known is not None:
                return _same_or_conflict(
                    known,
                    observation,
                    "observation",
                    conflict=LearnedRepositoryConflict.IDEMPOTENCY_KEY_REUSED,
                )
            self._observations.append(observation)
            self._observation_keys[observation.idempotency_key] = observation
            return observation

    async def list_observations(
        self,
        *,
        surface: str | None = None,
        status: ObservationStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[LearnedObservationRecord, ...]:
        rows = [
            item
            for item in self._observations
            if (surface is None or item.surface == surface)
            and (status is None or item.status is status)
        ]
        return _page(rows, limit=limit, offset=offset)

    # ---------------------------------------------------------------- activation

    async def record_approval(
        self, approval: LearnedActivationApproval
    ) -> LearnedActivationApproval:
        async with self._lock:
            known = self._approvals.get(approval.approval_id)
            if known is not None:
                return _same_or_conflict(known, approval, "approval")
            self._approvals[approval.approval_id] = approval
            return approval

    async def get_approval(self, approval_id: UUID) -> LearnedActivationApproval | None:
        return self._approvals.get(approval_id)

    async def record_activation(
        self, receipt: LearnedActivationReceipt
    ) -> LearnedActivationReceipt:
        async with self._lock:
            known = self._find_receipt(receipt.receipt_id)
            if known is not None:
                return _same_or_conflict(known, receipt, "activation receipt")
            self._receipts.append(receipt)
            return receipt

    async def get_activation_receipt(self, receipt_id: UUID) -> LearnedActivationReceipt | None:
        return self._find_receipt(receipt_id)

    async def latest_activation_for(self, surface: str) -> LearnedActivationReceipt | None:
        for receipt in reversed(self._receipts):
            if receipt.surface == surface:
                return receipt
        return None

    def _find_receipt(self, receipt_id: UUID) -> LearnedActivationReceipt | None:
        return next((item for item in self._receipts if item.receipt_id == receipt_id), None)

    # --------------------------------------------------------------------- audit

    async def record_access(self, access: LearnedAccessRecord) -> LearnedAccessRecord:
        async with self._lock:
            known = next(
                (item for item in self._accesses if item.access_id == access.access_id), None
            )
            if known is not None:
                return _same_or_conflict(known, access, "access record")
            self._accesses.append(access)
            return access

    # -------------------------------------------------------------------- replay

    async def replay(self) -> LearnedReplayResult:
        """Rebuild every projection from history and report whether they agree."""
        failures: list[str] = []
        rebuilt: dict[str, tuple[int, LearnedComponentState, str, UUID | None]] = {}
        revisions_seen = 0

        for component_id in sorted(self._revisions):
            history = sorted(self._revisions[component_id], key=lambda item: item.revision)
            revisions_seen += len(history)
            state: LearnedComponentState | None = None
            previous: LearnedComponentRevisionRecord | None = None
            lineage_id: UUID | None = None
            for expected, record in enumerate(history, start=1):
                if record.revision != expected:
                    failures.append(f"{component_id}: revision {expected} is missing from history")
                    break
                if record.content_hash != record.canonical_hash(exclude={"content_hash"}):
                    failures.append(f"{component_id} revision {record.revision}: hash mismatch")
                    break
                if previous is not None and record.previous_revision != previous.revision:
                    failures.append(
                        f"{component_id} revision {record.revision}: names predecessor "
                        f"{record.previous_revision}, follows {previous.revision}"
                    )
                    break
                if record.state_before is not state:
                    failures.append(
                        f"{component_id} revision {record.revision}: left "
                        f"{record.state_before.value if record.state_before else 'nothing'}, "
                        f"history holds {state.value if state else 'nothing'}"
                    )
                    break
                if state is not None and not durable_transition_is_legal(
                    state,
                    record.state_after,
                    rollback_target_revision=record.rollback_target_revision,
                ):
                    failures.append(
                        f"{component_id} revision {record.revision}: illegal transition "
                        f"{state.value} -> {record.state_after.value}"
                    )
                    break
                state, previous = record.state_after, record
                lineage_id = record.artifact_lineage_id or lineage_id
            if previous is not None and state is not None:
                rebuilt[component_id] = (
                    previous.revision,
                    state,
                    previous.descriptor_hash,
                    lineage_id,
                )

        for component_id, row in sorted(self._projection.items()):
            expected_row = rebuilt.get(component_id)
            if expected_row is None:
                failures.append(
                    f"{component_id}: the projection holds a row that history cannot account for"
                )
                continue
            actual = (
                row.current_revision,
                row.current_state,
                row.descriptor_hash,
                row.artifact_lineage_id,
            )
            if actual != expected_row:
                failures.append(
                    f"{component_id}: the projection holds {actual}, history rebuilds "
                    f"{expected_row}"
                )
        for component_id in sorted(set(rebuilt) - set(self._projection)):
            failures.append(f"{component_id}: history exists with no projection row")

        hash_failures = [item for item in failures if "hash mismatch" in item]
        return LearnedReplayResult(
            replayed_components=len(self._revisions),
            replayed_revisions=revisions_seen,
            projection_matches=not failures,
            hash_chain_verified=not hash_failures,
            failures=tuple(failures),
            replayed_at=utc_now(),
        )

    # ------------------------------------------------------------------ snapshots

    def snapshot(self) -> tuple[tuple[str, int, str], ...]:
        """A stable, order-independent summary for tests to compare across restarts."""
        return tuple(
            (row.component_id, row.current_revision, row.current_state.value)
            for row in sorted(self._projection.values(), key=lambda item: item.component_id)
        )

    def counts(self) -> dict[str, int]:
        """Ledger sizes, for tests that assert an operation appended exactly once."""
        return {
            "components": len(self._projection),
            "revisions": sum(len(items) for items in self._revisions.values()),
            "lineages": len(self._lineages),
            "evidence": len(self._evidence),
            "observations": len(self._observations),
            "approvals": len(self._approvals),
            "receipts": len(self._receipts),
            "accesses": len(self._accesses),
        }


def _page[T](rows: list[T] | tuple[T, ...], *, limit: int, offset: int) -> tuple[T, ...]:
    if offset < 0 or limit < 0:
        raise ValueError("limit and offset must not be negative")
    capped = min(limit, MAX_PAGE_SIZE)
    return tuple(rows[offset : offset + capped])


def _same_or_conflict[
    T: LearnedAccessRecord
    | LearnedActivationApproval
    | LearnedActivationReceipt
    | LearnedArtifactLineage
    | LearnedEvidenceRecord
    | LearnedObservationRecord
](
    known: T,
    candidate: T,
    label: str,
    *,
    conflict: LearnedRepositoryConflict = LearnedRepositoryConflict.EVIDENCE_MISMATCH,
) -> T:
    """Re-appending an identical immutable record is a no-op; changing one is not.

    This is the same rule the SQL controlled functions apply, and the reason it is a
    rule at all: an immutable ledger whose rows can be replaced under an existing key is
    not immutable, it is merely inconvenient to overwrite.
    """
    if known.content_hash != candidate.content_hash:
        raise LearnedRepositoryError(
            conflict, f"an immutable {label} cannot be replaced with different content"
        )
    return known
